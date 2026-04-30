from typing import Any, Dict, List

from loguru import logger


class UserRecommendationPipeline:
    def __init__(self, vector_store, postgres_store, redis=None):
        self.vector_store = vector_store
        self.postgres_store = postgres_store
        self.redis = redis

    async def recommend_users(self, user_id: str, limit: int = 5) -> Dict[str, Any]:
        followed_ids = set(self.postgres_store.get_followed_user_ids(user_id))
        blocked_ids = followed_ids | {user_id}
        request_size = max(limit * 4, 20)

        merged_scores: Dict[str, Dict[str, Any]] = {}
        user_goal_tags = set(self.postgres_store.get_user_goal_tags(user_id))

        if self.vector_store:
            similar_user_ids, scores = self.vector_store.search_users_by_user_id(
                user_id, k=request_size
            )
            for similar_user_id, score in zip(similar_user_ids, scores):
                if similar_user_id in blocked_ids:
                    continue
                merged_scores.setdefault(
                    similar_user_id, {"user_id": similar_user_id, "score": 0.0, "sources": set()}
                )
                merged_scores[similar_user_id]["score"] += float(score)
                merged_scores[similar_user_id]["sources"].add("user_embedding")

        cf_version = self.postgres_store.get_active_feature_version("cf", fallback="v1")
        for row in self.postgres_store.get_user_topk_neighbors(
            user_id, k=request_size, version=cf_version
        ):
            similar_user_id = row.get("similar_user_id")
            if not similar_user_id or similar_user_id in blocked_ids:
                continue
            merged_scores.setdefault(
                similar_user_id, {"user_id": similar_user_id, "score": 0.0, "sources": set()}
            )
            merged_scores[similar_user_id]["score"] += float(
                row.get("similarity_score", 0.0)
            )
            merged_scores[similar_user_id]["sources"].add("user_cf")

        if not merged_scores:
            recommendations: List[Dict[str, Any]] = []
        else:
            profiles = self.postgres_store.get_users_by_ids(list(merged_scores.keys()))
            profile_map = {profile["user_id"]: profile for profile in profiles}

            recommendations = []
            for candidate in merged_scores.values():
                profile = profile_map.get(candidate["user_id"])
                if not profile:
                    continue

                overlap = len(
                    user_goal_tags.intersection(set(profile.get("goalTags", []) or []))
                )
                score = candidate["score"] + overlap * 0.1
                recommendations.append(
                    {
                        "user_id": candidate["user_id"],
                        "username": profile.get("username"),
                        "display_name": profile.get("display_name"),
                        "avatar_url": profile.get("avatar_url"),
                        "bio": profile.get("bio"),
                        "score": round(score, 6),
                        "source": "+".join(sorted(candidate["sources"])),
                    }
                )

            recommendations.sort(key=lambda item: item["score"], reverse=True)
            recommendations = recommendations[:limit]

        if self.redis:
            try:
                await self.redis.set(
                    f"rec:users:{user_id}",
                    recommendations,
                    ttl=self.redis.CACHE_TTL["recommendations"],
                )
            except Exception as exc:
                logger.warning(f"Failed to cache user recommendations for {user_id}: {exc}")

        return {"user_id": user_id, "recommendations": recommendations}
