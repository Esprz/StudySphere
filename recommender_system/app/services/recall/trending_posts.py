from .base import RecallBase


class TrendingPostsRecall(RecallBase):
    def __init__(self, vector_store, postgres_store):
        super().__init__(
            name="trending_posts",
            vector_store=vector_store,
            postgres_store=postgres_store,
        )

    def get_candidates(self, k=50):
        candidates = []
        with self.postgres_store.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT item_id
                    FROM item_popularity
                    ORDER BY popularity_score DESC
                    LIMIT %s
                    """,
                    (k,),
                )
                rows = cursor.fetchall()
                candidates = [row[0] for row in rows]
        return candidates
