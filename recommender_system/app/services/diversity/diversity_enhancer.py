from typing import List, Dict, Any
from .base import DiversityBase


class DiversityEnhancer(DiversityBase):
    def __init__(self, db=None, lambda_score: float = 0.8):
        super().__init__(name="diversity_enhancer")
        self.db = db
        self.lambda_score = lambda_score

    async def diversify(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        del user_id, context
        sorted_candidates = sorted(
            candidates, key=lambda x: float(x.get("score", 0.0)), reverse=True
        )
        if self.db is None or not sorted_candidates:
            return sorted_candidates[:limit]

        candidate_ids = [
            candidate["item_id"]
            for candidate in sorted_candidates
            if candidate.get("item_id")
        ]
        topic_map = self.db.get_post_topic_tags(candidate_ids)
        max_topic_share = max(1, int(limit * 0.4))

        selected: List[Dict[str, Any]] = []
        topic_counts: Dict[str, int] = {}
        remaining = list(sorted_candidates)

        while remaining and len(selected) < limit:
            best_idx = 0
            best_score = None

            for idx, candidate in enumerate(remaining):
                topics = topic_map.get(candidate.get("item_id"), [])
                topic_penalty = 0.0
                if topics:
                    overrepresented = max(topic_counts.get(topic, 0) for topic in topics)
                    topic_penalty = min(1.0, overrepresented / max_topic_share)
                blended = (
                    self.lambda_score * float(candidate.get("score", 0.0))
                    + (1 - self.lambda_score) * (1 - topic_penalty)
                )
                if best_score is None or blended > best_score:
                    best_score = blended
                    best_idx = idx

            picked = remaining.pop(best_idx)
            selected.append(picked)
            for topic in topic_map.get(picked.get("item_id"), []):
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        return selected
