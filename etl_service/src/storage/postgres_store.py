from sqlalchemy.orm import Session
from sqlalchemy import text
from src.models.postgres_models import BehaviorEvent, Base
from typing import Dict, Any, Optional
import uuid
from loguru import logger
from datetime import datetime, timezone, timedelta


class PostgresStore:
    def __init__(self, db_config):
        self.db = db_config
        Base.metadata.create_all(bind=self.db.engine)
        self._ensure_behavior_event_schema()

    def get_session(self) -> Session:
        return self.db.get_session()

    def _ensure_behavior_event_schema(self) -> None:
        """Upgrade ETL event storage and migrate to monthly partitions when needed."""
        statements = [
            """
            CREATE TABLE IF NOT EXISTS etl_behavior_event_keys (
                event_id VARCHAR PRIMARY KEY,
                processed_at TIMESTAMP NOT NULL
            )
            """,
            """
            ALTER TABLE etl_behavior_events
            ADD COLUMN IF NOT EXISTS event_id VARCHAR
            """,
            """
            ALTER TABLE etl_behavior_events
            ADD COLUMN IF NOT EXISTS session_id VARCHAR
            """,
            """
            ALTER TABLE etl_behavior_events
            ADD COLUMN IF NOT EXISTS position INTEGER
            """,
            """
            ALTER TABLE etl_behavior_events
            ADD COLUMN IF NOT EXISTS dwell_ms INTEGER
            """,
            """
            ALTER TABLE etl_behavior_events
            ADD COLUMN IF NOT EXISTS source VARCHAR
            """,
            """
            ALTER TABLE etl_behavior_events
            ADD COLUMN IF NOT EXISTS extra_data JSON
            """,
            """
            ALTER TABLE etl_behavior_events
            ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP WITHOUT TIME ZONE
            """,
            """
            ALTER TABLE etl_behavior_events
            ADD COLUMN IF NOT EXISTS embedding_generated VARCHAR
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_session_id
            ON etl_behavior_events (session_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_position
            ON etl_behavior_events (position)
            """,
            """
            CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_dwell_ms
            ON etl_behavior_events (dwell_ms)
            """,
        ]

        try:
            with self.get_session() as session:
                for statement in statements:
                    session.execute(text(statement))
                session.commit()
                self._migrate_behavior_events_to_partitions(session)
                self._ensure_behavior_event_partition(
                    session,
                    self._first_of_next_month(datetime.now(timezone.utc)),
                )
                session.commit()
        except Exception as e:
            logger.error(f"Failed to ensure ETL behavior event schema: {e}")

    def _migrate_behavior_events_to_partitions(self, session: Session) -> None:
        """Convert heap ETL event table into a partitioned table if needed."""
        is_partitioned = bool(
            session.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM pg_partitioned_table pt
                        JOIN pg_class c ON c.oid = pt.partrelid
                        WHERE c.relname = 'etl_behavior_events'
                    )
                    """
                )
            ).scalar()
        )
        if is_partitioned:
            return

        row = session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS row_count,
                    MIN(COALESCE(processed_at, NOW())) AS min_processed_at,
                    MAX(COALESCE(processed_at, NOW())) AS max_processed_at
                FROM etl_behavior_events
                """
            )
        ).mappings().one()
        row_count = int(row["row_count"])

        session.execute(
            text(
                """
                INSERT INTO etl_behavior_event_keys (event_id, processed_at)
                SELECT DISTINCT event_id, COALESCE(processed_at, NOW())
                FROM etl_behavior_events
                WHERE event_id IS NOT NULL
                ON CONFLICT (event_id) DO NOTHING
                """
            )
        )
        legacy_name = f"etl_behavior_events_legacy_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        session.execute(text(f'ALTER TABLE etl_behavior_events RENAME TO {legacy_name}'))
        session.execute(
            text(
                """
                CREATE TABLE etl_behavior_events (
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
        )
        for statement in [
            "CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_user_id ON etl_behavior_events (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_post_id ON etl_behavior_events (post_id)",
            "CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_processed_at ON etl_behavior_events (processed_at)",
            "CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_session_id ON etl_behavior_events (session_id)",
            "CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_position ON etl_behavior_events (position)",
            "CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_dwell_ms ON etl_behavior_events (dwell_ms)",
        ]:
            session.execute(text(statement))

        if row_count > 0:
            min_month = self._first_of_month(row["min_processed_at"])
            max_month = self._first_of_month(row["max_processed_at"])
            month_cursor = min_month
            while month_cursor <= max_month:
                self._ensure_behavior_event_partition(session, month_cursor)
                month_cursor = self._first_of_next_month(month_cursor)
            session.execute(
                text(
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
            )
        else:
            self._ensure_behavior_event_partition(session, self._first_of_month(datetime.now(timezone.utc)))

    def _ensure_behavior_event_partition(self, session: Session, month_start: datetime) -> None:
        """Create one monthly partition if it does not yet exist."""
        start = self._first_of_month(month_start)
        end = self._first_of_next_month(start)
        partition_name = f"etl_behavior_events_{start.strftime('%Y_%m')}"
        start_literal = start.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        end_literal = end.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        session.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {partition_name}
                PARTITION OF etl_behavior_events
                FOR VALUES FROM ('{start_literal}') TO ('{end_literal}')
                """
            )
        )

    def _first_of_month(self, value) -> datetime:
        if value is None:
            return datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if getattr(value, "tzinfo", None) is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _first_of_next_month(self, value) -> datetime:
        base = self._first_of_month(value)
        return (base + timedelta(days=32)).replace(day=1)

    def store_behavior_event(
        self,
        user_id: str,
        post_id: str = None,
        event_type: str = None,
        search_term: str = None,
        extra_data: Dict[str, Any] = None,
        event_id: Optional[str] = None,
        session_id: Optional[str] = None,
        position: Optional[int] = None,
        dwell_ms: Optional[int] = None,
        source: Optional[str] = None,
    ) -> bool:
        try:
            row = {
                "id": str(uuid.uuid4()),
                "event_id": event_id,
                "user_id": user_id,
                "post_id": post_id,
                "event_type": event_type,
                "search_term": search_term,
                "session_id": session_id,
                "position": position,
                "dwell_ms": dwell_ms,
                "source": source,
                "extra_data": extra_data,
            }

            with self.get_session() as session:
                if event_id:
                    inserted = session.execute(
                        text(
                            """
                            INSERT INTO etl_behavior_event_keys (event_id, processed_at)
                            VALUES (:event_id, COALESCE(:processed_at, NOW()))
                            ON CONFLICT (event_id) DO NOTHING
                            RETURNING event_id
                            """
                        ),
                        {
                            "event_id": event_id,
                            "processed_at": datetime.now(timezone.utc).replace(tzinfo=None),
                        },
                    )
                    if inserted.scalar() is None:
                        session.rollback()
                        logger.debug(f"Duplicate event_id {event_id} skipped")
                        return False
                self._ensure_behavior_event_partition(
                    session,
                    row.get("processed_at") or datetime.now(timezone.utc),
                )
                result = session.execute(
                    text(
                        """
                        INSERT INTO etl_behavior_events (
                            id,
                            event_id,
                            user_id,
                            post_id,
                            event_type,
                            search_term,
                            session_id,
                            position,
                            dwell_ms,
                            source,
                            processed_at,
                            extra_data
                        )
                        VALUES (
                            :id,
                            :event_id,
                            :user_id,
                            :post_id,
                            :event_type,
                            :search_term,
                            :session_id,
                            :position,
                            :dwell_ms,
                            :source,
                            COALESCE(:processed_at, NOW()),
                            :extra_data
                        )
                        """
                    ),
                    {
                        **row,
                        "processed_at": datetime.now(timezone.utc).replace(tzinfo=None),
                    },
                )
                session.commit()
                if result.rowcount == 0:
                    logger.debug(f"Behavior event insert produced no rows for event_id={event_id}")
                    return False
                logger.info(
                    f"Behavior event stored: user={user_id} type={event_type}"
                )
                return True

        except Exception as e:
            logger.error(f"Error storing behavior event: {e}")
            return False
