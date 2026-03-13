from abc import ABC, abstractmethod
from typing import List, Dict, Any


class DiversityBase(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def diversify(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        pass
