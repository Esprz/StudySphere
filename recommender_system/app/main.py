from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import recommendations

from app.services.recall.content_based import ContentBasedRecall
from app.services.recall.user_collaborative import UserCollaborativeRecall
from app.services.recall.item_collaborative import ItemCollaborativeRecall
from app.services.recall.trending_posts import TrendingPostsRecall
from app.services.recall.cold_start import ColdStartRecall
from app.services.recall.following_activity import FollowingActivityRecall

from app.services.filters.seen_filter import SeenFilter
from app.services.filters.duplicate_filter import DuplicateFilter

from app.services.diversity.diversity_enhancer import DiversityEnhancer
from app.services.recommendation_pipeline import RecommendationPipeline

recall_services = [
    ContentBasedRecall(index_path="data/indices", db_connection_string="..."),
    UserCollaborativeRecall(index_path="data/indices", db_connection_string="..."),
    ItemCollaborativeRecall(index_path="data/indices", db_connection_string="..."),
    TrendingPostsRecall(db_connection_string="..."),
    FollowingActivityRecall(db_connection_string="..."),
    ColdStartRecall()  
]

recommendation_pipeline = RecommendationPipeline(
    recall_services=recall_services,
    filter_services=filter_services,
    diversity_service=diversity_service
)

filter_services = [
    SeenFilter(db_connection_string="..."),
    DuplicateFilter()
]

diversity_service = DiversityEnhancer()

user_id = "user_123"
context = {"device": "mobile", "time_of_day": "evening"}
recommendations = recommendation_pipeline.recommend(user_id, context, limit=20)

app = FastAPI(title="StudySphere Recommender System")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommendations.router)


@app.get("/")
async def root():
    return {"message": "StudySphere Recommender System API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
