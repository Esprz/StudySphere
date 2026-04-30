from typing import Any, Dict, List

from loguru import logger

from .base import RecallBase


class InterestAwareColdStartRecall(RecallBase):
    """Recall posts that align with a user's declared goal tags."""

    def __init__(self, vector_store=None, db=None):
        super().__init__(
            name="cold_start_interest", vector_store=vector_store, db=db
        )

    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 50
    ) -> List[Dict[str, Any]]:
        del context
        if self.db is None:
            return []

        try:
            goal_tags = self.db.get_user_goal_tags(user_id)
            if not goal_tags:
                return []

            rows = self.db.get_posts_matching_goal_tags(goal_tags, k=k)
            return [
                {
                    "item_id": row["item_id"],
                    "score": float(row.get("score", 0.0)),
                    "source": self.name,
                }
                for row in rows
            ]
        except Exception as exc:
            logger.error(f"InterestAwareColdStartRecall failed: {exc}")
            return []
