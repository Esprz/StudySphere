from typing import List, Dict, Any
from loguru import logger
from .base import RecallBase


class TrendingPostsRecall(RecallBase):
    """Returns globally trending posts. Used as fallback and for cold-start blending."""

    def __init__(self, vector_store=None, db=None):
        super().__init__(name="trending_posts", vector_store=vector_store, db=db)

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
                    SELECT
                        p.post_id AS item_id,
                        (
                            COALESCE(l.like_count, 0) * 2
                            + COALESCE(s.save_count, 0) * 3
                            + COALESCE(c.comment_count, 0)
                        )::float AS popularity
                    FROM "Post" p
                    LEFT JOIN (
                        SELECT post_id, COUNT(*) AS like_count
                        FROM "Like"
                        GROUP BY post_id
                    ) l ON l.post_id = p.post_id
                    LEFT JOIN (
                        SELECT post_id, COUNT(*) AS save_count
                        FROM "Save"
                        GROUP BY post_id
                    ) s ON s.post_id = p.post_id
                    LEFT JOIN (
                        SELECT post_id, COUNT(*) AS comment_count
                        FROM "Comment"
                        GROUP BY post_id
                    ) c ON c.post_id = p.post_id
                    ORDER BY popularity DESC, p.created_at DESC
                    LIMIT %s
                    """,
                    (k,),
                )
                rows = cursor.fetchall()

            return [
                {
                    "item_id": row["item_id"],
                    "score": float(row.get("popularity", 0.0)),
                    "source": self.name,
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"TrendingPostsRecall failed: {e}")
            return []
