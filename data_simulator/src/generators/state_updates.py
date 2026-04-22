"""State seeding and mutation logic for Phase 4."""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import datetime
from typing import Any

from config.models import (
    ActivityState,
    InteractionRecord,
    PostRecord,
    SessionContext,
    SessionOutcomes,
    SourceBundle,
    UserGoal,
    UserProfile,
    WorldState,
)
from core.time import clip_0_1
from generators.goals import maybe_generate_replacement_goal


def seed_user_memory(
    users: list[UserProfile],
    goals_by_user: dict[str, list[UserGoal]],
) -> dict[str, dict]:
    """Initialize per-user mutable memory stores."""
    memory: dict[str, dict] = {}
    for user in users:
        memory[user.user_id] = {
            "active_goals": goals_by_user.get(user.user_id, []),
            "completed_goals": [],
            "recent_sessions": [],
            "recent_topics_viewed": [],
            "recent_topics_hidden": [],
            "recent_authors_followed": [],
            "fatigue_carryover": 0.0,
            "pending_tasks": [],
            "completed_tasks": [],
        }
    return memory


def seed_content_memory(posts: list[PostRecord]) -> dict[str, dict]:
    """Initialize mutable per-post counters and quality signals."""
    memory: dict[str, dict] = {}
    for post in posts:
        memory[post.post_id] = {
            "true_latent_quality": post.true_latent_quality,
            "observed_quality": post.observed_quality,
            "exposure_count": 0,
            "view_count": 0,
            "like_count": 0,
            "save_count": 0,
            "comment_count": 0,
            "hide_count": 0,
            "last_session_delta": {},
        }
    return memory


def initialize_follow_graph(users: list[UserProfile]) -> dict[str, set[str]]:
    """Initialize directed follow graph with empty outbound sets."""
    return {user.user_id: set() for user in users}


def update_user_memory(
    *,
    user: UserProfile,
    session: SessionContext,
    activity_state: ActivityState,
    interactions: list[InteractionRecord],
    outcomes: SessionOutcomes,
    world_state: WorldState,
) -> None:
    """Mutate per-user memory based on latest session interactions/outcomes."""
    del activity_state
    memory = world_state.user_memory.setdefault(user.user_id, {})
    _append_unique(memory.setdefault("recent_sessions", []), session.session_id, limit=80)

    viewed_topics: list[str] = []
    hidden_topics: list[str] = []
    for event in interactions:
        post = _lookup_post(world_state.posts, event.post_id)
        if event.event_type in {"view", "save", "comment", "like"}:
            viewed_topics.append(post.topic)
        if event.event_type == "hide":
            hidden_topics.append(post.topic)
    for topic in viewed_topics:
        _append_unique(memory.setdefault("recent_topics_viewed", []), topic, limit=60)
    for topic in hidden_topics:
        _append_unique(memory.setdefault("recent_topics_hidden", []), topic, limit=40)

    for follower_id, followed_author_id in outcomes.follow_events:
        if follower_id != user.user_id:
            continue
        _append_unique(memory.setdefault("recent_authors_followed", []), followed_author_id, limit=60)

    pending_tasks = memory.setdefault("pending_tasks", [])
    for task in outcomes.new_tasks:
        pending_tasks.append(dict(task))
    completed_task_ids = set(outcomes.completed_tasks)
    if completed_task_ids:
        memory["pending_tasks"] = [
            task for task in pending_tasks if str(task.get("task_id")) not in completed_task_ids
        ]
        for task_id in completed_task_ids:
            _append_unique(memory.setdefault("completed_tasks", []), task_id, limit=200)

    view_count = sum(1 for event in interactions if event.event_type == "view")
    hide_count = sum(1 for event in interactions if event.event_type == "hide")
    quick_bounce_count = sum(1 for event in interactions if event.event_type == "quick_bounce")
    fatigue_signal = clip_0_1(0.05 * view_count + 0.04 * hide_count + 0.05 * quick_bounce_count)
    carryover = float(memory.get("fatigue_carryover", 0.0))
    memory["fatigue_carryover"] = round(clip_0_1(0.6 * carryover + 0.4 * fatigue_signal), 6)

    goals = world_state.goals_by_user.get(user.user_id, [])
    memory["active_goals"] = [goal for goal in goals if goal.progress_state == "active"]


