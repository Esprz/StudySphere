from typing import List, Optional, Dict, Any
from loguru import logger
from .qdrant_manager import QdrantManager


class VectorStore:
    """High-level vector storage with unified CRUD operations"""

    def __init__(self, qdrant_manager: QdrantManager):
        self.vector_store = qdrant_manager

    # ==================== UNIFIED CRUD METHODS ====================

    def get_vector(self, source_id: str, source_type: str) -> Optional[List[float]]:
        """Unified method to get any type of vector"""
        try:
            vector = self.vector_store.get_vector(source_type, source_id)
            if vector:
                logger.info(f"✅ Retrieved {source_type} vector {source_id}")
                return vector
        except Exception as qdrant_error:
            logger.error(f"❌ QDRANT lookup failed for {source_id}: {qdrant_error}")

        return None

    # ==================== CONVENIENCE METHODS ====================

    def get_post_vector(self, post_id: str) -> Optional[List[float]]:
        """Convenience method for getting post vectors"""
        return self.vector_store.get_vector(post_id, "realtime_posts")

    def get_user_vector(self, user_id: str) -> Optional[List[float]]:
        """Convenience method for getting user vectors"""
        return self.vector_store. get_vector(user_id, "realtime_users")

    # ==================== SEARCH METHODS ====================

    def search_posts(self, user_vector: List[float], k: int = 5) -> tuple:
        """Search similar posts"""
        try:
            post_ids, scores = self.vector_store.search_vectors(
                "realtime_posts", user_vector, k
            )
            logger.info(f"✅ Searched {len(post_ids)} posts for user {user_vector}")
            return post_ids, scores
        except Exception as e:
            logger.error(f"❌ Failed to search posts: {e}")
            return [], []

    def search_users(self, post_vector: List[float], k: int = 5) -> tuple:
        """Search similar users"""
        try:
            user_ids, scores = self.vector_store.search_vectors(
                "realtime_users", post_vector, k
            )
            logger.info(f"✅ Searched {len(user_ids)} users for post {post_vector}")
            return user_ids, scores
        except Exception as e:
            logger.error(f"❌ Failed to search users: {e}")
            return [], []

    # ==================== HELPER METHODS ====================

    def _validate_vector(self, vector: List[float]) -> bool:
        """Validate vector format and dimensions"""
        if not vector or not isinstance(vector, list):
            logger.error(f"❌ Invalid vector format: {vector}")
            return False
        if len(vector) != self.vector_store.dim_post:
            logger.error(f"❌ Invalid vector dimension: {len(vector)}")
            return False
        return True
