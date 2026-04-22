"""Typed records and runtime models for simulator simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GlobalTimeContext:
    wall_clock_time: datetime
    hour_segment: str
    day_type: str
    academic_season: str
    urgency_bonus: float = 0.0
    fatigue_bonus: float = 0.0
    intent_bias: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RunConfig:
    seed: int
    user_count: int = 100
    timeline_ticks: int = 30
    items_per_session: int = 12
    max_candidate_pool_size: int = 80
    render_text: bool = False


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    primary_interest: str
    secondary_interests: list[str]
    learning_intensity: str
    sleep_habit_skew: float
    posting_tendency: str
    interaction_tendency: str
    curiosity_level: float
    diligence_level: float
    social_affinity: float
    exploration_rate: float
    drift_rate: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class UserGoal:
    goal_id: str
    user_id: str
    goal_category: str
    goal_type: str
    related_topics: list[str]
    priority: float
    strength: float
    progress_state: str
    start_at: datetime
    end_at: datetime
    progress: float = 0.0


@dataclass(frozen=True)
class ActivityState:
    activity_id: str
    user_id: str
    goal_id: str
    activity_intent: str
    topic: str
    urgency: float
    available_minutes: int
    target_difficulty: int
    session_id: str
    timestamp: datetime


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    user_id: str
    activity_id: str
    surface: str
    started_at: datetime
    wall_clock_time: datetime
    hour_segment: str
    day_type: str
    academic_season: str
    goal_topic: str
    activity_intent: str
    candidate_pool_size: int
    items_exposed_count: int
    session_duration_seconds: int
    fatigue_start: float
    activity_transition_count: int


@dataclass(frozen=True)
class PostRecord:
    post_id: str
    author_id: str
    topic: str
    subtopic: str
    format: str
    creator_type: str
    difficulty: int
    true_latent_quality: float
    observed_quality: float
    freshness_hours: int
    study_context: str
    utility_style: str
    social_affordance: str
    created_at: datetime


@dataclass(frozen=True)
class ExposureRecord:
    exposure_id: str
    session_id: str
    user_id: str
    post_id: str
    surface: str
    timestamp: datetime
    rank_position: int
    candidate_score: float
    exposure_reasons: list[str]
    score_jitter: float | None = None
    score_breakdown: dict[str, float] | None = None
    deterministic_exposure_score: float | None = None
    ranking_policy: str | None = None
    ranking_policy_version: str | None = None


@dataclass(frozen=True)
class InteractionRecord:
    interaction_id: str
    event_type: str
    user_id: str
    post_id: str
    session_id: str
    exposure_id: str
    timestamp: datetime
    view_depth: str | None = None
    feed_dwell_ms: int | None = None
    dwell_ms: int | None = None
    comment_text: str | None = None
    reason_code: str | None = None
    negative_signal_strength: str | None = None
    deterministic_prob: float | None = None
    final_prob: float | None = None
    prob_jitter: float | None = None
    sampling_policy: str | None = None
    sampled_outcome: bool | None = None


@dataclass(frozen=True)
class FocusSessionRecord:
    focus_id: str
    user_id: str
    session_id: str
    trigger_post_id: str
    related_goal_id: str
    topic: str
    started_at: datetime
    ended_at: datetime
    duration_minutes: int
    trigger_strength: float
    deterministic_focus_prob: float | None = None
    final_focus_prob: float | None = None
    sampling_policy: str | None = None


@dataclass(frozen=True)
class RankedCandidate:
    post_id: str
    deterministic_exposure_score: float
    score_jitter: float
    candidate_score: float
    score_breakdown: dict[str, float]


@dataclass(frozen=True)
class SessionOutcomes:
    focus_session: FocusSessionRecord | None = None
    follow_events: list[tuple[str, str]] = field(default_factory=list)
    new_tasks: list[dict[str, Any]] = field(default_factory=list)
    completed_tasks: list[str] = field(default_factory=list)
    strongest_post_id: str | None = None


@dataclass(frozen=True)
class SourceBundle:
    base_path: Path
    sources: dict[str, dict[str, Any]]

    def require(self, name: str) -> dict[str, Any]:
        if name not in self.sources:
            raise KeyError(f"Missing source '{name}'")
        return self.sources[name]


@dataclass
class WorldState:
    users: list[UserProfile] = field(default_factory=list)
    goals_by_user: dict[str, list[UserGoal]] = field(default_factory=dict)
    posts: list[PostRecord] = field(default_factory=list)
    follow_graph: dict[str, set[str]] = field(default_factory=dict)
    user_memory: dict[str, dict[str, Any]] = field(default_factory=dict)
    content_memory: dict[str, dict[str, Any]] = field(default_factory=dict)
    sessions: list[SessionContext] = field(default_factory=list)
    exposures: list[ExposureRecord] = field(default_factory=list)
    interactions: list[InteractionRecord] = field(default_factory=list)
    focus_sessions: list[FocusSessionRecord] = field(default_factory=list)