def update_content_memory(
    *,
    interactions: list[InteractionRecord],
    content_memory: dict[str, dict[str, Any]],
) -> None:
    """Apply interaction counters to content memory and keep per-session deltas."""
    deltas: dict[str, dict[str, int]] = {}
    counters = {
        "view": "view_count",
        "like": "like_count",
        "save": "save_count",
        "comment": "comment_count",
        "hide": "hide_count",
    }

    for event in interactions:
        metric = counters.get(event.event_type)
        if metric is None:
            continue
        post_memory = content_memory.get(event.post_id)
        if post_memory is None:
            continue
        post_memory[metric] = int(post_memory.get(metric, 0)) + 1
        post_deltas = deltas.setdefault(event.post_id, {})
        post_deltas[metric] = int(post_deltas.get(metric, 0)) + 1

    for post_id, post_deltas in deltas.items():
        post_memory = content_memory.get(post_id)
        if post_memory is None:
            continue
        post_memory["last_session_delta"] = post_deltas


def update_goal_progress(
    *,
    user: UserProfile,
    active_goal: UserGoal,
    activity_state: ActivityState,
    interactions: list[InteractionRecord],
    outcomes: SessionOutcomes,
    world_state: WorldState,
    sources: SourceBundle,
    rng: random.Random,
    now: datetime,
) -> tuple[UserGoal, UserGoal | None]:
    """Mutate active-goal progress/strength and optionally create replacement goal."""
    weights = _goal_progress_weights(sources)
    goal_topic = activity_state.topic

    save_on_goal_topic = _count_events_on_topic(interactions, world_state.posts, goal_topic, {"save"})
    comment_on_goal_topic = _count_events_on_topic(interactions, world_state.posts, goal_topic, {"comment"})
    hide_on_goal_topic = _count_events_on_topic(interactions, world_state.posts, goal_topic, {"hide"})

    progress_delta = 0.0
    if outcomes.focus_session is not None:
        progress_delta += weights["focus_session"]
    if save_on_goal_topic > 0:
        progress_delta += weights["save_on_goal_aligned_post"] * min(1.0, save_on_goal_topic / 2.0)
    if comment_on_goal_topic > 0:
        progress_delta += weights["comment_on_goal_aligned_post"] * min(1.0, comment_on_goal_topic / 2.0)

    strength_delta = -weights["repeated_hide_on_goal_topic"] * min(1.0, hide_on_goal_topic / 3.0)
    strength_delta -= 0.01 * user.drift_rate

    new_progress = round(clip_0_1(active_goal.progress + progress_delta), 6)
    new_strength = round(clip_0_1(active_goal.strength + 0.10 * progress_delta + strength_delta), 6)

    new_state = active_goal.progress_state
    if new_progress >= 1.0:
        new_state = "completed"
    elif new_strength <= 0.15:
        new_state = "dropped"

    updated_goal = replace(
        active_goal,
        progress=new_progress,
        strength=new_strength,
        progress_state=new_state,
    )
    _replace_goal(world_state.goals_by_user.setdefault(user.user_id, []), updated_goal)

    replacement_goal: UserGoal | None = None
    if new_state in {"completed", "dropped"}:
        replacement_goal = maybe_generate_replacement_goal(user, sources, rng, now=now)
        world_state.goals_by_user[user.user_id].append(replacement_goal)
        memory = world_state.user_memory.setdefault(user.user_id, {})
        memory.setdefault("completed_goals", []).append(
            {
                "goal_id": updated_goal.goal_id,
                "progress_state": updated_goal.progress_state,
                "progress": updated_goal.progress,
                "strength": updated_goal.strength,
            }
        )

    return updated_goal, replacement_goal


def update_follow_graph(
    *,
    follow_graph: dict[str, set[str]],
    follow_events: list[tuple[str, str]],
) -> None:
    """Apply directed follow events to the persistent follow graph."""
    for follower_id, followed_author_id in follow_events:
        if follower_id == followed_author_id:
            continue
        follow_graph.setdefault(follower_id, set()).add(followed_author_id)


