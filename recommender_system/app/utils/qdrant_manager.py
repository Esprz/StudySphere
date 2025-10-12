from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from .env_config import EnvConfig
from loguru import logger


class QdrantManager:
    def __init__(self, dim_post=None, dim_user=None, host=None, port=None):
        # Use environment variables with fallback to defaults
        self.dim_post = dim_post or EnvConfig.QDRANT_DIM_POST
        self.dim_user = dim_user or EnvConfig.QDRANT_DIM_USER
        self.host = host or EnvConfig.QDRANT_HOST
        self.port = port or EnvConfig.QDRANT_PORT
        self.client = QdrantClient(host=self.host, port=self.port)
        self.collections = {
            "realtime_posts": "post_embeddings_realtime",
            "realtime_users": "user_embeddings_realtime",
        }
        if not all(
            self.client.collection_exists(collection_name=collection_name)
            for collection_name in self.collections.values()
        ):
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
                logger.info(f"✅ Created collection {collection_name}")
            except Exception as e:
                logger.error(f"❌ Failed to create collection {collection_name}: {e}")
                pass  # Collection already exists

    def get_vector(self, collection_type, vector_id: str):
        collection_name = self.collections[collection_type]
        result = self.client.retrieve(collection_name=collection_name, ids=[vector_id])
        return result[0].vector if result else None

    def search_vectors(self, collection_type, query_vector: list, k: int = 5):
        collection_name = self.collections[collection_type]
        result = self.client.search(
            collection_name=collection_name, query_vector=query_vector, limit=k
        )
        return [point.id for point in result], [point.score for point in result]
