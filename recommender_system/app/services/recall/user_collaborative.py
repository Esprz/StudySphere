from collections import defaultdict
from typing import List, Dict, Any
from loguru import logger
from .base import RecallBase


class UserCollaborativeRecall(RecallBase):
    """Recall via user-user collaborative filtering.
    Reads from CF tables populated by the Offline Pipeline (Spec 4).
    Until then, returns empty results.
    """

    def __init__(self, vector_store=None, db=None):
        super().__init__(name="user_cf", vector_store=vector_store, db=db)

    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 50
    ) -> List[Dict[str, Any]]:
        if self.db is None:
            return []

        version = context.get("cf_version")
        per_neighbor_k = context.get("per_neighbor_k", 10)

        try:
            neighbors = self.db.get_user_topk_neighbors(user_id, k=10, version=version)
            if not neighbors:
                return []

            scores: Dict[str, float] = defaultdict(float)
            for neighbor in neighbors:
                sim = neighbor.get("similarity_score", 0.0)
                neighbor_id = neighbor.get("similar_user_id")
                if not neighbor_id:
                    continue
                items = self.db.get_user_topk_posts(
                    neighbor_id, k=per_neighbor_k, version=version
                )
                for item in items:
                    item_id = item.get("item_id")
                    if item_id:
                        scores[item_id] += sim * item.get("interest_score", 1.0)

            ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]
            return [
                {"item_id": item_id, "score": float(score), "source": self.name}
                for item_id, score in ranked
            ]
        except Exception as e:
            logger.error(f"UserCollaborativeRecall failed: {e}")
            return []
