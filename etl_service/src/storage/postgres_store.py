from sqlalchemy.orm import Session
from src.models.postgres_models import BehaviorEvent, Base
from typing import Dict, Any
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
    ) -> bool:
        """Store behavior event"""
        try:
            with self.get_session() as session:
                behavior_event = BehaviorEvent(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    post_id=post_id,
                    event_type=event_type,
                    search_term=search_term,
                    extra_data=extra_data,
                )
                session.add(behavior_event)
                session.commit()
                logger.info(
                    f"✅ Behavior event stored successfully for user: {user_id} and post: {post_id}"
                )
                return True

        except Exception as e:
            logger.error(f"❌ Error storing behavior event: {e}")
            return False
