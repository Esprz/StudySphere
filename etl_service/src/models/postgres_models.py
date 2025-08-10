from sqlalchemy import Column, String, DateTime, JSON, Integer, Float, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class ProcessedVector(Base):
    __tablename__ = "etl_processed_vectors"

    id = Column(String, primary_key=True)
    source_id = Column(String, nullable=False, index=True)  # post_id or user_id
    source_type = Column(String, nullable=False)  # 'post' or 'user' or 'search'

    vector_data = Column(ARRAY(Float), nullable=False)
    vector_dimension = Column(Integer)

    faiss_indexed = Column(String, default="pending")  # pending, indexed, failed

    processed_at = Column(DateTime, default=datetime.now(timezone.utc))
    last_faiss_sync = Column(DateTime, default=datetime.now(timezone.utc))
    extra_data = Column(JSON)  # Changed from 'metadata' to 'extra_data'


class BehaviorEvent(Base):
    __tablename__ = "etl_behavior_events"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    post_id = Column(String, index=True)
    event_type = Column(String, nullable=False)  # VIEW, LIKE, SAVE, SEARCH
    search_term = Column(String)
    processed_at = Column(DateTime, default=datetime.now(timezone.utc))
    embedding_generated = Column(String)
    extra_data = Column(JSON)  # Changed from 'metadata' to 'extra_data'
