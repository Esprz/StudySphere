"""Ranking and exposure generation for simulator v2 Phase 2."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from math import exp
import re

from config.models import (
    ActivityState,
    ExposureRecord,
    PostRecord,
    RankedCandidate,
    SessionContext,
    SourceBundle,
    UserProfile,
    WorldState,
)
from core.ids import new_id
from core.time import clip_0_1


def build_candidate_pool(
    user: UserProfile,
    session: SessionContext,
    activity_state: ActivityState,
    world_state: WorldState,
    rng: random.Random,
) -> list[PostRecord]:
    posts = world_state.posts
    if not posts:
        return []

    primary = [p for p in posts if p.topic == user.primary_interest]
    secondary = [p for p in posts if p.topic in user.secondary_interests]
    goal_aligned = [p for p in posts if p.topic == activity_state.topic]
    followed_authors = world_state.follow_graph.get(user.user_id, set())
    social = [p for p in posts if p.author_id in followed_authors]
    recent = sorted(posts, key=lambda p: p.created_at, reverse=True)[:40]

    off_interest = [
        p for p in posts if p.topic not in {user.primary_interest, *user.secondary_interests}
    ]
    rng.shuffle(off_interest)
    exploration_size = max(1, int(user.exploration_rate * 20))
    exploration = off_interest[:exploration_size]

    merged = [*primary, *secondary, *goal_aligned, *social, *recent, *exploration]
    deduped = _deduplicate_posts(merged)

    hidden_topics = set(world_state.user_memory.get(user.user_id, {}).get("recent_topics_hidden", []))
    if hidden_topics:
        deduped = [post for post in deduped if post.topic not in hidden_topics]
    return deduped[: session.candidate_pool_size]


def compute_topic_match(user: UserProfile, post: PostRecord) -> float:
    if post.topic == user.primary_interest:
        return 1.0
    if post.topic in user.secondary_interests:
        return 0.7
    return 0.15


def compute_goal_alignment(activity_state: ActivityState, post: PostRecord) -> float:
    if post.topic == activity_state.topic:
        return 1.0
    return 0.2


def compute_activity_alignment(activity_state: ActivityState, post: PostRecord) -> float:
    intent = activity_state.activity_intent
    format_bonus = 0.0
    if intent in {"Project_Execution", "Portfolio_Building"} and post.format in {"project_log", "experience_post"}:
        format_bonus = 0.25
    elif intent in {"Exam_Preparation", "Revision_Queueing"} and post.utility_style in {"checklist", "worked_example"}:
        format_bonus = 0.25
    elif intent in {"Discussion", "Peer_Support"} and post.social_affordance in {"question_inviting", "controversial"}:
        format_bonus = 0.25
    return clip_0_1((0.75 if post.topic == activity_state.topic else 0.2) + format_bonus)


def compute_freshness_bonus(post: PostRecord, now: datetime | None = None) -> float:
    now_utc = now or datetime.now(timezone.utc)
    age_hours = max(0.0, (now_utc - post.created_at).total_seconds() / 3600.0)
    # Smooth recency decay, still non-zero for older posts.
    return round(clip_0_1(exp(-age_hours / 72.0)), 4)


def compute_social_bonus(user: UserProfile, post: PostRecord, follow_graph: dict[str, set[str]]) -> float:
    return 1.0 if post.author_id in follow_graph.get(user.user_id, set()) else 0.0


def compute_exploration_bonus(user: UserProfile, post: PostRecord) -> float:
    if post.topic in {user.primary_interest, *user.secondary_interests}:
        return 0.0
    return round(clip_0_1(user.exploration_rate * 2.0), 4)


def score_exposure(
    *,
    topic_match: float,
    goal_alignment: float,
    activity_alignment: float,
    freshness_bonus: float,
    observed_quality: float,
    social_bonus: float,
    exploration_bonus: float,
    weights: dict[str, float] | None = None,
) -> float:
    effective_weights = weights or _default_score_weights()
    score = (
        effective_weights["topic_match"] * topic_match
        + effective_weights["goal_alignment"] * goal_alignment
        + effective_weights["activity_alignment"] * activity_alignment
        + effective_weights["freshness_bonus"] * freshness_bonus
        + effective_weights["observed_quality"] * observed_quality
        + effective_weights["social_bonus"] * social_bonus
        + effective_weights["exploration_bonus"] * exploration_bonus
    )
    return round(clip_0_1(score), 6)


def rank_candidates_for_exposure(
    user: UserProfile,
    activity_state: ActivityState,
    candidates: list[PostRecord],
    world_state: WorldState,
    sources: SourceBundle,
    rng: random.Random,
) -> list[RankedCandidate]:
    ranked: list[RankedCandidate] = []
    jitter_lo, jitter_hi = _candidate_jitter_range(sources)
    score_weights = _score_weights_from_sources(sources)

    for post in candidates:
        topic_match = compute_topic_match(user, post)
        goal_alignment = compute_goal_alignment(activity_state, post)
        activity_alignment = compute_activity_alignment(activity_state, post)
        freshness_bonus = compute_freshness_bonus(post)
        observed_quality = world_state.content_memory.get(post.post_id, {}).get("observed_quality", post.observed_quality)
        social_bonus = compute_social_bonus(user, post, world_state.follow_graph)
        exploration_bonus = compute_exploration_bonus(user, post)

        deterministic = score_exposure(
            topic_match=topic_match,
            goal_alignment=goal_alignment,
            activity_alignment=activity_alignment,
            freshness_bonus=freshness_bonus,
            observed_quality=float(observed_quality),
            social_bonus=social_bonus,
            exploration_bonus=exploration_bonus,
            weights=score_weights,
        )
        jitter = round(rng.uniform(jitter_lo, jitter_hi), 6)
        candidate_score = round(clip_0_1(deterministic + jitter), 6)
        breakdown = {
            "topic_match": round(topic_match, 6),
            "goal_alignment": round(goal_alignment, 6),
            "activity_alignment": round(activity_alignment, 6),
            "freshness_bonus": round(freshness_bonus, 6),
            "observed_quality": round(float(observed_quality), 6),
            "social_bonus": round(social_bonus, 6),
            "exploration_bonus": round(exploration_bonus, 6),
        }
        ranked.append(
            RankedCandidate(
                post_id=post.post_id,
                deterministic_exposure_score=deterministic,
                score_jitter=jitter,
                candidate_score=candidate_score,
                score_breakdown=breakdown,
            )
        )

    ranked.sort(key=lambda x: x.candidate_score, reverse=True)
    return ranked


def emit_exposures(
    user: UserProfile,
    session: SessionContext,
    ranked_candidates: list[RankedCandidate],
    world_state: WorldState,
    rng: random.Random,
    *,
    items_per_session: int,
) -> list[ExposureRecord]:
    top_items = ranked_candidates[:items_per_session]
    exposures: list[ExposureRecord] = []
    for idx, ranked in enumerate(top_items, start=1):
        post = world_state_post_lookup(world_state, ranked.post_id)
        exposures.append(
            ExposureRecord(
                exposure_id=new_id("e", rng=rng),
                session_id=session.session_id,
                user_id=user.user_id,
                post_id=ranked.post_id,
                surface=session.surface,
                timestamp=session.started_at,
                rank_position=idx,
                candidate_score=ranked.candidate_score,
                exposure_reasons=_derive_exposure_reasons(user, session, post),
                score_jitter=ranked.score_jitter,
                score_breakdown=ranked.score_breakdown,
                deterministic_exposure_score=ranked.deterministic_exposure_score,
                ranking_policy="internal_heuristic_v1",
                ranking_policy_version="1.0",
            )
        )
        world_state.content_memory[ranked.post_id]["exposure_count"] += 1
    return exposures


def world_state_post_lookup(world_state: WorldState, post_id: str) -> PostRecord:
    for post in world_state.posts:
        if post.post_id == post_id:
            return post
    raise KeyError(f"post_id not found: {post_id}")


def _deduplicate_posts(posts: list[PostRecord]) -> list[PostRecord]:
    seen: set[str] = set()
    deduped: list[PostRecord] = []
    for post in posts:
        if post.post_id in seen:
            continue
        seen.add(post.post_id)
        deduped.append(post)
    return deduped


def _derive_exposure_reasons(user: UserProfile, session: SessionContext, post: PostRecord) -> list[str]:
    reasons: list[str] = []
    if post.topic == user.primary_interest:
        reasons.append("primary_interest_match")
    elif post.topic in user.secondary_interests:
        reasons.append("secondary_interest_match")

    if post.topic == session.goal_topic:
        reasons.append("goal_aligned")

    if post.freshness_hours <= 24:
        reasons.append("recent")

    if not reasons:
        reasons.append("exploration")
    return reasons


def _candidate_jitter_range(sources: SourceBundle) -> tuple[float, float]:
    jitter = (
        sources.require("jitter_noise_rules")
        .get("rules", {})
        .get("candidate_score_jitter", {})
        .get("range", [-0.02, 0.02])
    )
    return float(jitter[0]), float(jitter[1])


def _default_score_weights() -> dict[str, float]:
    return {
        "topic_match": 0.30,
        "goal_alignment": 0.20,
        "activity_alignment": 0.18,
        "freshness_bonus": 0.10,
        "observed_quality": 0.12,
        "social_bonus": 0.05,
        "exploration_bonus": 0.05,
    }


def _score_weights_from_sources(sources: SourceBundle) -> dict[str, float]:
    functions = sources.require("decision_formulas").get("functions", [])
    entry = next((item for item in functions if item.get("name") == "score_exposure"), None)
    if entry is None:
        return _default_score_weights()

    formula = str(entry.get("formula", ""))
    pairs = re.findall(r"([0-9]*\.?[0-9]+)\*([a-zA-Z_][a-zA-Z0-9_]*)", formula)
    weights = {name: float(weight) for weight, name in pairs}
    required = set(_default_score_weights().keys())
    if not required.issubset(weights):
        return _default_score_weights()
    return {name: weights[name] for name in _default_score_weights()}
