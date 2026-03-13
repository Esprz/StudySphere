from sqlalchemy import Column, String, DateTime, JSON, Integer, Float, ARRAY, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class BehaviorEvent(Base):
    __tablename__ = "etl_behavior_events"

    id = Column(String, primary_key=True)
    event_id = Column(String, unique=True, nullable=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    post_id = Column(String, index=True)
    event_type = Column(String, nullable=False)
    search_term = Column(String)
    processed_at = Column(DateTime, default=datetime.now(timezone.utc))
    extra_data = Column(JSON)
