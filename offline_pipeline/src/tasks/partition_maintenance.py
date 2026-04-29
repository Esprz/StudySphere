"""Monthly ETL partition migration and maintenance helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from psycopg import Connection


class PartitionMaintenanceTask:
    """Migrate `etl_behavior_events` to monthly partitions and maintain future partitions."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def run(self) -> dict[str, Any]:
        """Ensure the ETL event table is partitioned and create the next monthly partition."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'etl_behavior_events'
                ) AS exists
                """
            )
            row = cursor.fetchone()
            if not row or not row["exists"]:
                self._create_partitioned_parent()

            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_partitioned_table pt
                    JOIN pg_class c ON c.oid = pt.partrelid
                    WHERE c.relname = 'etl_behavior_events'
                ) AS is_partitioned
                """
            )
            row = cursor.fetchone()
            is_partitioned = bool(row and row["is_partitioned"])
            if not is_partitioned:
                migrated = self._migrate_existing_table()
            else:
                migrated = False

        next_partition_name = self._ensure_partition_for_month(_first_of_next_month(datetime.now(timezone.utc)))
        self.connection.commit()
        return {
            "job": "partition-maintenance",
            "status": "migrated_and_created" if migrated else "created_or_exists",
            "partition_name": next_partition_name,
            "migrated_table": migrated,
        }

    def _create_partitioned_parent(self) -> None:
        """Create the target partitioned parent plus dedupe registry from scratch."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS etl_behavior_event_keys (
                    event_id VARCHAR PRIMARY KEY,
                    processed_at TIMESTAMP NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS etl_behavior_events (
                    id VARCHAR NOT NULL,
                    user_id VARCHAR NOT NULL,
                    post_id VARCHAR,
                    event_type VARCHAR NOT NULL,
                    search_term VARCHAR,
                    processed_at TIMESTAMP NOT NULL,
                    embedding_generated VARCHAR,
                    extra_data JSON,
                    event_id VARCHAR,
                    session_id VARCHAR,
                    position INTEGER,
                    dwell_ms INTEGER,
                    source VARCHAR,
                    PRIMARY KEY (processed_at, id)
                )
                PARTITION BY RANGE (processed_at)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_user_id
                ON etl_behavior_events (user_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_post_id
                ON etl_behavior_events (post_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_processed_at
                ON etl_behavior_events (processed_at)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_session_id
                ON etl_behavior_events (session_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_position
                ON etl_behavior_events (position)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_dwell_ms
                ON etl_behavior_events (dwell_ms)
                """
            )

    def _migrate_existing_table(self) -> bool:
        """Convert an existing heap table into a range-partitioned table while preserving data."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS row_count,
                    MIN(COALESCE(processed_at, NOW())) AS min_processed_at,
                    MAX(COALESCE(processed_at, NOW())) AS max_processed_at
                FROM etl_behavior_events
                """
            )
            row = cursor.fetchone()
        row_count = int((row or {}).get("row_count", 0))
        if row_count == 0:
            with self.connection.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS etl_behavior_events")
            self._create_partitioned_parent()
            self._ensure_partition_for_month(_first_of_month(datetime.now(timezone.utc)))
            return True

        min_processed_at = _coerce_naive_datetime(row["min_processed_at"])
        max_processed_at = _coerce_naive_datetime(row["max_processed_at"])
        legacy_name = f"etl_behavior_events_legacy_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS etl_behavior_event_keys (
                    event_id VARCHAR PRIMARY KEY,
                    processed_at TIMESTAMP NOT NULL
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO etl_behavior_event_keys (event_id, processed_at)
                SELECT DISTINCT event_id, COALESCE(processed_at, NOW())
                FROM etl_behavior_events
                WHERE event_id IS NOT NULL
                ON CONFLICT (event_id) DO NOTHING
                """
            )
            cursor.execute(f'ALTER TABLE etl_behavior_events RENAME TO {legacy_name}')

        self._create_partitioned_parent()
        month_cursor = _first_of_month(min_processed_at)
        end_month = _first_of_month(max_processed_at)
        while month_cursor <= end_month:
            self._ensure_partition_for_month(month_cursor)
            month_cursor = _first_of_next_month(month_cursor)
        self._ensure_partition_for_month(_first_of_next_month(datetime.now(timezone.utc)))

        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO etl_behavior_events (
                    id,
                    user_id,
                    post_id,
                    event_type,
                    search_term,
                    processed_at,
                    embedding_generated,
                    extra_data,
                    event_id,
                    session_id,
                    position,
                    dwell_ms,
                    source
                )
                SELECT
                    id,
                    user_id,
                    post_id,
                    event_type,
                    search_term,
                    COALESCE(processed_at, NOW()),
                    embedding_generated,
                    extra_data,
                    event_id,
                    session_id,
                    position,
                    dwell_ms,
                    source
                FROM {legacy_name}
                """
            )
        return True

    def _ensure_partition_for_month(self, month_start: datetime) -> str:
        """Create one monthly partition if missing."""
        start = _first_of_month(month_start)
        end = _first_of_next_month(start)
        partition_name = f"etl_behavior_events_{start.strftime('%Y_%m')}"
        start_literal = start.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        end_literal = end.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {partition_name}
                PARTITION OF etl_behavior_events
                FOR VALUES FROM ('{start_literal}') TO ('{end_literal}')
                """
            )
        return partition_name


def _first_of_month(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _first_of_next_month(value: datetime) -> datetime:
    base = _first_of_month(value)
    return (base + timedelta(days=32)).replace(day=1)


def _coerce_naive_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return datetime.now(timezone.utc)
