"""Downstream outcomes generation for Phase 4."""

from __future__ import annotations

import random
import re
from datetime import timedelta

from config.models import (
    ActivityState,
    FocusSessionRecord,
    InteractionRecord,
    PostRecord,
    PropensityLogRecord,
    SessionContext,
    SessionOutcomes,
    SourceBundle,
    UserGoal,
    UserProfile,
    WorldState,
)
from core.ids import new_id
from core.time import clip_0_1
from generators.interactions import compute_utility_match, normalize_detail_dwell
from generators.ranking import compute_goal_alignment
from policies.propensity import make_propensity_log


def select_strongest_session_post(
    interactions: list[InteractionRecord],
    world_state: WorldState,
) -> PostRecord | None:
    """Select the strongest consumed post from one session's interaction trace."""
    views = [event for event in interactions if event.event_type == "view"]
    if not views:
        return None

    best_post: PostRecord | None = None
    best_score = -1.0
    for view in views:
        post = _lookup_post(world_state, view.post_id)
        positive_actions = _count_events(interactions, post.post_id, {"like", "save", "comment"})
        dwell_ms = int(view.dwell_ms or 0)
        dwell_norm = clip_0_1(dwell_ms / 120000.0)
        quality = float(
            world_state.content_memory.get(post.post_id, {}).get("observed_quality", post.observed_quality)
        )
        score = clip_0_1(0.50 * quality + 0.30 * dwell_norm + 0.20 * min(1.0, positive_actions / 3.0))
        if score > best_score:
            best_score = score
            best_post = post
    return best_post


def compute_focus_probability(
    *,
    user: UserProfile,
    strongest_post: PostRecord,
    activity_state: ActivityState,
    active_goal: UserGoal,
    interactions: list[InteractionRecord],
    sources: SourceBundle,
) -> float:
    """Compute deterministic focus probability using session evidence and goal alignment."""
    goal_alignment = compute_goal_alignment(activity_state, strongest_post)
    goal_strength = active_goal.strength
    saved_in_session = 1.0 if _count_events(interactions, strongest_post.post_id, {"save"}) > 0 else 0.0
    liked_in_session = 1.0 if _count_events(interactions, strongest_post.post_id, {"like"}) > 0 else 0.0
    detail_dwell_norm = _strongest_post_dwell_norm(interactions, strongest_post.post_id, sources)

    coeffs = _focus_coefficients(sources)
    score = (
        coeffs["base"]
        + coeffs["diligence_level"] * user.diligence_level
        + coeffs["goal_strength"] * goal_strength
        + coeffs["goal_alignment"] * goal_alignment
        + coeffs["saved_in_session"] * saved_in_session
        + coeffs["liked_in_session"] * liked_in_session
        + coeffs["detail_dwell_norm"] * detail_dwell_norm
    )
    return round(clip_0_1(score), 6)


