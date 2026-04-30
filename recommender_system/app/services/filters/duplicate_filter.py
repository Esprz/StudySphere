from typing import List, Dict, Any
from .base import FilterBase


class DuplicateFilter(FilterBase):
    def __init__(self):
        super().__init__(name="duplicate_filter")

    async def filter_candidates(
        self, user_id: str, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        del user_id, context
        deduped: Dict[str, Dict[str, Any]] = {}

        for candidate in candidates:
            item_id = candidate.get("item_id")
            if not item_id:
                continue

            score = float(candidate.get("score", 0.0))
            source = candidate.get("source")
            sources = list(candidate.get("sources", []))
            if source:
                sources.append(source)

            existing = deduped.get(item_id)
            if existing is None:
                merged = dict(candidate)
                merged["sources"] = sorted(set(sources))
                deduped[item_id] = merged
                continue

            existing_sources = set(existing.get("sources", []))
            existing_source = existing.get("source")
            if existing_source:
                existing_sources.add(existing_source)
            existing_sources.update(sources)

            if score > float(existing.get("score", 0.0)):
                merged = dict(candidate)
                merged["sources"] = sorted(existing_sources)
                deduped[item_id] = merged
            else:
                existing["sources"] = sorted(existing_sources)

        return list(deduped.values())
