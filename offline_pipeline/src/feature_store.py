"""Versioned feature-table helpers for Spec 4 offline artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from psycopg import Connection


CF_FEATURE_NAME = "cf"
TRENDING_FEATURE_NAME = "trending"
ACTIVE_VERSION_REDIS_KEYS = {
    CF_FEATURE_NAME: "offline:cf:active_version",
    TRENDING_FEATURE_NAME: "offline:trending:active_version",
}
FEATURE_TABLES = {
    CF_FEATURE_NAME: [
        "user_item_interest",
        "user_user_similarity",
        "item_item_similarity",
        "user_similar_users",
        "item_similar_items",
        "user_interested_items",
    ],
    TRENDING_FEATURE_NAME: ["trending_items"],
}


@dataclass(frozen=True)
class FeatureCutoverResult:
    """Metadata emitted after one feature version is activated."""

    feature_name: str
    version: str
    previous_version: str | None
    row_count: int
    computed_at: datetime


class FeatureStore:
    """Owns versioning metadata, runtime DB limits, and cleanup helpers."""

    def __init__(
        self,
        connection: Connection,
        *,
        session_cache: Any | None = None,
        work_mem: str = "64MB",
        statement_timeout_ms: int = 1_800_000,
    ) -> None:
        self.connection = connection
        self.session_cache = session_cache
        self.work_mem = work_mem
        self.statement_timeout_ms = statement_timeout_ms

    def ensure_runtime_schema(self) -> None:
        """Create feature metadata and supportive indexes when absent."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_metadata (
                    feature_name VARCHAR(100) PRIMARY KEY,
                    active_version VARCHAR(50) NOT NULL,
                    computed_at TIMESTAMP NOT NULL,
                    row_count INTEGER,
                    status VARCHAR(20) NOT NULL DEFAULT 'active'
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS user_item_interest_version_idx
                ON user_item_interest (version, user_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS user_similar_users_version_idx
                ON user_similar_users (version, user_id, rank)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS item_similar_items_version_idx
                ON item_similar_items (version, item_id, rank)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS trending_items_version_rank_idx
                ON trending_items (version, rank)
                """
            )
        self.connection.commit()

    def apply_runtime_resource_limits(self) -> None:
        """Apply constrained work_mem and statement_timeout for batch execution."""
        with self.connection.cursor() as cursor:
            cursor.execute(f"SET work_mem = '{self.work_mem}'")
            cursor.execute(f"SET statement_timeout = '{self.statement_timeout_ms}ms'")

    def create_version_tag(
        self,
        feature_name: str,
        *,
        computed_at: datetime | None = None,
    ) -> str:
        """Return timestamp-stable version ids like `cf_20260428T021530Z`."""
        timestamp = computed_at or datetime.now(timezone.utc)
        return f"{feature_name}_{timestamp.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    def get_active_version(self, feature_name: str) -> str | None:
        """Read the active version from metadata or session Redis marker."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT active_version
                FROM feature_metadata
                WHERE feature_name = %s
                """,
                (feature_name,),
            )
            row = cursor.fetchone()
        if row:
            return str(row["active_version"])
        if self.session_cache is None:
            return None
        key = ACTIVE_VERSION_REDIS_KEYS.get(feature_name)
        if key is None:
            return None
        return self.session_cache.get_text(key)

    def activate_version(
        self,
        *,
        feature_name: str,
        version: str,
        row_count: int,
        computed_at: datetime | None = None,
    ) -> FeatureCutoverResult:
        """Promote a freshly written version to active after successful writes."""
        timestamp = computed_at or datetime.now(timezone.utc)
        previous_version = self.get_active_version(feature_name)
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO feature_metadata (
                    feature_name,
                    active_version,
                    computed_at,
                    row_count,
                    status
                )
                VALUES (%s, %s, %s, %s, 'active')
                ON CONFLICT (feature_name)
                DO UPDATE SET
                    active_version = EXCLUDED.active_version,
                    computed_at = EXCLUDED.computed_at,
                    row_count = EXCLUDED.row_count,
                    status = EXCLUDED.status
                """,
                (feature_name, version, timestamp.replace(tzinfo=None), row_count),
            )
        self.connection.commit()
        if self.session_cache is not None:
            key = ACTIVE_VERSION_REDIS_KEYS.get(feature_name)
            if key:
                self.session_cache.set_text(key, version)
        return FeatureCutoverResult(
            feature_name=feature_name,
            version=version,
            previous_version=previous_version,
            row_count=row_count,
            computed_at=timestamp,
        )

    def cleanup_inactive_versions(self, feature_name: str, keep_version: str) -> dict[str, int]:
        """Delete rows for non-active historical versions of one feature family."""
        deleted: dict[str, int] = {}
        for table_name in FEATURE_TABLES.get(feature_name, []):
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {table_name} WHERE version <> %s",
                    (keep_version,),
                )
                deleted[table_name] = cursor.rowcount
        self.connection.commit()
        return deleted
