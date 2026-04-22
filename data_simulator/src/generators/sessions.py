"""Session and activity generation for simulator v2 Phase 1."""

from __future__ import annotations

import random
from datetime import datetime

from config.models import ActivityState, GlobalTimeContext, SessionContext, SourceBundle, UserGoal, UserProfile
from core.ids import new_id
from core.time import clip_0_1


def sample_active_users(
    time_tick: datetime,
    users: list[UserProfile],
    user_memory: dict[str, dict],
    global_time_context: GlobalTimeContext,
    rng: random.Random,
) -> list[UserProfile]:
    del time_tick, user_memory  # Included for interface consistency with later phases.

    active: list[UserProfile] = []
    for user in users:
        base = _base_activity_probability(user.learning_intensity)
        circadian = _circadian_adjustment(user, global_time_context.hour_segment)
        day_bonus = 0.04 if global_time_context.day_type == "weekend" else 0.0
        probability = clip_0_1(base + circadian + day_bonus + global_time_context.fatigue_bonus * -0.2)
        if rng.random() < probability:
            active.append(user)

    if not active and users:
        active.append(rng.choice(users))
    return active


def open_session(
    user: UserProfile,
    time_tick: datetime,
    active_goal: UserGoal,
    global_time_context: GlobalTimeContext,
    rng: random.Random,
    *,
    max_candidate_pool_size: int = 80,
) -> SessionContext:
    activity_id = new_id("a", rng=rng)
    return SessionContext(
        session_id=new_id("s", rng=rng),
        user_id=user.user_id,
        activity_id=activity_id,
        surface="feed",
        started_at=time_tick,
        wall_clock_time=global_time_context.wall_clock_time,
        hour_segment=global_time_context.hour_segment,
        day_type=global_time_context.day_type,
        academic_season=global_time_context.academic_season,
        goal_topic=active_goal.related_topics[0] if active_goal.related_topics else user.primary_interest,
        activity_intent="",
        candidate_pool_size=max_candidate_pool_size,
        items_exposed_count=0,
        session_duration_seconds=rng.randint(10 * 60, 25 * 60),
        fatigue_start=clip_0_1(0.10 + global_time_context.fatigue_bonus),
        activity_transition_count=0,
    )


def generate_activity_state(
    user: UserProfile,
    session: SessionContext,
    active_goal: UserGoal,
    sources: SourceBundle,
    global_time_context: GlobalTimeContext,
    rng: random.Random,
) -> ActivityState:
    intent = _sample_activity_intent(active_goal.goal_type, sources, global_time_context, rng)
    topic = active_goal.related_topics[0] if active_goal.related_topics else user.primary_interest

    urgency = clip_0_1(
        0.45 * active_goal.priority
        + 0.25 * active_goal.strength
        + global_time_context.urgency_bonus
        + rng.uniform(-0.1, 0.1)
    )

    available_minutes = _sample_available_minutes(user.learning_intensity, rng)
    target_difficulty = _sample_target_difficulty(user.diligence_level, rng)

    return ActivityState(
        activity_id=session.activity_id,
        user_id=user.user_id,
        goal_id=active_goal.goal_id,
        activity_intent=intent,
        topic=topic,
        urgency=round(urgency, 4),
        available_minutes=available_minutes,
        target_difficulty=target_difficulty,
        session_id=session.session_id,
        timestamp=session.started_at,
    )


def maybe_transition_activity_intent(
    user: UserProfile,
    session: SessionContext,
    current_activity_state: ActivityState,
    interactions_so_far: list,
    fatigue: float,
    rng: random.Random,
    *,
    transition_probability: float = 0.12,
) -> ActivityState:
    del user, session, interactions_so_far
    if rng.random() > clip_0_1(transition_probability + fatigue * 0.2):
        return current_activity_state
    # Phase 1 keeps transitions shallow; later phases can use richer rules.
    replacement = rng.choice(
        (
            "Concept_Learning",
            "Resource_Collecting",
            "Revision_Queueing",
            "Reflection",
        )
    )
    return ActivityState(
        activity_id=current_activity_state.activity_id,
        user_id=current_activity_state.user_id,
        goal_id=current_activity_state.goal_id,
        activity_intent=replacement,
        topic=current_activity_state.topic,
        urgency=current_activity_state.urgency,
        available_minutes=current_activity_state.available_minutes,
        target_difficulty=current_activity_state.target_difficulty,
        session_id=current_activity_state.session_id,
        timestamp=current_activity_state.timestamp,
    )


def _sample_activity_intent(
    goal_type: str,
    sources: SourceBundle,
    global_time_context: GlobalTimeContext,
    rng: random.Random,
) -> str:
    mappings = sources.require("goal_activity_bridge").get("mappings", [])
    for item in mappings:
        if item.get("goal") != goal_type:
            continue
        weights = dict(item.get("activity_intent_weights", {}))
        adjusted = _apply_intent_bias(weights, global_time_context.intent_bias)
        return _weighted_choice_dict(adjusted, rng)

    # Fallback to full activity intent taxonomy.
    intents: list[str] = []
    taxonomy = sources.require("activity_intent_taxonomy")
    for category in taxonomy.get("categories", []):
        intents.extend([str(intent) for intent in category.get("intents", [])])
    return rng.choice(intents) if intents else "Concept_Learning"


def _apply_intent_bias(weights: dict[str, float], bias: dict[str, float]) -> dict[str, float]:
    adjusted: dict[str, float] = {}
    for intent, weight in weights.items():
        adjusted[intent] = max(0.001, float(weight) + float(bias.get(intent, 0.0)))
    return adjusted


def _weighted_choice_dict(weights: dict[str, float], rng: random.Random) -> str:
    items = list(weights.items())
    total = sum(max(0.0, weight) for _, weight in items)
    if total <= 0:
        return rng.choice([name for name, _ in items])

    threshold = rng.uniform(0.0, total)
    running = 0.0
    for name, weight in items:
        running += max(0.0, weight)
        if threshold <= running:
            return name
    return items[-1][0]


def _base_activity_probability(learning_intensity: str) -> float:
    if learning_intensity == "light":
        return 0.18
    if learning_intensity == "medium":
        return 0.32
    return 0.5


def _circadian_adjustment(user: UserProfile, hour_segment: str) -> float:
    # Sleep skew closer to 1.0 indicates night preference.
    if hour_segment in {"evening", "late_night"}:
        return (user.sleep_habit_skew - 0.5) * 0.24
    if hour_segment in {"early_morning", "morning"}:
        return ((1.0 - user.sleep_habit_skew) - 0.5) * 0.24
    return 0.0


def _sample_available_minutes(learning_intensity: str, rng: random.Random) -> int:
    if learning_intensity == "light":
        return rng.randint(20, 45)
    if learning_intensity == "medium":
        return rng.randint(30, 75)
    return rng.randint(45, 110)


def _sample_target_difficulty(diligence_level: float, rng: random.Random) -> int:
    value = 1 + 4 * diligence_level + rng.uniform(-0.8, 0.8)
    return max(1, min(5, int(round(value))))
