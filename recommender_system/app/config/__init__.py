from .redis_config import redis_config

from ..services.recall.content_based import ContentBasedRecall

from ..services.filters.seen_filter import SeenFilter
from ..services.filters.duplicate_filter import DuplicateFilter

from ..services.diversity.diversity_enhancer import DiversityEnhancer
from ..services.recommendation_pipeline import RecommendationPipeline

from ..utils.qdrant_manager import QdrantManager
from ..utils.vector_store import VectorStore
from ..utils.postgres_store import PostgresStore

postgres_store = PostgresStore()
qdrant_manager = QdrantManager()
vector_store = VectorStore(qdrant_manager)

recall_services = [
    ContentBasedRecall(vector_store=vector_store, db=postgres_store),
]

filter_services = [SeenFilter(), DuplicateFilter()]

diversity_service = DiversityEnhancer()

recommendation_pipeline = RecommendationPipeline(
    recall_services=recall_services,
    filter_services=filter_services,
    diversity_service=diversity_service,
    postgres_store=postgres_store,
    redis=redis_config,
)

__all__ = ["redis_config", "recommendation_pipeline", "postgres_store"]
