from services.recall.base import RecallBase


class TrendingPostsRecall(RecallBase):
    def __init__(self):
        super().__init__(name="trending_posts")

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
