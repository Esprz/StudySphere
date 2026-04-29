from sqlalchemy import Column, String, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class BehaviorEvent(Base):
    __tablename__ = "etl_behavior_events"

    id = Column(String, primary_key=True)
    event_id = Column(String, nullable=True)
    user_id = Column(String, nullable=False, index=True)
    post_id = Column(String, index=True)
    event_type = Column(String, nullable=False)
    search_term = Column(String)
    session_id = Column(String, index=True)
    position = Column(Integer)
    dwell_ms = Column(Integer)
    source = Column(String)
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    embedding_generated = Column(String)
    extra_data = Column(JSON)
