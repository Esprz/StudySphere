from typing import Any, Dict, List, Optional
from .embeddings.text_embedder import TextEmbedder
from .embeddings.post_embedder import PostEmbedder
from .embeddings.user_embedder import UserEmbedder
from src.producers.embedding_producer import EmbeddingProducer
from loguru import logger


class EventProcessor:
    """Unified event processing coordinator"""

    def __init__(
        self, vector_store, postgres_store, model_name: str = "all-MiniLM-L6-v2"
    ):
        self.vector_store = vector_store
        self.postgres_store = postgres_store

        self.text_embedder = TextEmbedder(model_name)
        self.post_embedder = PostEmbedder(vector_store, self.text_embedder)
        self.user_embedder = UserEmbedder(vector_store, self.text_embedder)

        try:
            self.embedding_producer = EmbeddingProducer()
        except Exception as e:
            logger.warning(f"EmbeddingProducer unavailable: {e}")
            self.embedding_producer = None

    # ==================== USER EVENTS ====================

    def process_user_created(self, user_id: str) -> bool:
        """Process user creation event"""
        return self.user_embedder.init_user_embedding(user_id)

    def process_user_updated(self, user_id: str, updated_data: dict = None) -> bool:
        """Process user update event"""
        # Currently not processing user info updates affecting embeddings
        logger.info(f"✅ User {user_id} updated (embedding unchanged)")
        return True

    def process_user_deleted(self, user_id: str) -> bool:
        """Process user deletion event"""
        # TODO: Implement user embedding deletion
        logger.info(
            f"✅ User {user_id} deleted (TODO: implement user embedding deletion)"
        )
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
        event_id: str = None,
        session_id: str = None,
        source: str = None,
        extra_data: Dict[str, Any] = None,
    ) -> bool:
        post_success = self.post_embedder.process_post_created(
            post_id, title, content, tags
        )
        if post_success:
            self._notify_embedding_updated("post", post_id)

        user_success = True
        if post_success and author_id and timestamp:
            user_success = self.user_embedder.update_from_post_interaction(
                author_id, post_id, "POST_CREATED", timestamp
            )
            if user_success:
                self._notify_embedding_updated("user", author_id)

            self.postgres_store.store_behavior_event(
                user_id=author_id,
                post_id=post_id,
                event_type="POST_CREATED",
                event_id=event_id,
                session_id=session_id,
                source=source,
                extra_data=extra_data,
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
        event_id: str = None,
        session_id: str = None,
        source: str = None,
        extra_data: Dict[str, Any] = None,
    ) -> bool:
        post_success = self.post_embedder.process_post_updated(
            post_id, title, content, tags
        )
        if post_success:
            self._notify_embedding_updated("post", post_id)

        user_success = True
        if post_success and author_id and timestamp:
            user_success = self.user_embedder.update_from_post_interaction(
                author_id, post_id, "POST_UPDATED", timestamp
            )
            if user_success:
                self._notify_embedding_updated("user", author_id)

            self.postgres_store.store_behavior_event(
                user_id=author_id,
                post_id=post_id,
                event_type="POST_UPDATED",
                event_id=event_id,
                session_id=session_id,
                source=source,
                extra_data=extra_data,
            )

        return post_success and user_success

    def process_post_deleted(self, post_id: str) -> bool:
        """Process post deletion event"""
        return self.post_embedder.process_post_deleted(post_id)

    # ==================== BEHAVIOR EVENTS ====================

    def process_post_interaction(
        self,
        user_id: str,
        post_id: str,
        behavior_type: str,
        timestamp: str,
        event_id: str = None,
        session_id: str = None,
        position: int = None,
        dwell_ms: int = None,
        source: str = None,
        extra_data: Dict[str, Any] = None,
    ) -> bool:
        success = self.user_embedder.update_from_post_interaction(
            user_id, post_id, behavior_type, timestamp
        )
        if success:
            self._notify_embedding_updated("user", user_id)
            self.postgres_store.store_behavior_event(
                user_id=user_id,
                post_id=post_id,
                event_type=behavior_type,
                event_id=event_id,
                session_id=session_id,
                position=position,
                dwell_ms=dwell_ms,
                source=source,
                extra_data=extra_data,
            )
        return success

    def process_search_behavior(
        self,
        user_id: str,
        search_query: str,
        timestamp: str,
        event_id: str = None,
        session_id: str = None,
        source: str = None,
        extra_data: Dict[str, Any] = None,
    ) -> bool:
        success = self.user_embedder.update_from_search(user_id, search_query, timestamp)
        if success:
            self._notify_embedding_updated("user", user_id)
            self.postgres_store.store_behavior_event(
                user_id=user_id,
                event_type="SEARCH_PERFORMED",
                search_term=search_query,
                event_id=event_id,
                session_id=session_id,
                source=source,
                extra_data=extra_data,
            )
        return success

    def process_comment_created(
        self,
        user_id: str,
        post_id: str,
        comment_id: str,
        timestamp: str,
        event_id: str = None,
        session_id: str = None,
        source: str = None,
        extra_data: Dict[str, Any] = None,
    ) -> bool:
        success = self.user_embedder.update_from_post_interaction(
            user_id, post_id, "POST_COMMENTED", timestamp
        )
        if success:
            self._notify_embedding_updated("user", user_id)

        self.postgres_store.store_behavior_event(
            user_id=user_id,
            post_id=post_id,
            event_type="COMMENT_CREATED",
            event_id=event_id,
            session_id=session_id,
            source=source,
            extra_data={
                "commentId": comment_id,
                **(extra_data or {}),
            },
        )
        return success

    def process_aux_behavior(
        self,
        user_id: str,
        event_type: str,
        event_id: str = None,
        post_id: str = None,
        search_term: str = None,
        session_id: str = None,
        source: str = None,
        extra_data: Dict[str, Any] = None,
    ) -> bool:
        stored = self.postgres_store.store_behavior_event(
            user_id=user_id,
            post_id=post_id,
            event_type=event_type,
            search_term=search_term,
            event_id=event_id,
            session_id=session_id,
            source=source,
            extra_data=extra_data,
        )
        return stored

    # ==================== UTILITY METHODS ====================

    def _notify_embedding_updated(
        self,
        entity_type: str,
        entity_id: str,
        source_event_id: str | None = None,
    ):
        if self.embedding_producer:
            try:
                self.embedding_producer.publish(
                    entity_type,
                    entity_id,
                    source_event_id=source_event_id,
                )
            except Exception as e:
                logger.warning(f"Failed to publish embedding update: {e}")

    def get_post_embedding(self, post_id: str) -> Optional[List[float]]:
        return self.post_embedder.get_post_embedding(post_id)

    def get_user_embedding(self, user_id: str) -> Optional[List[float]]:
        return self.user_embedder.get_user_embedding(user_id)

    def generate_text_embedding(self, text: str) -> Optional[List[float]]:
        return self.text_embedder.generate_embedding(text)
