from sqlalchemy import Column, String, DateTime, JSON, Integer, Float, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class BehaviorEvent(Base):
    """User interaction events for recommendation algorithms"""
    __tablename__ = "etl_behavior_events"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    post_id = Column(String, index=True)
    event_type = Column(String, nullable=False)  # VIEW, LIKE, SAVE, SEARCH
    search_term = Column(String)
    processed_at = Column(DateTime, default=datetime.now(timezone.utc))
    extra_data = Column(JSON)  # Changed from 'metadata' to 'extra_data'
