import pytest

from app.services.pipelines.user_recommendation_pipeline import (
    UserRecommendationPipeline,
)


class FakeVectorStore:
    def search_users_by_user_id(self, user_id: str, k: int = 5):
        return ["user-2", "user-3", "user-1"], [0.9, 0.4, 0.99]


class FakePostgresStore:
    def get_followed_user_ids(self, user_id: str):
        return ["user-4"]

    def get_user_goal_tags(self, user_id: str):
        return ["ml", "algo"]

    def get_active_feature_version(self, feature_name: str, fallback="v1"):
        return "cf_v2"

    def get_user_topk_neighbors(self, user_id: str, k: int, version: str | None = None):
        return [
            {"similar_user_id": "user-3", "similarity_score": 0.5},
            {"similar_user_id": "user-4", "similarity_score": 0.8},
        ]

    def get_users_by_ids(self, user_ids):
        return [
            {
                "user_id": "user-2",
                "username": "u2",
                "display_name": "User Two",
                "avatar_url": None,
                "bio": "bio2",
                "goalTags": ["ml"],
            },
            {
                "user_id": "user-3",
                "username": "u3",
                "display_name": "User Three",
                "avatar_url": None,
                "bio": "bio3",
                "goalTags": ["algo"],
            },
        ]


class FakeRedis:
    CACHE_TTL = {"recommendations": 1800}

    def __init__(self):
        self.values = {}

    async def set(self, key, value, ttl=None):
        self.values[key] = value
        return True


@pytest.mark.asyncio
async def test_user_recommendation_pipeline_merges_sources_and_caches():
    redis = FakeRedis()
    pipeline = UserRecommendationPipeline(
        vector_store=FakeVectorStore(),
        postgres_store=FakePostgresStore(),
        redis=redis,
    )

    result = await pipeline.recommend_users("user-1", limit=2)

    assert {item["user_id"] for item in result["recommendations"]} == {
        "user-2",
        "user-3",
    }
    user3 = next(item for item in result["recommendations"] if item["user_id"] == "user-3")
    assert user3["source"] == "user_cf+user_embedding"
    assert redis.values["rec:users:user-1"] == result["recommendations"]
