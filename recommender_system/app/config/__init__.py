from .redis_config import redis_config, session_redis_config

from ..services.recall.content_based import ContentBasedRecall
from ..services.recall.following_activity import FollowingActivityRecall
from ..services.recall.interest_aware_cold_start import (
    InterestAwareColdStartRecall,
)
from ..services.recall.item_collaborative import ItemCollaborativeRecall
from ..services.recall.trending_posts import TrendingPostsRecall
from ..services.recall.user_collaborative import UserCollaborativeRecall

from ..services.filters.seen_filter import SeenFilter
from ..services.filters.duplicate_filter import DuplicateFilter

from ..services.diversity.diversity_enhancer import DiversityEnhancer
from ..services.pipelines.user_recommendation_pipeline import (
    UserRecommendationPipeline,
)
from ..services.recommendation_pipeline import RecommendationPipeline

from ..utils.qdrant_manager import QdrantManager
from ..utils.vector_store import VectorStore
from ..utils.postgres_store import PostgresStore

postgres_store = PostgresStore()
qdrant_manager = QdrantManager()
vector_store = VectorStore(qdrant_manager)

recall_services = [
    InterestAwareColdStartRecall(vector_store=vector_store, db=postgres_store),
    ContentBasedRecall(vector_store=vector_store, db=postgres_store),
    UserCollaborativeRecall(vector_store=vector_store, db=postgres_store),
    ItemCollaborativeRecall(vector_store=vector_store, db=postgres_store),
    FollowingActivityRecall(vector_store=vector_store, db=postgres_store),
    TrendingPostsRecall(vector_store=vector_store, db=postgres_store),
]

filter_services = [
    SeenFilter(db=postgres_store, redis=redis_config),
    DuplicateFilter(),
]

diversity_service = DiversityEnhancer(db=postgres_store)

recommendation_pipeline = RecommendationPipeline(
    recall_services=recall_services,
    filter_services=filter_services,
    diversity_service=diversity_service,
    postgres_store=postgres_store,
    redis=redis_config,
    session_redis=session_redis_config,
)

user_recommendation_pipeline = UserRecommendationPipeline(
    vector_store=vector_store,
    postgres_store=postgres_store,
    redis=redis_config,
)

__all__ = [
    "redis_config",
    "session_redis_config",
    "recommendation_pipeline",
    "user_recommendation_pipeline",
    "postgres_store",
]
