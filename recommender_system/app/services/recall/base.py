from abc import ABC, abstractmethod
from typing import List, Dict, Any


class RecallBase(ABC):
    def __init__(self, name: str, vector_store=None, db=None):
        self.name = name
        self.vector_store = vector_store
        self.db = db

    @abstractmethod
    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 100
    ) -> List[Dict[str, Any]]:
        """Returns [{"item_id": str, "score": float, "source": str}]"""
        pass

    def get_info(self) -> Dict[str, Any]:
        return {"name": self.name, "type": self.__class__.__name__}
