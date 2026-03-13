from typing import List, Dict, Any
from loguru import logger
from .base import RecallBase


class ContentBasedRecall(RecallBase):
    def __init__(self, vector_store, db=None):
        super().__init__(name="content_based", vector_store=vector_store, db=db)

    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 50
    ) -> List[Dict[str, Any]]:
        user_embedding = self.vector_store.get_user_vector(user_id)
        if user_embedding is None:
            logger.warning(f"No embedding found for user {user_id}")
            return []

        entity_type = context.get("entity_type", "posts")
        if entity_type == "posts":
            ids, scores = self.vector_store.search_posts(user_embedding, k)
        elif entity_type == "users":
            ids, scores = self.vector_store.search_users(user_embedding, k)
        else:
            return []

        return [
            {"item_id": item_id, "score": float(score), "source": self.name}
            for item_id, score in zip(ids, scores)
        ]
