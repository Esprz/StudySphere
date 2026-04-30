"""Unit tests for Phase 1 — interface consistency and pipeline behaviour."""

import pytest
from unittest.mock import AsyncMock
from typing import List, Dict, Any
import asyncio

from app.services.recall.base import RecallBase
from app.services.filters.base import FilterBase
from app.services.diversity.base import DiversityBase
from app.services.filters.duplicate_filter import DuplicateFilter
from app.services.filters.seen_filter import SeenFilter
from app.services.recommendation_pipeline import RecommendationPipeline


# ── Stubs ───────────────────────────────────────────────────────────


class StubRecall(RecallBase):
    def __init__(self, name: str, candidates: List[Dict[str, Any]]):
        super().__init__(name=name)
        self._candidates = candidates

    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 100
    ) -> List[Dict[str, Any]]:
        return self._candidates[:k]


class FailingRecall(RecallBase):
    def __init__(self):
        super().__init__(name="content_based")

    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 100
    ) -> List[Dict[str, Any]]:
        raise RuntimeError("recall exploded")


class SlowRecall(RecallBase):
    def __init__(self, delay: float = 1.0):
        super().__init__(name="trending")
        self._delay = delay

    async def get_candidates(
        self, user_id: str, context: Dict[str, Any], k: int = 100
    ) -> List[Dict[str, Any]]:
        await asyncio.sleep(self._delay)
        return [{"item_id": "slow-post", "score": 1.0, "source": self.name}]


