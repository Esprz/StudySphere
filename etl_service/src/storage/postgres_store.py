from sqlalchemy import text
from config.database_config import DatabaseConfig


class PostgresStore:
    def __init__(self):
        self.db = DatabaseConfig()

    def store_behavior_event(
        self, user_id: str, post_id: str, event_type: str, timestamp: str
    ):
        with self.db.get_session() as session:
            query = text(
                """
                INSERT INTO behavior_events (user_id, post_id, event_type, timestamp)
                VALUES (:user_id, :post_id, :event_type, :timestamp)
            """
            )
            session.execute(
                query,
                {
                    "user_id": user_id,
                    "post_id": post_id,
                    "event_type": event_type,
                    "timestamp": timestamp,
                },
            )
            session.commit()
