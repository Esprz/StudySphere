from typing import List, Dict, Any
from .base import FilterBase


class SeenFilter(FilterBase):
    def __init__(self):
        super().__init__(name="seen_filter")

    async def filter_candidates(
        self, user_id: str, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        seen_items = self._get_seen_items(user_id)
        return [c for c in candidates if c.get("item_id") not in seen_items]

    def _get_seen_items(self, user_id: str) -> set:
        # Placeholder: returns empty set. Full implementation in Spec 5
        # (query etl_behavior_events for POST_VIEWED by this user).
        return set()
