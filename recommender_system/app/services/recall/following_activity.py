from .base import RecallBase


class FollowingActivityRecall(RecallBase):
    def __init__(self, vector_store, db):
        super().__init__(
            name="following_activity",
            vector_store=vector_store,
            db=db,
        )

    def get_candidates(self, user_id, k=50):
        candidates = []
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT post_id
                    FROM following_activity
                    WHERE user_id = %s AND entity_type = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (user_id, "posts", k),
                )
                rows = cursor.fetchall()
                candidates = [row[0] for row in rows]
        return candidates
