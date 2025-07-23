import faiss
import numpy as np


class FaissManager:
    def __init__(self, dim_post=384, dim_user=384):
        self.post_index = faiss.IndexIDMap(faiss.IndexFlatL2(dim_post))
        self.user_index = faiss.IndexIDMap(faiss.IndexFlatL2(dim_user))

    def add_post_vector(self, post_id, vector):
        vec = np.array([vector], dtype=np.float32)
        self.post_index.add_with_ids(vec, np.array([post_id]))

    def add_user_vector(self, user_id, vector):
        vec = np.array([vector], dtype=np.float32)
        self.user_index.add_with_ids(vec, np.array([user_id]))

    def search_posts(self, user_vector, k=5):
        vec = np.array([user_vector], dtype=np.float32)
        D, I = self.post_index.search(vec, k)
        return I[0].tolist(), D[0].tolist()

    def search_users(self, post_vector, k=5):
        vec = np.array([post_vector], dtype=np.float32)
        D, I = self.user_index.search(vec, k)
        return I[0].tolist(), D[0].tolist()
