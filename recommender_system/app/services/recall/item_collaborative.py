from collections import defaultdict
from typing import List, Dict, Any
from loguru import logger
from .base import RecallBase


class ItemCollaborativeRecall(RecallBase):
    """Recall via item-item collaborative filtering.
    Reads from CF tables populated by the Offline Pipeline (Spec 4).
    Until then, returns empty results.
    """

    def __init__(self, vector_store=None, db=None):
        super().__init__(name="item_collaborative", vector_store=vector_store, db=db)

    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 50
    ) -> List[Dict[str, Any]]:
        if self.db is None:
            return []

        version = context.get("cf_version", "v1")

        try:
            seed_item_ids = self.db.get_user_interacted_item_ids(
                user_id, version=version
            )
            if not seed_item_ids:
                return []

            similar_rows = self.db.get_items_topk_similar_items(
                seed_item_ids[-20:], per_seed_k=5, version=version
            )

            scores: Dict[str, float] = defaultdict(float)
            for row in similar_rows:
                item_id = row.get("similar_item_id")
                sim = row.get("similarity_score", 0.0)
                if item_id and item_id not in seed_item_ids:
                    scores[item_id] += sim

            ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]
            return [
                {"item_id": item_id, "score": float(score), "source": self.name}
                for item_id, score in ranked
            ]
        except Exception as e:
            logger.error(f"ItemCollaborativeRecall failed: {e}")
            return []
