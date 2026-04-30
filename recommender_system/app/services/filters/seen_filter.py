from typing import List, Dict, Any
from .base import FilterBase


class SeenFilter(FilterBase):
    def __init__(self, db=None, redis=None):
        super().__init__(name="seen_filter")
        self.db = db
        self.redis = redis

    async def filter_candidates(
        self, user_id: str, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        seen_items = await self._get_seen_items(user_id)
        return [c for c in candidates if c.get("item_id") not in seen_items]

    async def _get_seen_items(self, user_id: str) -> set:
        cache_key = f"rec:seen:{user_id}"

        if self.redis:
            cached = await self.redis.get(cache_key)
            if isinstance(cached, list):
                return set(cached)

        if self.db is None:
            return set()

        seen_items = self.db.get_seen_items_last_days(user_id, days=30)

        if self.redis:
            await self.redis.set(cache_key, list(seen_items), ttl=600)

        return seen_items