def update_observed_quality(world_state: WorldState) -> None:
    """Update observed-quality signal in memory and mirrored post records."""
    post_index = {post.post_id: idx for idx, post in enumerate(world_state.posts)}
    for post_id, memory in world_state.content_memory.items():
        if post_id not in post_index:
            continue
        exposure_count = int(memory.get("exposure_count", 0))
        if exposure_count <= 0:
            continue

        view_rate = float(memory.get("view_count", 0)) / exposure_count
        like_rate = float(memory.get("like_count", 0)) / exposure_count
        save_rate = float(memory.get("save_count", 0)) / exposure_count
        comment_rate = float(memory.get("comment_count", 0)) / exposure_count
        hide_rate = float(memory.get("hide_count", 0)) / exposure_count
        latent = float(memory.get("true_latent_quality", 0.5))

        behavioral_signal = clip_0_1(
            0.35 * view_rate
            + 0.16 * like_rate
            + 0.22 * save_rate
            + 0.10 * comment_rate
            - 0.30 * hide_rate
            + 0.15 * latent
        )
        previous = float(memory.get("observed_quality", latent))
        updated = round(clip_0_1(0.85 * previous + 0.15 * behavioral_signal), 6)
        memory["observed_quality"] = updated

        idx = post_index[post_id]
        world_state.posts[idx] = replace(world_state.posts[idx], observed_quality=updated)


def update_world_state_after_session(
    *,
    user: UserProfile,
    session: SessionContext,
    activity_state: ActivityState,
    active_goal: UserGoal,
    interactions: list[InteractionRecord],
    outcomes: SessionOutcomes,
    world_state: WorldState,
    sources: SourceBundle,
    rng: random.Random,
    now: datetime,
) -> tuple[UserGoal, UserGoal | None]:
    """Apply all Phase-4 state mutations for one completed session."""
    update_content_memory(interactions=interactions, content_memory=world_state.content_memory)
    update_follow_graph(follow_graph=world_state.follow_graph, follow_events=outcomes.follow_events)
    updated_goal, replacement_goal = update_goal_progress(
        user=user,
        active_goal=active_goal,
        activity_state=activity_state,
        interactions=interactions,
        outcomes=outcomes,
        world_state=world_state,
        sources=sources,
        rng=rng,
        now=now,
    )
    update_user_memory(
        user=user,
        session=session,
        activity_state=activity_state,
        interactions=interactions,
        outcomes=outcomes,
        world_state=world_state,
    )
    if outcomes.focus_session is not None:
        world_state.focus_sessions.append(outcomes.focus_session)
    update_observed_quality(world_state)
    return updated_goal, replacement_goal


def _count_events_on_topic(
    interactions: list[InteractionRecord],
    posts: list[PostRecord],
    topic: str,
    event_types: set[str],
) -> int:
    """Count interaction events on a specific topic."""
    topics_by_post = {post.post_id: post.topic for post in posts}
    return sum(
        1
        for event in interactions
        if event.event_type in event_types and topics_by_post.get(event.post_id) == topic
    )


def _replace_goal(goals: list[UserGoal], updated_goal: UserGoal) -> None:
    """Replace goal object in-place by id."""
    for idx, goal in enumerate(goals):
        if goal.goal_id == updated_goal.goal_id:
            goals[idx] = updated_goal
            return
    goals.append(updated_goal)


def _lookup_post(posts: list[PostRecord], post_id: str) -> PostRecord:
    """Find post by id."""
    for post in posts:
        if post.post_id == post_id:
            return post
    raise KeyError(f"post_id not found: {post_id}")


def _append_unique(buffer: list[Any], value: Any, *, limit: int) -> None:
    """Append value to bounded history buffer, removing existing duplicate first."""
    if value in buffer:
        buffer.remove(value)
    buffer.append(value)
    if len(buffer) > limit:
        del buffer[: len(buffer) - limit]


def _goal_progress_weights(sources: SourceBundle) -> dict[str, float]:
    """Read goal-progress rule weights from state-update source."""
    defaults = {
        "focus_session": 0.45,
        "save_on_goal_aligned_post": 0.2,
        "comment_on_goal_aligned_post": 0.12,
        "repeated_hide_on_goal_topic": 0.2,
    }
    rules = sources.require("state_update_rules").get("goal_progress_rules", [])
    for rule in rules:
        signal = str(rule.get("signal", ""))
        weight = float(rule.get("weight", defaults.get(signal, 0.0)))
        if signal in defaults:
            defaults[signal] = weight
    return defaults
