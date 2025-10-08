from typing import List, Optional
from .qdrant_manager import QdrantManager
from loguru import logger


class VectorStore:
    """High-level vector storage with unified CRUD operations"""

    def __init__(self, qdrant_manager: QdrantManager):
        self.qdrant = qdrant_manager

    # ==================== UNIFIED CRUD METHODS ====================

    def add_vector(self, source_id: str, source_type: str, vector: List[float]) -> bool:
        """Unified method to add any type of vector"""
        try:
            if not self._validate_vector(vector):
                logger.error(f"❌ Invalid vector format for {source_type} {source_id}")
                return False

            self.qdrant.add_vector(source_type, source_id, vector)
            logger.info(f"✅ Added {source_type} vector {source_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to add {source_type} vector {source_id}: {e}")
            return False

    def get_vector(self, source_id: str, source_type: str) -> Optional[List[float]]:
        """Unified method to get any type of vector"""
        try:
            vector = self.qdrant.get_vector(source_type, source_id)
            if vector:
                logger.info(f"✅ Retrieved {source_type} vector {source_id}")
                return vector
        except Exception as e:
            logger.error(f"❌ Failed to get {source_type} vector {source_id}: {e}")

        return None

    def update_vector(
        self, source_id: str, source_type: str, vector: List[float]
    ) -> bool:
        """Unified method to update any type of vector"""
        try:
            if not self._validate_vector(vector):
                return False

            self.qdrant.update_vector(source_type, source_id, vector)
            logger.info(f"✅ Updated {source_type} vector {source_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to update {source_type} vector {source_id}: {e}")
            return False

    def delete_vector(self, source_id: str, source_type: str) -> bool:
        """Unified method to delete any type of vector"""
        try:
            self.qdrant.delete_vector(source_type, source_id)
            logger.info(f"✅ Deleted {source_type} vector {source_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete {source_type} vector {source_id}: {e}")
            return False

    # ==================== CONVENIENCE METHODS ====================

    def add_post_vector(self, post_id: str, vector: List[float]) -> bool:
        """Convenience method for adding post vectors"""
        return self.add_vector(post_id, "realtime_posts", vector)

    def get_post_vector(self, post_id: str) -> Optional[List[float]]:
        """Convenience method for getting post vectors"""
        return self.get_vector(post_id, "realtime_posts")

    def update_post_vector(self, post_id: str, vector: List[float]) -> bool:
        """Convenience method for updating post vectors"""
        return self.update_vector(post_id, "realtime_posts", vector)

    def delete_post_vector(self, post_id: str) -> bool:
        """Convenience method for deleting post vectors"""
        return self.delete_vector(post_id, "realtime_posts")

    def add_user_vector(self, user_id: str, vector: List[float]) -> bool:
        """Convenience method for adding user vectors"""
        return self.add_vector(user_id, "realtime_users", vector)

    def get_user_vector(self, user_id: str) -> Optional[List[float]]:
        """Convenience method for getting user vectors"""
        return self.get_vector(user_id, "realtime_users")

    def update_user_vector(self, user_id: str, vector: List[float]) -> bool:
        """Convenience method for updating user vectors"""
        return self.update_vector(user_id, "realtime_users", vector)

    def delete_user_vector(self, user_id: str) -> bool:
        """Convenience method for deleting user vectors"""
        return self.delete_vector(user_id, "realtime_users")

    # ==================== SEARCH METHODS ====================

    def search_posts(self, user_vector: List[float], k: int = 5) -> tuple:
        """Search similar posts"""
        return self.qdrant.search_vectors("realtime_posts", user_vector, k)

    def search_users(self, post_vector: List[float], k: int = 5) -> tuple:
        """Search similar users"""
        return self.qdrant.search_vectors("realtime_users", post_vector, k)

    # ==================== HELPER METHODS ====================

    def _validate_vector(self, vector: List[float]) -> bool:
        """Validate vector format and dimensions"""
        if not vector or not isinstance(vector, list):
            logger.error(f"❌ Invalid vector format: {vector}")
            return False
        if len(vector) != self.qdrant.dim_post:
            logger.error(f"❌ Invalid vector dimension: {len(vector)}")
            return False
        return True
