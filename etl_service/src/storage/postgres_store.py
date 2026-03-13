from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from src.models.postgres_models import BehaviorEvent, Base
from typing import Dict, Any, Optional
import uuid
from loguru import logger


class PostgresStore:
    def __init__(self, db_config):
        self.db = db_config
        Base.metadata.create_all(bind=self.db.engine)

    def get_session(self) -> Session:
        return self.db.get_session()

    def store_behavior_event(
        self,
        user_id: str,
        post_id: str = None,
        event_type: str = None,
        search_term: str = None,
        extra_data: Dict[str, Any] = None,
        event_id: Optional[str] = None,
    ) -> bool:
        try:
            row = {
                "id": str(uuid.uuid4()),
                "event_id": event_id,
                "user_id": user_id,
                "post_id": post_id,
                "event_type": event_type,
                "search_term": search_term,
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
