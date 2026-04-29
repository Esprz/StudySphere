"""User-item feature generation from recent ETL behavior events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from psycopg import Connection

from ..feature_store import CF_FEATURE_NAME, FeatureStore
from .common import fetch_recent_interest_rows


@dataclass(frozen=True)
class FeatureProcessorResult:
    """One completed user-item interest build for a fresh CF version."""

    version: str
    row_count: int
    interested_item_row_count: int
    computed_at: datetime


class FeatureProcessorTask:
    """Compute `user_item_interest` and `user_interested_items` for one version."""

    def __init__(
        self,
        connection: Connection,
        feature_store: FeatureStore,
        *,
        top_k: int = 10,
        lookback_days: int = 90,
    ) -> None:
        self.connection = connection
        self.feature_store = feature_store
        self.top_k = top_k
        self.lookback_days = lookback_days

    def run(self) -> dict[str, Any]:
        """Build one new CF version from recent ETL events."""
        self.feature_store.ensure_runtime_schema()
        self.feature_store.apply_runtime_resource_limits()
        computed_at = datetime.now(timezone.utc)
        version = self.feature_store.create_version_tag(
            CF_FEATURE_NAME,
            computed_at=computed_at,
        )
        rows = fetch_recent_interest_rows(self.connection, lookback_days=self.lookback_days)

        interest_payload = [
            (
                str(row["user_id"]),
                str(row["post_id"]),
                float(row["interest_score"]),
                version,
                computed_at.replace(tzinfo=None),
            )
            for row in rows
        ]
        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO user_item_interest (
                    user_id,
                    item_id,
                    interest_score,
                    version,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                interest_payload,
            )

            cursor.execute(
                """
                WITH ranked AS (
                    SELECT
                        user_id,
                        item_id,
                        interest_score,
                        ROW_NUMBER() OVER (
                            PARTITION BY user_id
                            ORDER BY interest_score DESC, item_id ASC
                        ) AS rank
                    FROM user_item_interest
                    WHERE version = %s
                )
                INSERT INTO user_interested_items (
                    user_id,
                    item_id,
                    interest_score,
                    rank,
                    version,
                    created_at
                )
                SELECT
                    user_id,
                    item_id,
                    interest_score,
                    rank,
                    %s,
                    %s
                FROM ranked
                WHERE rank <= %s
                """,
                (version, version, computed_at.replace(tzinfo=None), self.top_k),
            )
            interested_item_row_count = cursor.rowcount
        self.connection.commit()

        return {
            "job": "feature-processor",
            "version": version,
            "row_count": len(interest_payload),
            "interested_item_row_count": interested_item_row_count,
            "computed_at": computed_at.isoformat(),
        }
