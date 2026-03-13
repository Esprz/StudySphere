"""Unit tests for Phase 1 — interface consistency and pipeline behaviour."""

import pytest
from unittest.mock import AsyncMock
from typing import List, Dict, Any

from app.services.recall.base import RecallBase
from app.services.filters.base import FilterBase
from app.services.diversity.base import DiversityBase
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
    def get_user_interaction_count(self, user_id: str) -> int:
        return 100


# ── Helpers ─────────────────────────────────────────────────────────


def _make_pipeline(recall_list, filter_list=None, diversity=None, with_db=True):
    return RecommendationPipeline(
        recall_services=recall_list,
        filter_services=filter_list or [PassthroughFilter()],
        diversity_service=diversity or TopNDiversity(),
        postgres_store=FakePostgresStore() if with_db else None,
    )


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
    """When user is cold-start, only cold_start/trending_posts/content_based run."""
    pipe = _make_pipeline(
        [
            StubRecall(
                "user_collaborative", [{"item_id": "uc-1", "score": 9, "source": "uc"}]
            ),
            StubRecall("cold_start", [{"item_id": "cs-1", "score": 1, "source": "cs"}]),
        ],
        with_db=False,
    )
    result = await pipe.recommend("user-1", {}, limit=10, use_cache=False)
    recs = result["recommendations"]
    ids = [r["item_id"] for r in recs]
    assert "cs-1" in ids
    assert "uc-1" not in ids
