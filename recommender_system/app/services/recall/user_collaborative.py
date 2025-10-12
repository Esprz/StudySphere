from collections import defaultdict
from typing import List

from .base import RecallBase


class UserCollaborativeRecall(RecallBase):
    def __init__(self, vector_store, db):
        super().__init__(
            name="user_collaborative",
            vector_store=vector_store,
            db=db,
        )

    def get_candidates(
        self,
        user_id: str,
        k: int = 50,
        *,
        version: str = "v1",
        per_neighbor_k: int = 10,  # how many items to take from each neighbor
        aggregate: str = "sum",  # "sum" or "max"
    ) -> List[str]:

        # 1) similar users (neighbors) with similarity scores
        neighbors = self.db.get_user_topk_neighbors(user_id, k=k, version=version)
        if not neighbors:
            return []

        # 2) items the target user has already interacted with (filter out)
        seen_items = set(self.db.get_user_interacted_item_ids(user_id, version=version))

        # 3) aggregate scores from neighbors' favorite items
        scores = defaultdict(float)
        for nb in neighbors:
            nb_id = nb["similar_user_id"]
            sim = float(nb.get("similarity_score") or 0.0)
            if sim <= 0:
                continue

            # neighbor's top items with their interest scores
            nb_items = self.db.get_user_topk_posts(
                nb_id, k=per_neighbor_k, version=version
            )
            for row in nb_items:
                item_id = row["post_id"]
                if item_id in seen_items:
                    continue
                interest = float(row.get("interest_score") or 0.0)
                if interest <= 0:
                    continue

                contrib = sim * interest
                if contrib <= 0:
                    continue

                if aggregate == "max":
                    if contrib > scores[item_id]:
                        scores[item_id] = contrib
                else:  # default "sum"
                    scores[item_id] += contrib

        if not scores:
            return []

        # 4) rank & cut
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [item_id for item_id, _ in ranked]
