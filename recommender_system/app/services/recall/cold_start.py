from services.recall.base import RecallBase


class ColdStartRecall(RecallBase):
    def __init__(self):
        super().__init__(name="cold_start")

    def get_candidates(self, k=50):
        candidates = []
        with self.postgres_store.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT post_id
                    FROM posts
                    ORDER BY RANDOM()
                    LIMIT %s
                    """,
                    (k,),
                )
                rows = cursor.fetchall()
                candidates = [row[0] for row in rows]
        return candidates
