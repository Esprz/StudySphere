import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import re


class TextEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.model.eval()
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def preprocess_text(self, text: str) -> str:
        if not text:
            return ""

        # remove extra spaces, and non-alphanumeric characters
        text = re.sub(r"\s+", " ", text.strip())
        text = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", text)
        return text

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text"""
        processed_text = self.preprocess_text(text)
        if not processed_text:
            return None

        try:
            with torch.no_grad():
                embedding = self.model.encode(processed_text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            return None

    def generate_batch_embeddings(
        self, texts: List[str]
    ) -> List[Optional[List[float]]]:
        """Generate embeddings for a batch of texts"""
        processed_texts = [self.preprocess_text(text) for text in texts]
        valid_texts = [text for text in processed_texts if text]

        if not valid_texts:
            return [None] * len(texts)

        try:
            with torch.no_grad():
                embeddings = self.model.encode(valid_texts, normalize_embeddings=True)

            # Map back to original order
            result = []
            valid_idx = 0
            for text in processed_texts:
                if text:
                    result.append(embeddings[valid_idx].tolist())
                    valid_idx += 1
                else:
                    result.append(None)
            return result
        except Exception as e:
            print(f"❌ Error generating batch embeddings: {e}")
            return [None] * len(texts)

    def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding"""
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        if norm == 0:
            return embedding
        return (embedding_array / norm).tolist()
