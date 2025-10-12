from .base import RecallBase


class ColdStartRecall(RecallBase):
    def __init__(self, vector_store, db):
        super().__init__(name="cold_start", vector_store=vector_store, db=db)

    def get_candidates(self, k=50):
        candidates = []
        with self.db.get_connection() as conn:
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
