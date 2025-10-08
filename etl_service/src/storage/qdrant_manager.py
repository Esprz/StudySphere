from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os


class QdrantManager:
    def __init__(self, dim_post=384, dim_user=384, host="qdrant", port=6333):
        self.client = QdrantClient(host=host, port=port)
        self.collections = {
            "realtime_posts": "post_embeddings_realtime",
            "realtime_users": "user_embeddings_realtime",
        }
        self.dim_post = dim_post
        self.dim_user = dim_user
        self._create_collections()

    def _create_collections(self):
        for collection_name in self.collections.values():
            try:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.dim_post, distance=Distance.COSINE
                    ),
                )
            except:
                pass  # Collection already exists

    def get_vector(self, collection_type, vector_id: str):
        collection_name = self.collections[collection_type]
        result = self.client.retrieve(collection_name=collection_name, ids=[vector_id])
        return result[0].vector if result else None

    def update_vector(self, collection_type, vector_id: str, vector: list):
        collection_name = self.collections[collection_type]
        self.client.upsert(
            collection_name=collection_name,
            points=[PointStruct(id=vector_id, vector=vector)],
        )

    def delete_vector(self, collection_type, vector_id: str):
        collection_name = self.collections[collection_type]
        self.client.delete(collection_name=collection_name, ids=[vector_id])

    def search_vectors(self, collection_type, query_vector: list, k: int = 5):
        collection_name = self.collections[collection_type]
        result = self.client.search(
            collection_name=collection_name, query_vector=query_vector, limit=k
        )
        return [point.id for point in result], [point.score for point in result]
