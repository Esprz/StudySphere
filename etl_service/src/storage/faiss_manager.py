import faiss
import numpy as np
from src.utils.utils import uuid_to_int64


class FaissManager:
    def __init__(self, dim_post=384, dim_user=384):
        self.post_index = faiss.IndexIDMap(faiss.IndexFlatL2(dim_post))
        self.user_index = faiss.IndexIDMap(faiss.IndexFlatL2(dim_user))

    # post vector methods
    def add_post_vector(self, post_id, vector):
        vec = np.array([vector], dtype=np.float32)
        self.post_index.add_with_ids(vec, np.array([uuid_to_int64(post_id)]))

    def update_post_vector(self, post_id, vector):
        vec = np.array([vector], dtype=np.float32)
        self.post_index.remove_ids(np.array([uuid_to_int64(post_id)]))
        self.post_index.add_with_ids(vec, np.array([uuid_to_int64(post_id)]))

    def delete_post_vector(self, post_id):
        self.post_index.remove_ids(np.array([uuid_to_int64(post_id)]))

    def get_post_vector(self, post_id):
        try:
            return self.post_index.reconstruct(uuid_to_int64(post_id)).tolist()
        except faiss.IndexIDMapError:
            return None

    def search_posts(self, user_vector, k=5):
        vec = np.array([user_vector], dtype=np.float32)
        D, I = self.post_index.search(vec, k)
        return I[0].tolist(), D[0].tolist()

    # user vector methods
    def add_user_vector(self, user_id, vector):
        vec = np.array([vector], dtype=np.float32)
        self.user_index.add_with_ids(vec, np.array([uuid_to_int64(user_id)]))

    def search_users(self, post_vector, k=5):
        vec = np.array([post_vector], dtype=np.float32)
        D, I = self.user_index.search(vec, k)
        return I[0].tolist(), D[0].tolist()
