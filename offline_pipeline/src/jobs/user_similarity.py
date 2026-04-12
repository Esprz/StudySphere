"""User-user similarity batch job."""

from __future__ import annotations

from typing import Any, Dict

from .base import OfflineJob
from .common import build_user_item_map, fetch_interactions, top_k_similarities


class UserSimilarityJob(OfflineJob):
    name = "user-similarity"

    def __init__(self, connection, cache, top_k: int):
        self.connection = connection
        self.cache = cache
        self.top_k = top_k

    def run(self) -> Dict[str, Any]:
        rows = fetch_interactions(self.connection)
        user_map = build_user_item_map(rows)
        similarities = top_k_similarities(user_map, self.top_k)

        for user_id, scored in similarities.items():
            payload = [
                {"user_id": other_id, "score": float(score)}
                for other_id, score in scored
            ]
            self.cache.set_json(f"offline:sim:user:{user_id}", payload, ttl_seconds=7200)

        return {"job": self.name, "count": len(similarities)}

