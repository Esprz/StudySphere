from typing import List, Optional, Dict, Any
from .faiss_manager import FaissManager
import time


class VectorStore:
    """High-level vector storage with business logic"""

    def __init__(self, faiss_manager: FaissManager):
        self.faiss = faiss_manager
        self._post_cache = {}  # Simple in-memory cache
        self._user_cache = {}
        self.cache_ttl = 300  # 5 minutes

    # ==================== POST VECTORS ====================

    def add_post_vector(self, post_id: str, vector: List[float]) -> bool:
        """Add post vector with business logic"""
        try:
            # Validate vector
            if not self._validate_vector(vector):
                print(f"Invalid vector for post {post_id}")
                return False

            # Add to Faiss
            self.faiss.add_vector(self.faiss.post_index, post_id, vector)

            # Update cache
            self._post_cache[post_id] = {"vector": vector, "timestamp": time.time()}

            # Save indexes
            self.faiss.save_indexes()

            print(f"✅ Added post vector for {post_id}")
            return True

        except Exception as e:
            print(f"❌ Error adding post vector {post_id}: {e}")
            return False

    def get_post_vector(self, post_id: str) -> Optional[List[float]]:
        """Get post vector with caching"""
        # Check cache first
        if post_id in self._post_cache:
            cache_entry = self._post_cache[post_id]
            if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                return cache_entry["vector"]

        # Get from Faiss
        vector = self.faiss.get_vector(self.faiss.post_index, post_id)

        # Update cache
        if vector:
            self._post_cache[post_id] = {"vector": vector, "timestamp": time.time()}

        return vector

    def update_post_vector(self, post_id: str, vector: List[float]) -> bool:
        """Update post vector"""
        try:
            if not self._validate_vector(vector):
                return False

            self.faiss.update_vector(self.faiss.post_index, post_id, vector)

            # Update cache
            self._post_cache[post_id] = {"vector": vector, "timestamp": time.time()}

            self.faiss.save_indexes()
            return True

        except Exception as e:
            print(f"❌ Error updating post vector {post_id}: {e}")
            return False

    def delete_post_vector(self, post_id: str) -> bool:
        """Delete post vector"""
        try:
            self.faiss.delete_vector(self.faiss.post_index, post_id)

            # Remove from cache
            self._post_cache.pop(post_id, None)

            self.faiss.save_indexes()
            return True

        except Exception as e:
            print(f"❌ Error deleting post vector {post_id}: {e}")
            return False

    def search_posts(self, user_vector: List[float], k: int = 5) -> tuple:
        """Search similar posts"""
        return self.faiss.search_vectors(self.faiss.post_index, user_vector, k)

    # ==================== USER VECTORS ====================

    def add_user_vector(self, user_id: str, vector: List[float]) -> bool:
        """Add user vector with business logic"""
        try:
            if not self._validate_vector(vector):
                return False

            self.faiss.add_vector(self.faiss.user_index, user_id, vector)

            self._user_cache[user_id] = {"vector": vector, "timestamp": time.time()}

            self.faiss.save_indexes()
            return True

        except Exception as e:
            print(f"❌ Error adding user vector {user_id}: {e}")
            return False

    def get_user_vector(self, user_id: str) -> Optional[List[float]]:
        """Get user vector with caching"""
        # Check cache
        if user_id in self._user_cache:
            cache_entry = self._user_cache[user_id]
            if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                return cache_entry["vector"]

        # Get from Faiss
        vector = self.faiss.get_vector(self.faiss.user_index, user_id)

        # Update cache
        if vector:
            self._user_cache[user_id] = {"vector": vector, "timestamp": time.time()}

        return vector

    def update_user_vector(self, user_id: str, vector: List[float]) -> bool:
        """Update user vector"""
        try:
            if not self._validate_vector(vector):
                return False

            self.faiss.update_vector(self.faiss.user_index, user_id, vector)

            self._user_cache[user_id] = {"vector": vector, "timestamp": time.time()}

            self.faiss.save_indexes()
            return True

        except Exception as e:
            print(f"❌ Error updating user vector {user_id}: {e}")
            return False

    def search_users(self, post_vector: List[float], k: int = 5) -> tuple:
        """Search similar users"""
        return self.faiss.search_vectors(self.faiss.user_index, post_vector, k)

    # ==================== UTILITY METHODS ====================

    def _validate_vector(self, vector: List[float]) -> bool:
        """Validate vector format and dimensions"""
        if not vector or not isinstance(vector, list):
            return False

        if len(vector) != 384:  # Expected dimension
            return False

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        return {
            "post_count": self.faiss.post_index.ntotal,
            "user_count": self.faiss.user_index.ntotal,
            "post_cache_size": len(self._post_cache),
            "user_cache_size": len(self._user_cache),
        }

    def clear_cache(self):
        """Clear all caches"""
        self._post_cache.clear()
        self._user_cache.clear()
