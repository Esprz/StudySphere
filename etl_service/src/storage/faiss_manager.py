import faiss
import numpy as np
import os
from src.utils.utils import uuid_to_int64


class FaissManager:
    """Low-level Faiss index operations"""

    def __init__(self, dim_post=384, dim_user=384, persist_dir="./faiss_data"):
        self.persist_dir = persist_dir
        self.post_index_path = os.path.join(persist_dir, "post_index.faiss")
        self.user_index_path = os.path.join(persist_dir, "user_index.faiss")

        os.makedirs(persist_dir, exist_ok=True)

        self.post_index = self._load_or_create_index(self.post_index_path, dim_post)
        self.user_index = self._load_or_create_index(self.user_index_path, dim_user)

        print(
            f"📊 Faiss loaded - Posts: {self.post_index.ntotal}, Users: {self.user_index.ntotal}"
        )

    def _load_or_create_index(self, path: str, dim: int):
        """Load existing index or create new one"""
        if os.path.exists(path):
            try:
                return faiss.read_index(path)
            except Exception as e:
                print(f"❌Error loading index from {path}: {e}")

        return faiss.IndexIDMap(faiss.IndexFlatL2(dim))

    def save_indexes(self):
        """Save both indexes to disk"""
        try:
            faiss.write_index(self.post_index, self.post_index_path)
            faiss.write_index(self.user_index, self.user_index_path)
        except Exception as e:
            print(f"❌Error saving indexes: {e}")

    # Raw Faiss operations - no business logic
    def add_vector(self, index, vector_id: str, vector: list):
        """Generic add vector operation"""
        vec = np.array([vector], dtype=np.float32)
        index.add_with_ids(vec, np.array([uuid_to_int64(vector_id)]))

    def update_vector(self, index, vector_id: str, vector: list):
        """Generic update vector operation"""
        vec = np.array([vector], dtype=np.float32)
        index.remove_ids(np.array([uuid_to_int64(vector_id)]))
        index.add_with_ids(vec, np.array([uuid_to_int64(vector_id)]))

    def delete_vector(self, index, vector_id: str):
        """Generic delete vector operation"""
        index.remove_ids(np.array([uuid_to_int64(vector_id)]))

    def get_vector(self, index, vector_id: str):
        """Generic get vector operation"""
        try:
            return index.reconstruct(uuid_to_int64(vector_id)).tolist()
        except (RuntimeError, Exception):
            return None

    def search_vectors(self, index, query_vector: list, k: int = 5):
        """Generic vector search operation"""
        vec = np.array([query_vector], dtype=np.float32)
        D, I = index.search(vec, k)
        return I[0].tolist(), D[0].tolist()
