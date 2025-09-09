from asyncio.log import logger
from app.services.recall.base import RecallBase

class ContentBasedRecall(RecallBase):
    def __init__(self):
        super().__init__(name = "content_based")
    
    def get_candidates(self, user_id, entity_type="posts", context=None, k=50):
        user_embedding = self.vector_store.get_user_embedding(user_id)
        candidates = []
        if user_embedding is None:
            logger.warning(f"No embedding found for user {user_id}")
            print(f"No embedding found for user {user_id}")
            return candidates
        if entity_type == "posts":
            post_ids, scores = self.vector_store.search_posts(user_embedding, k)
            candidates = [{"item_id": pid, "score": score} for pid, score in zip(post_ids, scores)]
        elif entity_type == "users":
            user_ids, scores = self.vector_store.search_users(user_embedding, k)
            candidates = [{"item_id": uid, "score": score} for uid, score in zip(user_ids, scores)]
        else:
            logger.error(f"Unknown entity_type {entity_type}")
            print(f"Unknown entity_type {entity_type}")
        return candidates
    
