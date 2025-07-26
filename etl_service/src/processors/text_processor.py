from sentence_transformers import SentenceTransformer
import torch


class TextProcessor:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.model.eval()  # Disable dropout, etc.

    def generate_post_embedding(
        self, title: str, content: str, tags: list[str] = None
    ) -> list[float]:
        """
        Generate a semantic embedding for a post given its title, content, and optional tags.

        Returns: List[float] of dimension 384 (SBERT default)
        """
        # 1. Join title + content + tags
        text_parts = [title.strip(), content.strip()]
        if tags:
            tag_text = " ".join(tags)
            text_parts.append(tag_text)

        full_text = " [SEP] ".join(text_parts)  # use separator for clarity

        # 2. Generate embedding
        with torch.no_grad():
            embedding = self.model.encode(full_text, normalize_embeddings=True)

        return embedding.tolist()  # for Faiss/PostgreSQL compatibility
