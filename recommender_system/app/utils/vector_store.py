from typing import List, Optional, Dict, Any
from .faiss_manager import FaissManager
from .postgres_store import PostgresStore
import time


class VectorStore:
    """High-level vector storage with unified CRUD operations"""

    def __init__(self, faiss_manager: FaissManager, postgres_store: PostgresStore):
        self.faiss = faiss_manager
        self.postgres = postgres_store
        self._cache = {}  # Unified cache
        self.cache_ttl = 300

    # ==================== UNIFIED CRUD METHODS ====================

    def add_vector(self, source_id: str, source_type: str, vector: List[float]) -> bool:
        """Unified method to add any type of vector"""
        try:
            if not self._validate_vector(vector):
                return False

            # 1. Store to PostgreSQL first (primary storage)
            pg_success = self.postgres.store_vector(
                source_id=source_id,
                source_type=source_type,
                vector_data=vector,
                vector_dimension=len(vector),
                faiss_indexed="pending",
                extra_data={"created_at": time.time()},
            )

            if not pg_success:
                print(f"Failed to store vector in PostgreSQL for {source_id}")
                return False

            # 2. Try to index in FAISS (performance layer)
            try:
                index = self._get_faiss_index(source_type)
                self.faiss.add_vector(index, source_id, vector)
                self.faiss.save_indexes()

                # Mark as successfully indexed
                self.postgres.mark_faiss_indexed(source_id, source_type, True)

                # Update cache
                self._update_cache(source_id, source_type, vector)

                print(f"Added {source_type} vector for {source_id} (PG + FAISS)")
                return True

            except Exception as faiss_error:
                print(f"FAISS indexing failed for {source_id}: {faiss_error}")
                self.postgres.mark_faiss_indexed(source_id, source_type, False)
                print(f"Added {source_type} vector for {source_id} (PG only)")
                return True  # Still success since PostgreSQL worked

        except Exception as e:
            print(f"Error adding {source_type} vector {source_id}: {e}")
            return False

    def get_vector(self, source_id: str, source_type: str) -> Optional[List[float]]:
        """Unified method to get any type of vector"""
        cache_key = f"{source_type}:{source_id}"

        # 1. Check cache first
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                return cache_entry["vector"]

        # 2. Try FAISS first (fast)
        try:
            index = self._get_faiss_index(source_type)
            vector = self.faiss.get_vector(index, source_id)
            if vector:
                self._update_cache(source_id, source_type, vector)
                return vector
        except Exception as faiss_error:
            print(f"FAISS lookup failed for {source_id}: {faiss_error}")

        # 3. Fallback to PostgreSQL (reliable)
        try:
            pg_vector = self.postgres.get_vector(source_id, source_type)
            if pg_vector and pg_vector.vector_data:
                vector = pg_vector.vector_data

                # Try to reindex to FAISS
                if pg_vector.faiss_indexed != "indexed":
                    self._reindex_to_faiss(source_id, source_type, vector)

                self._update_cache(source_id, source_type, vector)
                return vector
        except Exception as pg_error:
            print(f"PostgreSQL lookup failed for {source_id}: {pg_error}")

        return None

    def update_vector(
        self, source_id: str, source_type: str, vector: List[float]
    ) -> bool:
        """Unified method to update any type of vector"""
        try:
            if not self._validate_vector(vector):
                return False

            # 1. Update PostgreSQL first
            pg_success = self.postgres.update_vector(
                source_id=source_id,
                source_type=source_type,
                vector_data=vector,
                vector_dimension=len(vector),
                faiss_indexed="pending",
                extra_data={"updated_at": time.time()},
            )

            if not pg_success:
                print(f"Failed to update vector in PostgreSQL for {source_id}")
                return False

            # 2. Update FAISS
            try:
                index = self._get_faiss_index(source_type)
                self.faiss.update_vector(index, source_id, vector)
                self.faiss.save_indexes()

                self.postgres.mark_faiss_indexed(source_id, source_type, True)

                # Update cache
                self._update_cache(source_id, source_type, vector)

                print(f"Updated {source_type} vector for {source_id}")
                return True

            except Exception as faiss_error:
                print(f"FAISS update failed for {source_id}: {faiss_error}")
                self.postgres.mark_faiss_indexed(source_id, source_type, False)
                return True  # PostgreSQL update still succeeded

        except Exception as e:
            print(f"Error updating {source_type} vector {source_id}: {e}")
            return False

    def delete_vector(self, source_id: str, source_type: str) -> bool:
        """Unified method to delete any type of vector"""
        try:
            # 1. Delete from FAISS
            try:
                index = self._get_faiss_index(source_type)
                self.faiss.delete_vector(index, source_id)
                self.faiss.save_indexes()
            except Exception as faiss_error:
                print(f"FAISS delete failed for {source_id}: {faiss_error}")

            # 2. Delete from PostgreSQL
            success = self.postgres.delete_vector(source_id, source_type)

            # 3. Remove from cache
            cache_key = f"{source_type}:{source_id}"
            self._cache.pop(cache_key, None)

            if success:
                print(f"Deleted {source_type} vector for {source_id}")

            return success

        except Exception as e:
            print(f"Error deleting {source_type} vector {source_id}: {e}")
            return False

    # ==================== CONVENIENCE METHODS ====================

    def add_post_vector(self, post_id: str, vector: List[float]) -> bool:
        """Convenience method for adding post vectors"""
        return self.add_vector(post_id, "post", vector)

    def get_post_vector(self, post_id: str) -> Optional[List[float]]:
        """Convenience method for getting post vectors"""
        return self.get_vector(post_id, "post")

    def update_post_vector(self, post_id: str, vector: List[float]) -> bool:
        """Convenience method for updating post vectors"""
        return self.update_vector(post_id, "post", vector)

    def delete_post_vector(self, post_id: str) -> bool:
        """Convenience method for deleting post vectors"""
        return self.delete_vector(post_id, "post")

    def add_user_vector(self, user_id: str, vector: List[float]) -> bool:
        """Convenience method for adding user vectors"""
        return self.add_vector(user_id, "user", vector)

    def get_user_vector(self, user_id: str) -> Optional[List[float]]:
        """Convenience method for getting user vectors"""
        return self.get_vector(user_id, "user")

    def update_user_vector(self, user_id: str, vector: List[float]) -> bool:
        """Convenience method for updating user vectors"""
        return self.update_vector(user_id, "user", vector)

    def delete_user_vector(self, user_id: str) -> bool:
        """Convenience method for deleting user vectors"""
        return self.delete_vector(user_id, "user")

    # ==================== SEARCH METHODS ====================

    def search_posts(self, user_vector: List[float], k: int = 5) -> tuple:
        """Search similar posts"""
        return self.faiss.search_vectors(self.faiss.post_index, user_vector, k)

    def search_users(self, post_vector: List[float], k: int = 5) -> tuple:
        """Search similar users"""
        return self.faiss.search_vectors(self.faiss.user_index, post_vector, k)

    # ==================== HELPER METHODS ====================

    def _get_faiss_index(self, source_type: str):
        """Get appropriate FAISS index for source type"""
        if source_type == "post":
            return self.faiss.post_index
        elif source_type == "user":
            return self.faiss.user_index
        else:
            raise ValueError(f"Unknown source type: {source_type}")

    def _update_cache(self, source_id: str, source_type: str, vector: List[float]):
        """Update unified cache"""
        cache_key = f"{source_type}:{source_id}"
        self._cache[cache_key] = {"vector": vector, "timestamp": time.time()}

    def _reindex_to_faiss(self, source_id: str, source_type: str, vector: List[float]):
        """Reindex vector to FAISS in background"""
        try:
            index = self._get_faiss_index(source_type)
            self.faiss.add_vector(index, source_id, vector)
            self.faiss.save_indexes()
            self.postgres.mark_faiss_indexed(source_id, source_type, True)
            print(f"Reindexed {source_id} to FAISS")
        except Exception as e:
            print(f"Failed to reindex {source_id} to FAISS: {e}")
            self.postgres.mark_faiss_indexed(source_id, source_type, False)

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
            "cache_size": len(self._cache),
        }

    def clear_cache(self):
        """Clear all caches"""
        self._cache.clear()
