"""Warm cached feeds from offline artifacts."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict

from .base import OfflineJob
from .common import build_user_item_map, fetch_interactions


class CacheWarmupJob(OfflineJob):
    name = "cache-warmup"

    def __init__(self, connection, cache, user_limit: int, fallback_limit: int):
        self.connection = connection
        self.cache = cache
        self.user_limit = user_limit
        self.fallback_limit = fallback_limit

    def run(self) -> Dict[str, Any]:
        rows = fetch_interactions(self.connection)
        user_map = build_user_item_map(rows)

        active_users = sorted(
            user_map.items(),
            key=lambda item: sum(item[1].values()),
            reverse=True,
        )[: self.user_limit]

        warmed = 0
        fallback = self.cache.client.get("offline:trending:global")

        for user_id, interactions in active_users:
            scores: Dict[str, float] = defaultdict(float)
            seen_posts = set(interactions)

            for post_id, weight in interactions.items():
                similar_items = self.cache.client.get(f"offline:sim:item:{post_id}")
                if not similar_items:
                    continue
                for item in __import__("json").loads(similar_items):
                    candidate_id = item["post_id"]
                    if candidate_id in seen_posts:
                        continue
                    scores[candidate_id] += float(item["score"]) * weight

            ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
            payload = [
                {"post_id": post_id, "score": float(score), "source": "offline_cf"}
                for post_id, score in ranked[: self.fallback_limit]
            ]

            if not payload and fallback:
                payload = __import__("json").loads(fallback)[: self.fallback_limit]

            if payload:
                self.cache.set_json(f"rec:feed:{user_id}", payload, ttl_seconds=3600)
                warmed += 1

        return {"job": self.name, "count": warmed}

