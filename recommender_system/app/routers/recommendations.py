from fastapi import APIRouter, Query
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from fastapi import HTTPException

from ..config import recommendation_pipeline, postgres_store, redis_config
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

        recommendations = await recommendation_pipeline.recommend(
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


@router.post("/{user_id}/invalidate-cache")
async def invalidate_user_cache(user_id: str):
    """Invalidate cached recommendations for a specific user"""
    try:
        await recommendation_pipeline.invalidate_user_cache(user_id)
        return {"message": f"Cache invalidated for user {user_id}"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error invalidating cache: {str(e)}"
        )


@router.post("/warm-up-cache")
async def warm_up_cache(
    user_ids: List[str],
    context: Optional[Dict[str, Any]] = None
):
    """Pre-warm cache for multiple users"""
    try:
        await recommendation_pipeline.warm_up_cache(user_ids, context)
        return {"message": f"Cache warmed up for {len(user_ids)} users"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error warming up cache: {str(e)}"
        )


@router.get("/cache/stats")
async def get_cache_stats():
    """Get Redis cache statistics"""
    try:
        stats = await redis_config.get_cache_stats()
        return {"cache_stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting cache stats: {str(e)}"
        )
