from typing import List, Optional
from .embeddings.text_embedder import TextEmbedder
from .embeddings.post_embedder import PostEmbedder
from .embeddings.user_embedder import UserEmbedder


class EventProcessor:
    """Unified event processing coordinator"""

    def __init__(self, faiss_manager, db_config, model_name: str = "all-MiniLM-L6-v2"):
        # Initialize base components
        self.faiss = faiss_manager
        self.db = db_config

        # Initialize embedder components
        self.text_embedder = TextEmbedder(model_name)
        self.post_embedder = PostEmbedder(faiss_manager, self.text_embedder)
        self.user_embedder = UserEmbedder(faiss_manager, self.text_embedder)

    # ==================== USER EVENTS ====================

    def process_user_created(self, user_id: str) -> bool:
        """Process user creation event"""
        return self.user_embedder.init_user_embedding(user_id)

    def process_user_updated(self, user_id: str, updated_data: dict = None) -> bool:
        """Process user update event"""
        # Currently not processing user info updates affecting embeddings
        print(f"✅ User {user_id} updated (embedding unchanged)")
        return True

    def process_user_deleted(self, user_id: str) -> bool:
        """Process user deletion event"""
        # TODO: Implement user embedding deletion
        print(f"✅ User {user_id} deleted (TODO: implement user embedding deletion)")
        return True

    # ==================== POST EVENTS ====================

    def process_post_created(
        self,
        post_id: str,
        title: str,
        content: str,
        tags: List[str] = None,
        author_id: str = None,
        timestamp: str = None,
    ) -> bool:
        """Process post creation event"""
        # 1. Process post embedding
        post_success = self.post_embedder.process_post_created(
            post_id, title, content, tags
        )

        # 2. If author info available, update author embedding
        user_success = True
        if post_success and author_id and timestamp:
            user_success = self.user_embedder.update_from_post_interaction(
                author_id, post_id, "POST_CREATED", timestamp
            )

        return post_success and user_success

    def process_post_updated(
        self,
        post_id: str,
        title: str,
        content: str,
        tags: List[str] = None,
        author_id: str = None,
        timestamp: str = None,
    ) -> bool:
        """Process post update event"""
        # 1. Update post embedding
        post_success = self.post_embedder.process_post_updated(
            post_id, title, content, tags
        )

        # 2. If author info available, update author embedding
        user_success = True
        if post_success and author_id and timestamp:
            user_success = self.user_embedder.update_from_post_interaction(
                author_id, post_id, "POST_CREATED", timestamp
            )

        return post_success and user_success

    def process_post_deleted(self, post_id: str) -> bool:
        """Process post deletion event"""
        return self.post_embedder.process_post_deleted(post_id)

    # ==================== BEHAVIOR EVENTS ====================

    def process_post_interaction(
        self, user_id: str, post_id: str, behavior_type: str, timestamp: str
    ) -> bool:
        """Process user-post interaction behavior"""
        return self.user_embedder.update_from_post_interaction(
            user_id, post_id, behavior_type, timestamp
        )

    def process_search_behavior(
        self, user_id: str, search_query: str, timestamp: str
    ) -> bool:
        """Process search behavior"""
        return self.user_embedder.update_from_search(user_id, search_query, timestamp)

    # ==================== UTILITY METHODS ====================

    def get_post_embedding(self, post_id: str) -> Optional[List[float]]:
        """Get post embedding"""
        return self.post_embedder.get_post_embedding(post_id)

    def get_user_embedding(self, user_id: str) -> Optional[List[float]]:
        """Get user embedding"""
        return self.user_embedder.get_user_embedding(user_id)

    def generate_text_embedding(self, text: str) -> Optional[List[float]]:
        """Generate text embedding"""
        return self.text_embedder.generate_embedding(text)
