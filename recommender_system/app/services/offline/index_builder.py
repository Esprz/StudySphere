import os
import numpy as np
import faiss
from loguru import logger


class IndexBuilder:
    def __init__(self, index_path, db_connection):
        self.index_path = index_path
        self.db_connection = db_connection
        os.makedirs(index_path, exist_ok=True)

    def build_indices(self):
        self.init_content_indices()
        self.init_collaborative_indices()

    def init_content_indices(self):
        with self.db_connection as conn:
            result = conn.execute(
                """
                SELECT source_id, source_type, vector_data FROM etl_processed_vectors
                """
            )
            post_vecs, post_ids = [], []
            user_vecs, user_ids = [], []
            search_vecs, search_ids = [], []

            for row in result:
                vec = np.array(row.vector_data, dtype=np.float32)
                if row.source_type == "post":
                    post_vecs.append(vec)
                    post_ids.append(row.source_id)
                elif row.source_type == "user":
                    user_vecs.append(vec)
                    user_ids.append(row.source_id)
                elif row.source_type == "search":
                    search_vecs.append(vec)
                    search_ids.append(row.source_id)

            if post_vecs:
                self._build_and_save_index(
                    np.vstack(post_vecs),
                    post_ids,
                    os.path.join(self.index_path, "post_index.faiss"),
                )
            if user_vecs:
                self._build_and_save_index(
                    np.vstack(user_vecs),
                    user_ids,
                    os.path.join(self.index_path, "user_index.faiss"),
                )
            if search_vecs:
                self._build_and_save_index(
                    np.vstack(search_vecs),
                    search_ids,
                    os.path.join(self.index_path, "search_index.faiss"),
                )
            conn.commit()

    def _build_and_save_index(self, vecs, ids, out_path):
        dim = vecs.shape[1]
        index = faiss.IndexIDMap(faiss.IndexFlatL2(dim))
        index.add_with_ids(vecs, np.array(ids))
        faiss.write_index(index, out_path)
        logger.info(f"✅ Saved FAISS index to {out_path}, size={index.ntotal}")

    def init_collaborative_indices(self, version="v1"):
        self.compute_user_user_similarity(version)
        self.compute_item_item_similarity(version)
        self.compute_top10_similar_items(version)
        self.compute_top10_similar_users(version)

    def compute_user_user_similarity(self, version="v1"):
        with self.db_connection as conn:
            conn.execute(
                "SELECT refresh_user_similarity(:version)", {"version": version}
            )
            conn.commit()

    def compute_item_item_similarity(self, version="v1"):
        with self.db_connection as conn:
            conn.execute(
                "SELECT refresh_item_similarity(:version)", {"version": version}
            )
            conn.commit()

    def compute_top10_similar_items(self, version="v1"):
        with self.db_connection as conn:
            conn.execute(
                "SELECT refresh_top10_similar_items(:version)", {"version": version}
            )
            conn.commit()

    def compute_top10_similar_users(self, version="v1"):
        with self.db_connection as conn:
            conn.execute(
                "SELECT refresh_top10_similar_users(:version)", {"version": version}
            )
            conn.commit()
