from typing import List, Dict, Any
from loguru import logger
from .base import RecallBase


class ColdStartRecall(RecallBase):
    """Simple random-post fallback for cold-start users.
    Will be replaced by InterestAwareColdStart in Spec 5.
    """

    def __init__(self, vector_store=None, db=None):
        super().__init__(name="cold_start", vector_store=vector_store, db=db)

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
                    SELECT post_id AS item_id
                    FROM "Post"
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (k,),
                )
                rows = cursor.fetchall()

            return [
                {"item_id": row["item_id"], "score": 0.0, "source": self.name}
                for row in rows
            ]
        except Exception as e:
            logger.error(f"ColdStartRecall failed: {e}")
            return []
