from fastapi import APIRouter, Query, HTTPException
from typing import Dict, List, Any, Optional

from ..config import recommendation_pipeline, postgres_store
from ..utils.env_config import EnvConfig

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/{user_id}")
async def get_post_recommendations(
    user_id: str,
    device: Optional[str] = Query(None),
    time_of_day: Optional[str] = Query(None),
    limit: int = Query(EnvConfig.DEFAULT_RECOMMENDATION_LIMIT),
):
    try:
        context: Dict[str, Any] = {}
        if device:
            context["device"] = device
        if time_of_day:
            context["time_of_day"] = time_of_day

        result = await recommendation_pipeline.recommend(
            user_id=user_id, context=context, limit=limit
        )

        recommendations = result.get("recommendations", [])
        if not recommendations:
            return {
                "posts": [],
                "metadata": {"count": 0, "user_id": user_id, "context_used": context},
            }

        post_ids = [rec.get("item_id") for rec in recommendations if rec.get("item_id")]
        post_details = postgres_store.get_posts_by_ids(post_ids)

        rec_info = {
            rec.get("item_id"): {
                "score": rec.get("score"),
                "source": rec.get("source", "unknown"),
            }
            for rec in recommendations
        }

        posts = []
        for post in post_details:
            post_id = post.get("id")
            if post_id in rec_info:
                post["recommendation_score"] = rec_info[post_id].get("score")
                post["recommendation_source"] = rec_info[post_id].get("source")
                posts.append(post)

        return {
            "posts": posts,
            "metadata": {
                "count": len(posts),
                "user_id": user_id,
                "context_used": context,
                "cached": result.get("cached", False),
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating recommendations: {str(e)}"
        )


@router.post("/{user_id}/invalidate-cache")
async def invalidate_user_cache(user_id: str):
    try:
        await recommendation_pipeline.invalidate_user_cache(user_id)
        return {"message": f"Cache invalidated for user {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
