import numpy as np
from datetime import datetime
from typing import List, Optional
from .text_embedder import TextEmbedder


class UserEmbedder:
    """User embedding processor with temporal decay and behavior weighting"""

    def __init__(self, vector_store, text_embedder: TextEmbedder = None):
        self.vector_store = vector_store
        self.text_embedder = text_embedder or TextEmbedder()

        # Configuration parameters
        self.decay_rate = 0.95  # 5% decay per day
        self.learning_rate = 0.1  # Embedding update learning rate

        # Behavior weights for different user actions
        self.behavior_weights = {
            "POST_LIKED": 1.0,
            "POST_SAVED": 1.5,
            "POST_VIEWED": 0.3,
            "POST_CREATED": 2.0,
            "SEARCH_PERFORMED": 0.5,
            "POST_COMMENTED": 1.2,
        }

    def init_user_embedding(self, user_id: str) -> bool:
        """Initialize user embedding with global average or zero vector"""
        try:
            # Check if already exists
            if self.vector_store.get_user_vector(user_id):
                print(f"User {user_id} embedding already exists")
                return True

            # Initialize with zero vector (will be updated as user interacts)
            zero_embedding = np.zeros(
                self.text_embedder.embedding_dim, dtype=np.float32
            )

            # Store in vector store
            self.vector_store.add_user_vector(user_id, zero_embedding.tolist())
            print(f"✅ Initialized user embedding for {user_id} with zero vector")
            return True

        except Exception as e:
            print(f"Error initializing user embedding for {user_id}: {e}")
            return False

    def calculate_time_decay(self, timestamp: str) -> float:
        """Calculate time-based decay factor"""
        try:
            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            current_time = datetime.now(event_time.tzinfo)
            days_diff = (current_time - event_time).days

            # Exponential decay
            decay_factor = self.decay_rate**days_diff
            return max(decay_factor, 0.01)  # Minimum decay of 0.01
        except Exception as e:
            print(f"Error calculating time decay: {e}")
            return 1.0

    def update_user_embedding(
        self,
        user_id: str,
        target_vector: List[float],
        behavior_type: str,
        timestamp: str,
    ) -> bool:
        """Update user embedding using moving average approach"""
        try:
            # Get current user embedding
            current_embedding = self.vector_store.get_user_vector(user_id)
            if not current_embedding:
                # Initialize user embedding if not exists
                if not self.init_user_embedding(user_id):
                    return False
                current_embedding = self.vector_store.get_user_vector(user_id)

            # Calculate update weight
            time_decay = self.calculate_time_decay(timestamp)
            behavior_weight = self.behavior_weights.get(behavior_type, 0.5)
            update_weight = behavior_weight * time_decay * self.learning_rate

            # Update embedding using moving average
            target_vector = np.array(target_vector)
            current_embedding = np.array(current_embedding)

            new_embedding = current_embedding + update_weight * (
                target_vector - current_embedding
            )
            new_embedding = new_embedding / np.linalg.norm(new_embedding)

            # Update in vector store
            self.vector_store.update_user_vector(user_id, new_embedding.tolist())

            print(
                f"✅ Updated user {user_id} embedding from {behavior_type} (weight: {update_weight:.3f})"
            )
            return True

        except Exception as e:
            print(f"Error updating user embedding for {user_id}: {e}")
            return False

    def update_from_post_interaction(
        self, user_id: str, post_id: str, behavior_type: str, timestamp: str
    ) -> bool:
        """Update user embedding based on post interaction"""
        try:
            # Get post embedding
            post_vector = self.vector_store.get_post_vector(post_id)
            if not post_vector:
                print(f"Post vector not found for {post_id}")
                return False

            return self.update_user_embedding(
                user_id, post_vector, behavior_type, timestamp
            )

        except Exception as e:
            print(f"Error updating user embedding from post interaction: {e}")
            return False

    def update_from_search(
        self, user_id: str, search_query: str, timestamp: str
    ) -> bool:
        """Update user embedding based on search query"""
        try:
            # Generate search query embedding
            search_embedding = self.text_embedder.generate_embedding(search_query)
            if not search_embedding:
                print(f"Failed to generate search embedding for query: {search_query}")
                return False

            return self.update_user_embedding(
                user_id, search_embedding, "SEARCH_PERFORMED", timestamp
            )

        except Exception as e:
            print(f"Error updating user embedding from search: {e}")
            return False

    def get_user_embedding(self, user_id: str) -> Optional[List[float]]:
        """Get user embedding from vector store"""
        try:
            return self.vector_store.get_user_vector(user_id)
        except Exception as e:
            print(f"Error getting user embedding for {user_id}: {e}")
            return None
