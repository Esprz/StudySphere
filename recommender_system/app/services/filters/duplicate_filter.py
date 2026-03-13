from typing import List, Dict, Any
from .base import FilterBase


class DuplicateFilter(FilterBase):
    def __init__(self):
        super().__init__(name="duplicate_filter")

    async def filter_candidates(
        self, user_id: str, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for candidate in candidates:
            item_id = candidate.get("item_id")
            if item_id and item_id not in seen:
                seen.add(item_id)
                unique.append(candidate)
        return unique
