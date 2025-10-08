from .services.recall.content_based import ContentBasedRecall
from .services.recall.user_collaborative import UserCollaborativeRecall
from .services.recall.item_collaborative import ItemCollaborativeRecall
from .services.recall.trending_posts import TrendingPostsRecall
from .services.recall.cold_start import ColdStartRecall
from .services.recall.following_activity import FollowingActivityRecall

from .services.filters.seen_filter import SeenFilter
from .services.filters.duplicate_filter import DuplicateFilter

from .services.diversity.diversity_enhancer import DiversityEnhancer
from .services.recommendation_pipeline import RecommendationPipeline

from .utils.qdrant_manager import QdrantManager
from .utils.vector_store import VectorStore
from .utils.postgres_store import PostgresStore

# Initialize services
postgres_store = PostgresStore()
qdrant_manager = QdrantManager()
vector_store = VectorStore(qdrant_manager, postgres_store)

recall_services = [
    ContentBasedRecall(vector_store=vector_store, postgres_store=postgres_store),
    UserCollaborativeRecall(vector_store=vector_store, postgres_store=postgres_store),
    ItemCollaborativeRecall(vector_store=vector_store, postgres_store=postgres_store),
    TrendingPostsRecall(vector_store=vector_store, postgres_store=postgres_store),
    FollowingActivityRecall(vector_store=vector_store, postgres_store=postgres_store),
    ColdStartRecall(vector_store=vector_store, postgres_store=postgres_store),
]

filter_services = [SeenFilter(), DuplicateFilter()]

diversity_service = DiversityEnhancer()

recommendation_pipeline = RecommendationPipeline(
    recall_services=recall_services,
    filter_services=filter_services,
    diversity_service=diversity_service,
)
