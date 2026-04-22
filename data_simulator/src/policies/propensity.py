"""Propensity logging helpers for stochastic decision tracking."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from config.models import PropensityLogRecord
from core.ids import new_id


def make_propensity_log(
    *,
    decision_stage: str,
    user_id: str,
    session_id: str,
    timestamp: datetime,
    post_id: str | None = None,
    exposure_id: str | None = None,
    goal_id: str | None = None,
    deterministic_prob: float | None = None,
    final_prob: float | None = None,
    prob_jitter: float | None = None,
    rng: random.Random | None = None,
    sampling_policy: str = "internal_heuristic_v1",
    sampling_policy_version: str = "1.0",
    sampled_outcome: bool | None = None,
    metadata: dict[str, Any] | None = None,
) -> PropensityLogRecord:
    """Construct a normalized propensity log record for one stochastic decision."""
    return PropensityLogRecord(
        log_id=new_id("pl", rng=rng),
        decision_stage=decision_stage,
        user_id=user_id,
        session_id=session_id,
        timestamp=timestamp,
        post_id=post_id,
        exposure_id=exposure_id,
        goal_id=goal_id,
        deterministic_prob=deterministic_prob,
        final_prob=final_prob,
        prob_jitter=prob_jitter,
        sampling_policy=sampling_policy,
        sampling_policy_version=sampling_policy_version,
        sampled_outcome=sampled_outcome,
        metadata=dict(metadata or {}),
    )
