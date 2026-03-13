from typing import List, Dict, Any
from loguru import logger
from .base import RecallBase


class FollowingActivityRecall(RecallBase):
    """Returns recent posts from users the current user follows.
    Requires follow data and post data in Postgres. Returns empty until
    the following_activity view or join is available (Spec 5).
    """

    def __init__(self, vector_store=None, db=None):
        super().__init__(name="following_activity", vector_store=vector_store, db=db)

    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 50
    ) -> List[Dict[str, Any]]:
        if self.db is None:
            return []

        try:
            session = self.db.get_session()
            with session.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT p.id as item_id, p.created_at
                    FROM posts p
                    JOIN follows f ON f.followee_id = p.user_id
                    WHERE f.follower_id = %s
                      AND p.created_at > NOW() - INTERVAL '7 days'
                    ORDER BY p.created_at DESC
                    LIMIT %s
                    """,
                    (user_id, k),
                )
                rows = cursor.fetchall()

            return [
                {"item_id": row["item_id"], "score": 0.5, "source": self.name}
                for row in rows
            ]
        except Exception as e:
            logger.error(f"FollowingActivityRecall failed: {e}")
            return []
