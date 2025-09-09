from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class RecallBase(ABC):

    def __init__(self, name: str, vector_store, postgres_store):

        self.name = name
        self.vector_store = vector_store
        self.postgres_store = postgres_store

    @abstractmethod
    def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 100
    ) -> List[Dict[str, Any]]:

        pass

    def process_candidates(
        self, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        processed = []
        for candidate in candidates:
            if "item_id" not in candidate:
                continue

            if "source" not in candidate:
                candidate["source"] = self.name

            processed.append(candidate)

        return processed

    def combine_candidates(
        self, candidate_lists: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        seen = set()
        combined = []

        for candidates in candidate_lists:
            for candidate in candidates:
                item_id = candidate.get("item_id")
                if item_id and item_id not in seen:
                    seen.add(item_id)
                    combined.append(candidate)

        return combined

    def get_info(self) -> Dict[str, Any]:

        return {"name": self.name, "type": self.__class__.__name__}
