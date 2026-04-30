from typing import List, Dict, Any
from loguru import logger
from .base import RecallBase


class TrendingPostsRecall(RecallBase):
    """Returns globally trending posts. Used as fallback and for cold-start blending."""

    def __init__(self, vector_store=None, db=None):
        super().__init__(name="trending", vector_store=vector_store, db=db)

    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 50
    ) -> List[Dict[str, Any]]:
        del user_id
        if self.db is None:
            return []

        try:
            version = context.get("trending_version")
            rows = self.db.get_trending_posts(k=k, version=version)

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
