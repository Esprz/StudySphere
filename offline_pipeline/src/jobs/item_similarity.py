"""Item-item similarity batch job."""

from __future__ import annotations

from typing import Any, Dict

from .base import OfflineJob
from .common import (
    build_user_item_map,
    fetch_interactions,
    invert_interactions,
    top_k_similarities,
)


class ItemSimilarityJob(OfflineJob):
    name = "item-similarity"

    def __init__(self, connection, cache, top_k: int):
        self.connection = connection
        self.cache = cache
        self.top_k = top_k

    def run(self) -> Dict[str, Any]:
        rows = fetch_interactions(self.connection)
        user_map = build_user_item_map(rows)
        item_map = invert_interactions(user_map)
        similarities = top_k_similarities(item_map, self.top_k)

        for post_id, scored in similarities.items():
            payload = [
                {"post_id": other_id, "score": float(score)}
                for other_id, score in scored
            ]
            self.cache.set_json(f"offline:sim:item:{post_id}", payload, ttl_seconds=7200)

        return {"job": self.name, "count": len(similarities)}

