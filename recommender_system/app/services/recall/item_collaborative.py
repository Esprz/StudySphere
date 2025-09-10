from services.recall.base import RecallBase


class ItemCollaborativeRecall(RecallBase):
    def __init__(self):
        super().__init__(name="item_copllaborative")

    def get_candidates(self, user_id, k=50, version="v1"):
        # 1) seed items with scores
        seeds = self.postgres_store.get_user_topk_posts(user_id, k=10, version=version)
        if not seeds:
            return []

        seed_ids = [s["post_id"] for s in seeds]
        seed_interest = {s["post_id"]: float(s["interest_score"] or 0.0) for s in seeds}

        # 2) batch fetch top-k similars for all seeds
        rows = self.postgres_store.get_items_topk_similar_items(
            seed_ids, per_seed_k=10, version=version
        )

        # 3) filter out already-interacted
        seen = set(
            self.postgres_store.get_user_interacted_item_ids(user_id, version=version)
        )
        seed_set = set(seed_ids)

        # 4) aggregate scores (max path score; switch to += to sum)
        from collections import defaultdict

        scores = defaultdict(float)
        for r in rows:
            seed = r["seed_item_id"]
            tgt = r["similar_item_id"]
            if tgt in seed_set or tgt in seen:
                continue
            path_score = seed_interest.get(seed, 0.0) * float(
                r["similarity_score"] or 0.0
            )
            if path_score > scores[tgt]:
                scores[tgt] = path_score

        # 5) rank & cut
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [item_id for item_id, _ in ranked]
