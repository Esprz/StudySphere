from abc import ABC, abstractmethod
from typing import List, Dict, Any


class FilterBase(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def filter_candidates(
        self, user_id: str, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        pass