def generate_session_outcomes(
    *,
    user: UserProfile,
    session: SessionContext,
    activity_state: ActivityState,
    active_goal: UserGoal,
    interactions: list[InteractionRecord],
    world_state: WorldState,
    sources: SourceBundle,
    rng: random.Random,
) -> SessionOutcomes:
    """Generate focus/follow/task outcomes from a session's interaction results."""
    strongest_post = select_strongest_session_post(interactions, world_state)
    if strongest_post is None:
        return SessionOutcomes()

    propensity_logs: list[PropensityLogRecord] = []
    decision_offset_s = 0

    focus_prob = compute_focus_probability(
        user=user,
        strongest_post=strongest_post,
        activity_state=activity_state,
        active_goal=active_goal,
        interactions=interactions,
        sources=sources,
    )
    focus_outcome = rng.random() < focus_prob
    propensity_logs.append(
        make_propensity_log(
            decision_stage="focus_decision",
            user_id=user.user_id,
            session_id=session.session_id,
            timestamp=session.started_at + timedelta(seconds=decision_offset_s),
            post_id=strongest_post.post_id,
            goal_id=active_goal.goal_id,
            deterministic_prob=focus_prob,
            final_prob=focus_prob,
            prob_jitter=0.0,
            rng=rng,
            sampled_outcome=focus_outcome,
        )
    )
    decision_offset_s += 1
    focus_session = (
        _generate_focus_session(
            user=user,
            session=session,
            strongest_post=strongest_post,
            active_goal=active_goal,
            deterministic_focus_prob=focus_prob,
            final_focus_prob=focus_prob,
            rng=rng,
        )
        if focus_outcome
        else None
    )

    follow_events: list[tuple[str, str]] = []
    follow_prob = _compute_follow_probability(
        user=user,
        strongest_post=strongest_post,
        activity_state=activity_state,
        interactions=interactions,
    )
    follow_outcome = strongest_post.author_id != user.user_id and rng.random() < follow_prob
    propensity_logs.append(
        make_propensity_log(
            decision_stage="follow_decision",
            user_id=user.user_id,
            session_id=session.session_id,
            timestamp=session.started_at + timedelta(seconds=decision_offset_s),
            post_id=strongest_post.post_id,
            goal_id=active_goal.goal_id,
            deterministic_prob=follow_prob,
            final_prob=follow_prob,
            prob_jitter=0.0,
            rng=rng,
            sampled_outcome=follow_outcome,
            metadata={"target_author_id": strongest_post.author_id},
        )
    )
    decision_offset_s += 1
    if follow_outcome:
        follow_events.append((user.user_id, strongest_post.author_id))

    new_tasks: list[dict[str, object]] = []
    task_creation_prob = _compute_task_creation_probability(
        user=user,
        strongest_post=strongest_post,
        activity_state=activity_state,
    )
    task_create_outcome = rng.random() < task_creation_prob
    propensity_logs.append(
        make_propensity_log(
            decision_stage="task_create_decision",
            user_id=user.user_id,
            session_id=session.session_id,
            timestamp=session.started_at + timedelta(seconds=decision_offset_s),
            post_id=strongest_post.post_id,
            goal_id=active_goal.goal_id,
            deterministic_prob=task_creation_prob,
            final_prob=task_creation_prob,
            prob_jitter=0.0,
            rng=rng,
            sampled_outcome=task_create_outcome,
        )
    )
    decision_offset_s += 1
    if task_create_outcome:
        new_tasks.append(
            {
                "task_id": new_id("t", rng=rng),
                "goal_id": active_goal.goal_id,
                "post_id": strongest_post.post_id,
                "topic": strongest_post.topic,
                "status": "open",
            }
        )

    completed_tasks: list[str] = []
    task_completion_prob = _compute_task_completion_probability(
        user=user,
        active_goal=active_goal,
        interactions=interactions,
        focus_session=focus_session,
    )
    task_complete_outcome = rng.random() < task_completion_prob
    propensity_logs.append(
        make_propensity_log(
            decision_stage="task_complete_decision",
            user_id=user.user_id,
            session_id=session.session_id,
            timestamp=session.started_at + timedelta(seconds=decision_offset_s),
            post_id=strongest_post.post_id,
            goal_id=active_goal.goal_id,
            deterministic_prob=task_completion_prob,
            final_prob=task_completion_prob,
            prob_jitter=0.0,
            rng=rng,
            sampled_outcome=task_complete_outcome,
        )
    )
    decision_offset_s += 1
    if task_complete_outcome:
        existing = list(world_state.user_memory.get(user.user_id, {}).get("pending_tasks", []))
        if existing:
            completed_tasks.append(str(existing[0].get("task_id")))
        elif new_tasks:
            completed_tasks.append(str(new_tasks[0]["task_id"]))

    return SessionOutcomes(
        focus_session=focus_session,
        follow_events=follow_events,
        new_tasks=new_tasks,
        completed_tasks=completed_tasks,
        strongest_post_id=strongest_post.post_id,
        propensity_logs=propensity_logs,
    )


def _generate_focus_session(
    *,
    user: UserProfile,
    session: SessionContext,
    strongest_post: PostRecord,
    active_goal: UserGoal,
    deterministic_focus_prob: float,
    final_focus_prob: float,
    rng: random.Random,
) -> FocusSessionRecord:
    """Build one focus-session record triggered by a high-impact consumed post."""
    start_offset_minutes = rng.randint(3, 12)
    duration_minutes = int(round(20 + 55 * user.diligence_level + 25 * active_goal.strength))
    duration_minutes = max(15, min(120, duration_minutes))
    started_at = session.started_at + timedelta(minutes=start_offset_minutes)
    ended_at = started_at + timedelta(minutes=duration_minutes)
    return FocusSessionRecord(
        focus_id=new_id("f", rng=rng),
        user_id=user.user_id,
        session_id=session.session_id,
        trigger_post_id=strongest_post.post_id,
        related_goal_id=active_goal.goal_id,
        topic=strongest_post.topic,
        started_at=started_at,
        ended_at=ended_at,
        duration_minutes=duration_minutes,
        trigger_strength=round(clip_0_1(0.5 * deterministic_focus_prob + 0.5 * active_goal.strength), 6),
        deterministic_focus_prob=deterministic_focus_prob,
        final_focus_prob=final_focus_prob,
        sampling_policy="internal_heuristic_v1",
        sampling_policy_version="1.0",
    )


