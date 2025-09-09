from app.services.recall.base import RecallBase

class ItemCollaborativeRecall(RecallBase):
    def __init__(self):
        super().__init__(name = "item_collaborative")
    
    def get_candidates(self, user_id, entity_type="posts", context=None, k=50):
        candidates = []