"""Collaborative filtering index builder (SQL-backed, no FAISS).

Calls PostgreSQL functions to refresh similarity and neighbour tables.
Actual vector search is handled by Qdrant.
"""
from loguru import logger


class IndexBuilder:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def build_indices(self, version: str = "v1"):
        self.refresh_similarities(version)
        self.refresh_neighbours(version)

    def refresh_similarities(self, version: str = "v1"):
        with self.db_connection as conn:
            conn.execute(
                "SELECT refresh_user_similarity(:version)", {"version": version}
            )
            conn.execute(
                "SELECT refresh_item_similarity(:version)", {"version": version}
            )
            conn.commit()
            logger.info(f"Refreshed user/item similarity tables (version={version})")

    def refresh_neighbours(self, version: str = "v1", k: int = 10):
        with self.db_connection as conn:
            conn.execute(
                "SELECT refresh_topk_user_neighbors(:version, :k)",
                {"version": version, "k": k},
            )
            conn.execute(
                "SELECT refresh_topk_item_neighbors(:version, :k)",
                {"version": version, "k": k},
            )
            conn.commit()
            logger.info(f"Refreshed top-{k} neighbour tables (version={version})")
