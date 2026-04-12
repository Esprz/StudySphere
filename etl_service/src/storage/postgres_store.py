from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from src.models.postgres_models import BehaviorEvent, Base
from typing import Dict, Any, Optional
import uuid
from loguru import logger


class PostgresStore:
    def __init__(self, db_config):
        self.db = db_config
        Base.metadata.create_all(bind=self.db.engine)
        self._ensure_behavior_event_schema()

    def get_session(self) -> Session:
        return self.db.get_session()

    def _ensure_behavior_event_schema(self) -> None:
        """Upgrade the shared ETL table in-place when the local DB is on an older schema."""
        statements = [
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
            CREATE UNIQUE INDEX IF NOT EXISTS ix_etl_behavior_events_event_id
            ON etl_behavior_events (event_id)
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_etl_behavior_events_event_id
            ON etl_behavior_events (event_id)
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
        except Exception as e:
            logger.error(f"Failed to ensure ETL behavior event schema: {e}")

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
                    stmt = (
                        insert(BehaviorEvent)
                        .values(**row)
                        .on_conflict_do_nothing(index_elements=["event_id"])
                    )
                    result = session.execute(stmt)
                    session.commit()
                    if result.rowcount == 0:
                        logger.debug(f"Duplicate event_id {event_id} skipped")
                        return False
                else:
                    session.add(BehaviorEvent(**row))
                    session.commit()

                logger.info(
                    f"Behavior event stored: user={user_id} type={event_type}"
                )
                return True

        except Exception as e:
            logger.error(f"Error storing behavior event: {e}")
            return False