def _compute_follow_probability(
    *,
    user: UserProfile,
    strongest_post: PostRecord,
    activity_state: ActivityState,
    interactions: list[InteractionRecord],
) -> float:
    """Compute follow trigger probability from affinity plus positive interactions."""
    goal_alignment = compute_goal_alignment(activity_state, strongest_post)
    positive_actions = _count_events(interactions, strongest_post.post_id, {"like", "save", "comment"})
    score = (
        0.02
        + 0.20 * user.social_affinity
        + 0.10 * goal_alignment
        + 0.07 * min(1.0, positive_actions / 3.0)
    )
    return round(clip_0_1(score), 6)


def _compute_task_creation_probability(
    *,
    user: UserProfile,
    strongest_post: PostRecord,
    activity_state: ActivityState,
) -> float:
    """Compute probability of creating a concrete follow-up task from the session."""
    goal_alignment = compute_goal_alignment(activity_state, strongest_post)
    utility_match = compute_utility_match(activity_state, strongest_post)
    score = 0.05 + 0.22 * goal_alignment + 0.18 * utility_match + 0.12 * user.diligence_level
    return round(clip_0_1(score), 6)


def _compute_task_completion_probability(
    *,
    user: UserProfile,
    active_goal: UserGoal,
    interactions: list[InteractionRecord],
    focus_session: FocusSessionRecord | None,
) -> float:
    """Compute same-session task completion probability for pending or newly created tasks."""
    goal_topic_saves = sum(
        1
        for event in interactions
        if event.event_type == "save"
    )
    focus_bonus = 0.18 if focus_session is not None else 0.0
    score = (
        0.04
        + 0.18 * user.diligence_level
        + 0.14 * active_goal.strength
        + focus_bonus
        + 0.06 * min(1.0, goal_topic_saves / 3.0)
    )
    return round(clip_0_1(score), 6)


def _strongest_post_dwell_norm(
    interactions: list[InteractionRecord],
    post_id: str,
    sources: SourceBundle,
) -> float:
    """Return normalized max detail dwell for the selected strongest post."""
    view_dwells = [
        int(event.dwell_ms or 0)
        for event in interactions
        if event.event_type == "view" and event.post_id == post_id
    ]
    if not view_dwells:
        return 0.0
    return normalize_detail_dwell(max(view_dwells), sources)


def _count_events(
    interactions: list[InteractionRecord],
    post_id: str,
    event_types: set[str],
) -> int:
    """Count matching events on one post within the current session."""
    return sum(
        1
        for event in interactions
        if event.post_id == post_id and event.event_type in event_types
    )


def _lookup_post(world_state: WorldState, post_id: str) -> PostRecord:
    """Resolve a post from world-state inventory."""
    for post in world_state.posts:
        if post.post_id == post_id:
            return post
    raise KeyError(f"post_id not found: {post_id}")


def _focus_coefficients(sources: SourceBundle) -> dict[str, float]:
    """Extract focus-formula coefficients from decision-formulas source with defaults."""
    defaults = {
        "base": 0.05,
        "diligence_level": 0.24,
        "goal_strength": 0.18,
        "goal_alignment": 0.20,
        "saved_in_session": 0.12,
        "liked_in_session": 0.05,
        "detail_dwell_norm": 0.12,
    }
    functions = sources.require("decision_formulas").get("functions", [])
    entry = next((item for item in functions if item.get("name") == "sample_focus_trigger"), None)
    if entry is None:
        return defaults

    formula = str(entry.get("formula", ""))
    constant_match = re.search(r"clip_0_1\(([0-9]*\.?[0-9]+)", formula)
    if constant_match:
        defaults["base"] = float(constant_match.group(1))

    pairs = re.findall(r"([0-9]*\.?[0-9]+)\s*\*\s*([a-zA-Z_][a-zA-Z0-9_]*)", formula)
    for weight, name in pairs:
        if name in defaults:
            defaults[name] = float(weight)
    return defaults
