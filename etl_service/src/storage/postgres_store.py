from sqlalchemy.orm import Session
from config.database_config import DatabaseConfig
from src.models.postgres_models import ProcessedVector, BehaviorEvent, Base
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timezone


class PostgresStore:
    def __init__(self):
        self.db = DatabaseConfig()
        Base.metadata.create_all(bind=self.db.engine)

    def get_session(self) -> Session:
        return self.db.get_session()

    def store_vector(
        self,
        source_id: str,  # post_id, user_id, etc.
        source_type: str,  # 'post', 'user', 'search'
        vector_data: List[float],
        vector_dimension: int,
        faiss_indexed: str = "pending",
        extra_data: Dict[str, Any] = None,
    ) -> bool:
        try:
            with self.get_session() as session:
                existing = (
                    session.query(ProcessedVector)
                    .filter_by(source_id=source_id, source_type=source_type)
                    .first()
                )

                if existing:
                    existing.vector_data = vector_data
                    existing.vector_dimension = vector_dimension
                    existing.faiss_indexed = faiss_indexed
                    existing.processed_at = datetime.now(timezone.utc)
                    existing.extra_data = extra_data
                    if existing.faiss_indexed == "indexed":
                        existing.last_faiss_sync = datetime.now(timezone.utc)
                else:
                    processed_vector = ProcessedVector(
                        id=str(uuid.uuid4()),
                        source_id=source_id,
                        source_type=source_type,
                        vector_data=vector_data,
                        vector_dimension=vector_dimension,
                        faiss_indexed=faiss_indexed,
                        extra_data=extra_data,
                        last_faiss_sync=datetime.now(datetime.now(timezone.utc))
                        if faiss_indexed == "indexed"
                        else None,
                    )
                    session.add(processed_vector)

                session.commit()
                return True

        except Exception as e:
            print(f"❌Error storing vector metadata {source_id}: {e}")
            return False

    def get_vector(self, source_id: str, source_type: str) -> Optional[ProcessedVector]:
        try:
            with self.get_session() as session:
                return (
                    session.query(ProcessedVector)
                    .filter_by(source_id=source_id, source_type=source_type)
                    .first()
                )
        except Exception as e:
            print(f"❌Error getting vector metadata {source_id}: {e}")
            return None

    def get_unindexed_vectors(self, limit: int = 100) -> List[ProcessedVector]:
        try:
            with self.get_session() as session:
                return (
                    session.query(ProcessedVector)
                    .filter(ProcessedVector.faiss_indexed != "indexed")
                    .limit(limit)
                    .all()
                )
        except Exception as e:
            print(f"❌Error getting unindexed vectors: {e}")
            return []

    def mark_faiss_indexed(
        self, source_id: str, source_type: str, succes: bool = True
    ) -> bool:
        try:
            with self.get_session() as session:
                vector = (
                    session.query(ProcessedVector)
                    .filter_by(source_id=source_id, source_type=source_type)
                    .first()
                )
                if vector:
                    vector.faiss_indexed = "indexed" if succes else "failed"
                    if succes:
                        vector.last_faiss_sync = datetime.now(timezone.utc)
                    session.commit()
                    return True
                else:
                    print(f"❌ Vector not found for {source_id}")
                    return False
        except Exception as e:
            print(f"❌Error marking vector {source_id} as indexed: {e}")
            return False

    def update_vector(
        self,
        source_id: str,
        source_type: str,
        vector_data: List[float],
        vector_dimension: int,
        faiss_indexed: str = "pending",
        extra_data: Dict[str, Any] = None,
    ) -> bool:
        try:
            with self.get_session() as session:
                vector = (
                    session.query(ProcessedVector)
                    .filter_by(source_id=source_id, source_type=source_type)
                    .first()
                )

                if vector:
                    vector.vector_data = vector_data
                    vector.vector_dimension = vector_dimension
                    vector.faiss_indexed = faiss_indexed
                    vector.processed_at = datetime.now(timezone.utc)
                    vector.extra_data = extra_data
                    session.commit()
                    return True
                else:
                    print(f"Vector not found for update: {source_id}")
                    return False

        except Exception as e:
            print(f"Error updating vector {source_id}: {e}")
            return False

    def delete_vector(self, source_id: str, source_type: str) -> bool:
        try:
            with self.get_session() as session:
                result = (
                    session.query(ProcessedVector)
                    .filter_by(source_id=source_id, source_type=source_type)
                    .delete()
                )
                session.commit()
                return result > 0

        except Exception as e:
            print(f"Error deleting vector {source_id}: {e}")
            return False

    def store_behavior_event(
        self,
        user_id: str,
        post_id: str = None,
        event_type: str = None,
        search_term: str = None,
        embedding_generated: str = None,
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
                    embedding_generated=embedding_generated,
                    extra_data=extra_data,
                )
                session.add(behavior_event)
                session.commit()
                return True

        except Exception as e:
            print(f"❌Error storing behavior event: {e}")
            return False
