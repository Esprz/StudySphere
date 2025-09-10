from webbrowser import get
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import recommendations

from services.recall.content_based import ContentBasedRecall
from services.recall.user_collaborative import UserCollaborativeRecall
from services.recall.item_collaborative import ItemCollaborativeRecall
from services.recall.trending_posts import TrendingPostsRecall
from services.recall.cold_start import ColdStartRecall
from services.recall.following_activity import FollowingActivityRecall

from services.filters.seen_filter import SeenFilter
from services.filters.duplicate_filter import DuplicateFilter

from services.diversity.diversity_enhancer import DiversityEnhancer
from services.recommendation_pipeline import RecommendationPipeline

from utils.faiss_manager import FaissManager
from utils.vector_store import VectorStore
from utils.postgres_store import PostgresStore

postgres_store = PostgresStore()
faiss_manager = FaissManager()
vector_store = VectorStore(faiss_manager=faiss_manager, postgres_store=postgres_store)

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
user_id = "user_123"
context = {"device": "mobile", "time_of_day": "evening"}
recommendations = recommendation_pipeline.recommend(user_id, context, limit=20)

app = FastAPI(title="StudySphere Recommender System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommendations.router)


@get("/")
async def root():
    return {"message": "StudySphere Recommender System API"}


@get("/health")
async def health_check():
    return {"status": "healthy"}
