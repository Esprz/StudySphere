from fastapi import APIRouter, Query
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from fastapi import HTTPException

from ..config import recommendation_pipeline, postgres_store
from ..utils.env_config import EnvConfig

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class Post(BaseModel):
    """Model for post data"""

    id: str
    title: str
    content: str
    created_at: Optional[str]
    updated_at: Optional[str]
    author_id: str
    author_name: str
    author_avatar: Optional[str]
    tags: List[Dict[str, Any]]
    recommendation_score: Optional[float] = None
    recommendation_reason: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Response model for recommendations"""

    posts: List[Post]
    metadata: Dict[str, Any]


@router.get("/{user_id}", response_model=RecommendationResponse)
async def get_post_recommendations(
    user_id: str,
    device: Optional[str] = Query(
        None, description="User device type (e.g., mobile, desktop)"
    ),
    time_of_day: Optional[str] = Query(
        None, description="Time of day (e.g., morning, afternoon, evening)"
    ),
    limit: int = Query(
        EnvConfig.DEFAULT_RECOMMENDATION_LIMIT,
        description="Maximum number of recommendations to return",
    ),
):
    """Get personalized post recommendations for a user"""
    try:
        context = {}
        if device:
            context["device"] = device
        if time_of_day:
            context["time_of_day"] = time_of_day

        recommendations = recommendation_pipeline.recommend(
            user_id=user_id, context=context, limit=limit
        )

        if not recommendations:
            return {
                "posts": [],
                "metadata": {"count": 0, "user_id": user_id, "context_used": context},
            }

        post_ids = [rec.get("item_id") for rec in recommendations]

        post_details = postgres_store.get_posts_by_ids(post_ids)

        # Create a mapping of recommendation metadata for each post
        rec_info = {
            rec.get("item_id"): {
                "score": rec.get("score"),
                "reason": rec.get("reason", "Recommended for you"),
            }
            for rec in recommendations
        }

        posts = []
        for post in post_details:
            post_id = post.get("id")
            if post_id in rec_info:
                post["recommendation_score"] = rec_info[post_id].get("score")
                post["recommendation_reason"] = rec_info[post_id].get("reason")
                posts.append(post)

        return {
            "posts": posts,
            "metadata": {
                "count": len(posts),
                "user_id": user_id,
                "context_used": context,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating recommendations: {str(e)}"
        )