class PassthroughFilter(FilterBase):
    def __init__(self):
        super().__init__(name="passthrough")

    async def filter_candidates(
        self, user_id: str, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        return candidates


class TopNDiversity(DiversityBase):
    def __init__(self):
        super().__init__(name="topn")

    async def diversify(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        sorted_c = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
        return sorted_c[:limit]


class FakePostgresStore:
    def __init__(self, interaction_count: int = 100, seen_items=None):
        self.interaction_count = interaction_count
        self.seen_items = set(seen_items or [])

    def get_user_interaction_count(self, user_id: str) -> int:
        return self.interaction_count

    def get_active_feature_version(self, feature_name: str, fallback=None) -> str:
        versions = {"cf": "cf_v2", "trending": "trending_v2"}
        return versions.get(feature_name, fallback)

    def get_seen_items_last_days(self, user_id: str, days: int = 30) -> set:
        return set(self.seen_items)

    def get_post_topic_tags(self, post_ids: List[str]) -> Dict[str, List[str]]:
        return {post_id: [post_id.split("-")[0]] for post_id in post_ids}


# ── Helpers ─────────────────────────────────────────────────────────


def _make_pipeline(
    recall_list,
    filter_list=None,
    diversity=None,
    with_db=True,
    interaction_count: int = 100,
    seen_items=None,
):
    return RecommendationPipeline(
        recall_services=recall_list,
        filter_services=filter_list or [DuplicateFilter(), PassthroughFilter()],
        diversity_service=diversity or TopNDiversity(),
        postgres_store=(
            FakePostgresStore(
                interaction_count=interaction_count,
                seen_items=seen_items,
            )
            if with_db
            else None
        ),
    )


class FakeRedis:
    CACHE_TTL = {"recommendations": 1800, "cold_start": 3600}

    def __init__(self):
        self.values: Dict[str, Any] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: Any, ttl: int = None):
        self.values[key] = value
        return True

    async def invalidate_pattern(self, pattern: str) -> int:
        prefix = pattern.rstrip("*")
        to_delete = [key for key in self.values if key.startswith(prefix)]
        for key in to_delete:
            del self.values[key]
        return len(to_delete)

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.values:
                del self.values[key]
                deleted += 1
        return deleted


SAMPLE_CANDIDATES = [
    {"item_id": f"post-{i}", "score": float(10 - i), "source": "stub"}
    for i in range(10)
]


# ── Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pipeline_returns_recommendations():
    pipe = _make_pipeline([StubRecall("content_based", SAMPLE_CANDIDATES)])
    result = await pipe.recommend("user-1", {}, limit=5, use_cache=False)
    recs = result["recommendations"]
    assert len(recs) == 5
    assert recs[0]["item_id"] == "post-0"


@pytest.mark.asyncio
async def test_pipeline_empty_recall():
    pipe = _make_pipeline([StubRecall("content_based", [])])
    result = await pipe.recommend("user-1", {}, limit=5, use_cache=False)
    assert result["recommendations"] == []


@pytest.mark.asyncio
async def test_pipeline_failing_recall_does_not_crash():
    pipe = _make_pipeline(
        [
            FailingRecall(),
            StubRecall("cold_start", SAMPLE_CANDIDATES),
        ]
    )
    result = await pipe.recommend("user-1", {}, limit=5, use_cache=False)
    assert len(result["recommendations"]) == 5


@pytest.mark.asyncio
async def test_pipeline_deduplicates_by_item_id():
    duped = [
        {"item_id": "post-1", "score": 5.0, "source": "a"},
        {"item_id": "post-1", "score": 8.0, "source": "b"},
        {"item_id": "post-2", "score": 3.0, "source": "a"},
    ]
    pipe = _make_pipeline([StubRecall("content_based", duped)])
    result = await pipe.recommend("user-1", {}, limit=10, use_cache=False)
    recs = result["recommendations"]
    ids = [r["item_id"] for r in recs]
    assert ids.count("post-1") == 1
    kept = next(r for r in recs if r["item_id"] == "post-1")
    assert kept["score"] == 8.0


@pytest.mark.asyncio
async def test_cold_start_defaults_true_without_db():
    pipe = _make_pipeline([StubRecall("cold_start", SAMPLE_CANDIDATES)], with_db=False)
    is_cold = await pipe._is_cold_start_user("new-user")
    assert is_cold is True


@pytest.mark.asyncio
async def test_cold_start_false_with_enough_interactions():
    pipe = _make_pipeline([StubRecall("content_based", SAMPLE_CANDIDATES)])
    is_cold = await pipe._is_cold_start_user("active-user")
    assert is_cold is False


@pytest.mark.asyncio
async def test_pipeline_no_redis_still_works():
    pipe = _make_pipeline([StubRecall("content_based", SAMPLE_CANDIDATES)])
    assert pipe.redis is None
    result = await pipe.recommend("user-1", {}, limit=3, use_cache=True)
    assert len(result["recommendations"]) == 3


@pytest.mark.asyncio
async def test_cold_start_limits_active_services():
    """When user has 0 interactions, only cold_start_interest + trending run."""
    pipe = _make_pipeline(
        [
            StubRecall(
                "user_cf", [{"item_id": "uc-1", "score": 9, "source": "uc"}]
            ),
            StubRecall(
                "cold_start_interest",
                [{"item_id": "cs-1", "score": 1, "source": "cs"}],
            ),
            StubRecall("trending", [{"item_id": "tr-1", "score": 0.5, "source": "tr"}]),
        ],
        interaction_count=0,
    )
    result = await pipe.recommend("user-1", {}, limit=10, use_cache=False)
    recs = result["recommendations"]
    ids = [r["item_id"] for r in recs]
    assert "cs-1" in ids
    assert "tr-1" in ids
    assert "uc-1" not in ids


@pytest.mark.asyncio
async def test_warm_user_uses_full_source_set():
    pipe = _make_pipeline(
        [
            StubRecall("user_cf", [{"item_id": "uc-1", "score": 9, "source": "uc"}]),
            StubRecall("item_cf", [{"item_id": "ic-1", "score": 7, "source": "ic"}]),
            StubRecall("content_based", [{"item_id": "cb-1", "score": 8, "source": "cb"}]),
        ],
        interaction_count=10,
    )
    result = await pipe.recommend("user-1", {}, limit=10, use_cache=False)
    ids = [r["item_id"] for r in result["recommendations"]]
    assert "uc-1" in ids
    assert "ic-1" in ids
    assert "cb-1" in ids


@pytest.mark.asyncio
async def test_partial_cold_start_uses_interest_content_trending():
    pipe = _make_pipeline(
        [
            StubRecall("cold_start_interest", [{"item_id": "cs-1", "score": 9, "source": "cs"}]),
            StubRecall("content_based", [{"item_id": "cb-1", "score": 8, "source": "cb"}]),
            StubRecall("trending", [{"item_id": "tr-1", "score": 7, "source": "tr"}]),
            StubRecall("user_cf", [{"item_id": "uc-1", "score": 10, "source": "uc"}]),
        ],
        interaction_count=3,
    )
    result = await pipe.recommend("user-1", {}, limit=10, use_cache=False)
    ids = [r["item_id"] for r in result["recommendations"]]
    assert {"cs-1", "cb-1", "tr-1"}.issubset(set(ids))
    assert "uc-1" not in ids


@pytest.mark.asyncio
async def test_pipeline_writes_feed_cache_entries():
    pipe = _make_pipeline([StubRecall("content_based", SAMPLE_CANDIDATES)])
    fake_redis = FakeRedis()
    pipe.redis = fake_redis

    await pipe.recommend("user-1", {}, limit=2, use_cache=False)

    assert fake_redis.values["rec:feed:user-1"] == [
        {"post_id": "post-0", "score": 10.0, "source": "stub"},
        {"post_id": "post-1", "score": 9.0, "source": "stub"},
    ]


@pytest.mark.asyncio
async def test_timeout_skips_slow_source_and_keeps_fast_one():
    pipe = _make_pipeline(
        [
            SlowRecall(delay=0.6),
            StubRecall("content_based", [{"item_id": "fast-post", "score": 5.0, "source": "cb"}]),
        ]
    )

    result = await pipe.recommend("user-1", {}, limit=5, use_cache=False, detailed=True)
    ids = [r["item_id"] for r in result["recommendations"]]
    assert ids == ["fast-post"]
    assert result["metrics"]["source_metrics"]["trending"]["status"] == "timeout"


@pytest.mark.asyncio
async def test_seen_filter_reads_db_and_excludes_seen_items():
    filter_service = SeenFilter(db=FakePostgresStore(seen_items={"post-1"}), redis=FakeRedis())
    candidates = [
        {"item_id": "post-1", "score": 3.0, "source": "a"},
        {"item_id": "post-2", "score": 2.0, "source": "b"},
    ]
    filtered = await filter_service.filter_candidates("user-1", candidates, {})
    assert filtered == [{"item_id": "post-2", "score": 2.0, "source": "b"}]


@pytest.mark.asyncio
async def test_duplicate_filter_keeps_highest_score_and_merges_sources():
    filter_service = DuplicateFilter()
    candidates = [
        {"item_id": "post-1", "score": 3.0, "source": "user_cf"},
        {"item_id": "post-1", "score": 5.0, "source": "content_based"},
    ]
    filtered = await filter_service.filter_candidates("user-1", candidates, {})
    assert filtered == [
        {
            "item_id": "post-1",
            "score": 5.0,
            "source": "content_based",
            "sources": ["content_based", "user_cf"],
        }
    ]
