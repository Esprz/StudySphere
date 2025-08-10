from typing import List, Optional
from .text_embedder import TextEmbedder


class PostEmbedder:
    """Post embedding processor"""

    def __init__(self, vector_store, text_embedder: TextEmbedder = None):
        self.vector_store = vector_store
        self.text_embedder = text_embedder or TextEmbedder()

    def generate_post_embedding(
        self, title: str, content: str, tags: List[str] = None
    ) -> Optional[List[float]]:
        """
        Generate post embedding by combining title, content and tags
        Uses separator tokens to distinguish different parts
        """
        text_parts = []

        if title and title.strip():
            text_parts.append(title.strip())

        if content and content.strip():
            text_parts.append(content.strip())

        if tags:
            tag_text = " ".join([tag.strip() for tag in tags if tag.strip()])
            if tag_text:
                text_parts.append(tag_text)

        if not text_parts:
            print("No valid content for post embedding")
            return None

        # Use special separator to join different parts
        full_text = " [SEP] ".join(text_parts)
        return self.text_embedder.generate_embedding(full_text)

    def process_post_created(
        self, post_id: str, title: str, content: str, tags: List[str] = None
    ) -> bool:
        """Process post creation event"""
        try:
            embedding = self.generate_post_embedding(title, content, tags)
            if not embedding:
                print(f"Failed to generate embedding for post {post_id}")
                return False

            # Store in vector store
            self.vector_store.add_post_vector(post_id, embedding)
            print(f"✅ Stored post embedding for {post_id}")
            return True

        except Exception as e:
            print(f"❌Error processing post created {post_id}: {e}")
            return False

    def process_post_updated(
        self, post_id: str, title: str, content: str, tags: List[str] = None
    ) -> bool:
        """Process post update event"""
        try:
            embedding = self.generate_post_embedding(title, content, tags)
            if not embedding:
                print(f"Failed to generate embedding for updated post {post_id}")
                return False

            # Update vector in vector store
            self.vector_store.update_post_vector(post_id, embedding)
            print(f"✅ Updated post embedding for {post_id}")
            return True

        except Exception as e:
            print(f"❌Error processing post updated {post_id}: {e}")
            return False

    def process_post_deleted(self, post_id: str) -> bool:
        """Process post deletion event"""
        try:
            self.vector_store.delete_post_vector(post_id)
            print(f"✅ Deleted post embedding for {post_id}")
            return True
        except Exception as e:
            print(f"❌Error deleting post embedding {post_id}: {e}")
            return False

    def get_post_embedding(self, post_id: str) -> Optional[List[float]]:
        """Get post embedding from vector store"""
        try:
            return self.vector_store.get_post_vector(post_id)
        except Exception as e:
            print(f"❌Error getting post embedding {post_id}: {e}")
            return None
