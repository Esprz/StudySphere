"""Interaction simulation for Phase 3."""

from __future__ import annotations

import random
from datetime import timedelta

from config.models import ActivityState, ExposureRecord, InteractionRecord, PostRecord, SessionContext, SourceBundle, UserProfile, WorldState
from core.ids import new_id
from core.time import clip_0_1
from generators.ranking import compute_activity_alignment, compute_goal_alignment, compute_topic_match
from generators.sessions import maybe_transition_activity_intent


def compute_view_probability(
    *,
    user: UserProfile,
    exposure: ExposureRecord,
    post: PostRecord,
    activity_state: ActivityState,
    fatigue: float,
    sources: SourceBundle,
) -> float:
    """Compute deterministic view probability before floor and jitter adjustments."""
    params = _session_params(sources)
    difficulty_distance = abs(activity_state.target_difficulty - post.difficulty) / 4.0
    hook_strength = compute_hook_strength(post, observed_quality=post.observed_quality)
    score = (
        float(params.get("base_view_probability", 0.22))
        + 0.45 * exposure.candidate_score
        + 0.08 * user.curiosity_level
        + 0.06 * hook_strength
        - 0.035 * float(max(0, exposure.rank_position - 1))
        - 0.18 * fatigue
        - 0.06 * difficulty_distance
    )
    return round(clip_0_1(score), 6)


def compute_off_interest_click_floor(user: UserProfile, post: PostRecord, sources: SourceBundle) -> float:
    """Return bounded minimum click-through probability for off-interest posts."""
    if post.topic in {user.primary_interest, *user.secondary_interests}:
        return 0.0

    rule = (
        sources.require("jitter_noise_rules")
        .get("rules", {})
        .get("off_interest_click_floor", {})
    )
    base = float(rule.get("base", 0.01))
    curiosity_multiplier = float(rule.get("curiosity_multiplier", 0.03))
    upper = float(rule.get("max", 0.05))
    floor = base + curiosity_multiplier * user.curiosity_level
    return round(clip_0_1(min(floor, upper)), 6)


def sample_negative_signal_after_skip(
    *,
    user: UserProfile,
    exposure: ExposureRecord,
    post: PostRecord,
    feed_dwell_ms: int,
    deterministic_prob: float,
    final_prob: float,
    prob_jitter: float,
    sampling_policy: str,
    rng: random.Random,
    timestamp_offset_s: int,
    session_started_at,
    sources: SourceBundle,
) -> InteractionRecord:
    """Create a skip-path negative event (`scroll_past` or `hide`) after no view."""
    del sampling_policy
    topic_match = compute_topic_match(user, post)
    hide_prob = clip_0_1(0.03 + 0.12 * (1.0 - topic_match) + 0.05 * (1.0 - exposure.candidate_score))
    if post.topic not in {user.primary_interest, *user.secondary_interests}:
        hide_prob = clip_0_1(hide_prob + 0.08)

    event_type = "hide" if rng.random() < hide_prob else "scroll_past"
    return InteractionRecord(
        interaction_id=new_id("i", rng=rng),
        event_type=event_type,
        user_id=user.user_id,
        post_id=post.post_id,
        session_id=exposure.session_id,
        exposure_id=exposure.exposure_id,
        timestamp=session_started_at + timedelta(seconds=timestamp_offset_s),
        feed_dwell_ms=feed_dwell_ms,
        reason_code="low_relevance_after_exposure" if event_type == "scroll_past" else "explicit_dislike_after_exposure",
        negative_signal_strength=_negative_strength(sources, event_type),
        deterministic_prob=deterministic_prob,
        final_prob=final_prob,
        prob_jitter=prob_jitter,
        sampling_policy="internal_heuristic_v1",
        sampled_outcome=False,
    )


def generate_view_interaction(
    *,
    user: UserProfile,
    exposure: ExposureRecord,
    post: PostRecord,
    feed_dwell_ms: int,
    dwell_ms: int,
    deterministic_prob: float,
    final_prob: float,
    prob_jitter: float,
    rng: random.Random,
    timestamp_offset_s: int,
    session_started_at,
) -> InteractionRecord:
    """Create the canonical `view` interaction linked to an exposure."""
    return InteractionRecord(
        interaction_id=new_id("i", rng=rng),
        event_type="view",
        user_id=user.user_id,
        post_id=post.post_id,
        session_id=exposure.session_id,
        exposure_id=exposure.exposure_id,
        timestamp=session_started_at + timedelta(seconds=timestamp_offset_s),
        view_depth=_view_depth_from_dwell(dwell_ms),
        feed_dwell_ms=feed_dwell_ms,
        dwell_ms=dwell_ms,
        deterministic_prob=deterministic_prob,
        final_prob=final_prob,
        prob_jitter=prob_jitter,
        sampling_policy="internal_heuristic_v1",
        sampled_outcome=True,
    )


def sample_like_probability(
    *,
    user: UserProfile,
    post: PostRecord,
    activity_state: ActivityState,
    detail_dwell_norm: float,
    action_prob_jitter: float,
) -> float:
    """Sample-like propensity from topic/activity fit, quality, and dwell signals."""
    topic_match = compute_topic_match(user, post)
    activity_alignment = compute_activity_alignment(activity_state, post)
    score = (
        0.10
        + 0.24 * topic_match
        + 0.12 * activity_alignment
        + 0.20 * post.observed_quality
        + 0.08 * user.social_affinity
        + 0.12 * detail_dwell_norm
        + action_prob_jitter
    )
    return round(clip_0_1(score), 6)


def sample_save_probability(
    *,
    user: UserProfile,
    post: PostRecord,
    activity_state: ActivityState,
    detail_dwell_norm: float,
    action_prob_jitter: float,
) -> float:
    """Sample-save propensity with stronger utility and goal alignment dependence."""
    del user
    goal_alignment = compute_goal_alignment(activity_state, post)
    activity_alignment = compute_activity_alignment(activity_state, post)
    utility_match = compute_utility_match(activity_state, post)
    score = (
        0.08
        + 0.24 * goal_alignment
        + 0.18 * activity_alignment
        + 0.20 * utility_match
        + 0.12 * post.observed_quality
        + 0.12 * detail_dwell_norm
        + action_prob_jitter
    )
    return round(clip_0_1(score), 6)


def sample_comment_probability(
    *,
    user: UserProfile,
    post: PostRecord,
    activity_state: ActivityState,
    detail_dwell_norm: float,
    action_prob_jitter: float,
) -> float:
    """Sample-comment propensity driven by social affinity and discussion affordance."""
    activity_alignment = compute_activity_alignment(activity_state, post)
    discussion_affordance = compute_discussion_affordance(post)
    score = (
        0.03
        + 0.16 * activity_alignment
        + 0.22 * user.social_affinity
        + 0.20 * discussion_affordance
        + 0.10 * detail_dwell_norm
        + action_prob_jitter
    )
    return round(clip_0_1(score), 6)


def simulate_session_interactions(
    *,
    user: UserProfile,
    session: SessionContext,
    activity_state: ActivityState,
    exposures: list[ExposureRecord],
    world_state: WorldState,
    sources: SourceBundle,
    rng: random.Random,
) -> tuple[list[InteractionRecord], ActivityState, int]:
    """Simulate ordered interaction events for one session's ranked exposures."""
    if not exposures:
        return [], activity_state, 0

    params = _session_params(sources)
    transition_every = int(params.get("intent_transition_check_every_n_exposures", 3))
    transition_prob = float(params.get("intent_transition_base_probability", 0.12))

    interactions: list[InteractionRecord] = []
    current_activity = activity_state
    transition_count = 0
    fatigue = session.fatigue_start
    view_count = 0
    event_offset_s = 0

    ordered_exposures = sorted(exposures, key=lambda x: x.rank_position)
    for exposure_index, exposure in enumerate(ordered_exposures, start=1):
        # Periodically allow short-term intent drift as fatigue/feedback accumulates.
        if transition_every > 0 and exposure_index % transition_every == 0:
            transitioned = maybe_transition_activity_intent(
                user=user,
                session=session,
                current_activity_state=current_activity,
                interactions_so_far=interactions,
                fatigue=fatigue,
                rng=rng,
                transition_probability=transition_prob,
            )
            if transitioned.activity_intent != current_activity.activity_intent:
                transition_count += 1
            current_activity = transitioned

        post = _lookup_post(world_state, exposure.post_id)
        feed_dwell_ms = sample_feed_dwell_ms(sources, rng)

        deterministic_view_prob = compute_view_probability(
            user=user,
            exposure=exposure,
            post=post,
            activity_state=current_activity,
            fatigue=fatigue,
            sources=sources,
        )
        floor_prob = compute_off_interest_click_floor(user, post, sources)
        view_prob_jitter = sample_view_probability_jitter(sources, rng)
        final_view_prob = round(clip_0_1(max(deterministic_view_prob, floor_prob) + view_prob_jitter), 6)

        should_view = rng.random() < final_view_prob
        if not should_view:
            # Skip branch: emit a negative signal and increase fatigue modestly.
            negative_event = sample_negative_signal_after_skip(
                user=user,
                exposure=exposure,
                post=post,
                feed_dwell_ms=feed_dwell_ms,
                deterministic_prob=deterministic_view_prob,
                final_prob=final_view_prob,
                prob_jitter=view_prob_jitter,
                sampling_policy="internal_heuristic_v1",
                rng=rng,
                timestamp_offset_s=event_offset_s,
                session_started_at=session.started_at,
                sources=sources,
            )
            event_offset_s += 1
            interactions.append(negative_event)
            fatigue = update_fatigue_after_skip(fatigue, exposure.rank_position, sources)
            continue

        dwell_ms = sample_detail_dwell_ms(user, post, current_activity, sources, rng)
        view_event = generate_view_interaction(
            user=user,
            exposure=exposure,
            post=post,
            feed_dwell_ms=feed_dwell_ms,
            dwell_ms=dwell_ms,
            deterministic_prob=deterministic_view_prob,
            final_prob=final_view_prob,
            prob_jitter=view_prob_jitter,
            rng=rng,
            timestamp_offset_s=event_offset_s,
            session_started_at=session.started_at,
        )
        event_offset_s += 1
        interactions.append(view_event)
        view_count += 1

        if is_quick_bounce(dwell_ms, sources):
            # Quick bounce is a post-view negative branch and ends deep-action sampling.
            bounce = generate_quick_bounce_event(
                user=user,
                exposure=exposure,
                post=post,
                rng=rng,
                timestamp_offset_s=event_offset_s,
                session_started_at=session.started_at,
            )
            event_offset_s += 1
            interactions.append(bounce)
            fatigue = update_fatigue_after_bounce(fatigue, sources)
            continue

        detail_dwell_norm = normalize_detail_dwell(dwell_ms, sources)
        action_prob_jitter = sample_post_action_probability_jitter(sources, rng)
        deterministic_like = sample_like_probability(
            user=user,
            post=post,
            activity_state=current_activity,
            detail_dwell_norm=detail_dwell_norm,
            action_prob_jitter=0.0,
        )
        deterministic_save = sample_save_probability(
            user=user,
            post=post,
            activity_state=current_activity,
            detail_dwell_norm=detail_dwell_norm,
            action_prob_jitter=0.0,
        )
        deterministic_comment = sample_comment_probability(
            user=user,
            post=post,
            activity_state=current_activity,
            detail_dwell_norm=detail_dwell_norm,
            action_prob_jitter=0.0,
        )

        like_prob = sample_like_probability(
            user=user,
            post=post,
            activity_state=current_activity,
            detail_dwell_norm=detail_dwell_norm,
            action_prob_jitter=action_prob_jitter,
        )
        save_prob = sample_save_probability(
            user=user,
            post=post,
            activity_state=current_activity,
            detail_dwell_norm=detail_dwell_norm,
            action_prob_jitter=action_prob_jitter,
        )
        comment_prob = sample_comment_probability(
            user=user,
            post=post,
            activity_state=current_activity,
            detail_dwell_norm=detail_dwell_norm,
            action_prob_jitter=action_prob_jitter,
        )

        if rng.random() < like_prob:
            like_event = _generate_action_event(
                event_type="like",
                user=user,
                exposure=exposure,
                post=post,
                rng=rng,
                timestamp_offset_s=event_offset_s,
                session_started_at=session.started_at,
                deterministic_prob=deterministic_like,
                final_prob=like_prob,
                prob_jitter=action_prob_jitter,
                comment_text=None,
            )
            event_offset_s += 1
            interactions.append(like_event)

        if rng.random() < save_prob:
            save_event = _generate_action_event(
                event_type="save",
                user=user,
                exposure=exposure,
                post=post,
                rng=rng,
                timestamp_offset_s=event_offset_s,
                session_started_at=session.started_at,
                deterministic_prob=deterministic_save,
                final_prob=save_prob,
                prob_jitter=action_prob_jitter,
                comment_text=None,
            )
            event_offset_s += 1
            interactions.append(save_event)

        if rng.random() < comment_prob:
            comment_event = _generate_action_event(
                event_type="comment",
                user=user,
                exposure=exposure,
                post=post,
                rng=rng,
                timestamp_offset_s=event_offset_s,
                session_started_at=session.started_at,
                deterministic_prob=deterministic_comment,
                final_prob=comment_prob,
                prob_jitter=action_prob_jitter,
                comment_text=f"Useful take on {post.topic.lower()}.",
            )
            event_offset_s += 1
            interactions.append(comment_event)

        hide_prob = _hide_after_view_probability(user, post, fatigue)
        if rng.random() < hide_prob:
            hide_event = InteractionRecord(
                interaction_id=new_id("i", rng=rng),
                event_type="hide",
                user_id=user.user_id,
                post_id=post.post_id,
                session_id=exposure.session_id,
                exposure_id=exposure.exposure_id,
                timestamp=session.started_at + timedelta(seconds=event_offset_s),
                reason_code="explicit_dislike_after_view",
                negative_signal_strength=_negative_strength(sources, "hide"),
                deterministic_prob=hide_prob,
                final_prob=hide_prob,
                prob_jitter=0.0,
                sampling_policy="internal_heuristic_v1",
                sampled_outcome=True,
            )
            event_offset_s += 1
            interactions.append(hide_event)

        fatigue = update_fatigue_after_view(
            fatigue=fatigue,
            rank_position=exposure.rank_position,
            dwell_ms=dwell_ms,
            viewed_count=view_count,
            sources=sources,
        )

    return interactions, current_activity, transition_count


def generate_quick_bounce_event(
    *,
    user: UserProfile,
    exposure: ExposureRecord,
    post: PostRecord,
    rng: random.Random,
    timestamp_offset_s: int,
    session_started_at,
) -> InteractionRecord:
    """Create `quick_bounce` event after shallow detail dwell."""
    return InteractionRecord(
        interaction_id=new_id("i", rng=rng),
        event_type="quick_bounce",
        user_id=user.user_id,
        post_id=post.post_id,
        session_id=exposure.session_id,
        exposure_id=exposure.exposure_id,
        timestamp=session_started_at + timedelta(seconds=timestamp_offset_s),
        reason_code="detail_dwell_too_short",
        negative_signal_strength="medium_negative",
    )


def sample_feed_dwell_ms(sources: SourceBundle, rng: random.Random) -> int:
    """Sample feed dwell duration from configured range."""
    lo, hi = _dwell_range(sources, "feed_dwell_ms_range", (250, 2600))
    return rng.randint(lo, hi)


def sample_detail_dwell_ms(
    user: UserProfile,
    post: PostRecord,
    activity_state: ActivityState,
    sources: SourceBundle,
    rng: random.Random,
) -> int:
    """Sample detail dwell duration conditioned on diligence and difficulty distance."""
    lo, hi = _dwell_range(sources, "detail_dwell_ms_range", (2500, 120000))
    difficulty_distance = abs(activity_state.target_difficulty - post.difficulty) / 4.0
    attention = clip_0_1(0.45 + 0.35 * user.diligence_level + 0.20 * (1.0 - difficulty_distance))
    mean_ms = lo + int((hi - lo) * attention)
    jitter = int((hi - lo) * rng.uniform(-0.12, 0.12))
    return max(lo, min(hi, mean_ms + jitter))


def normalize_detail_dwell(dwell_ms: int, sources: SourceBundle) -> float:
    """Normalize detail dwell milliseconds into [0, 1] using configured bounds."""
    lo, hi = _dwell_range(sources, "detail_dwell_ms_range", (2500, 120000))
    if hi <= lo:
        return 0.0
    return round(clip_0_1((dwell_ms - lo) / float(hi - lo)), 6)


def sample_view_probability_jitter(sources: SourceBundle, rng: random.Random) -> float:
    """Sample bounded additive jitter for view probability."""
    lo, hi = _jitter_range(sources, "view_probability_jitter", (-0.015, 0.015))
    return round(rng.uniform(lo, hi), 6)


def sample_post_action_probability_jitter(sources: SourceBundle, rng: random.Random) -> float:
    """Sample bounded additive jitter for post-view action probabilities."""
    lo, hi = _jitter_range(sources, "post_action_probability_jitter", (-0.01, 0.01))
    return round(rng.uniform(lo, hi), 6)


def is_quick_bounce(dwell_ms: int, sources: SourceBundle) -> bool:
    """Return True when detail dwell is below quick-bounce threshold."""
    threshold = int(_session_params(sources).get("quick_bounce_dwell_threshold_ms", 4000))
    return dwell_ms <= threshold


def update_fatigue_after_skip(fatigue: float, rank_position: int, sources: SourceBundle) -> float:
    """Update session fatigue after skipping an exposure."""
    params = _session_params(sources)
    base = float(params.get("fatigue_increase_per_skip", 0.02))
    rank_penalty = max(0.0, float(rank_position - 1)) * 0.002
    return round(clip_0_1(fatigue + base + rank_penalty), 6)


def update_fatigue_after_bounce(fatigue: float, sources: SourceBundle) -> float:
    """Update fatigue after quick-bounce behavior."""
    base_view = float(_session_params(sources).get("fatigue_increase_per_view", 0.08))
    return round(clip_0_1(fatigue + base_view * 0.75), 6)


def update_fatigue_after_view(
    *,
    fatigue: float,
    rank_position: int,
    dwell_ms: int,
    viewed_count: int,
    sources: SourceBundle,
) -> float:
    """Update fatigue after a full view, accounting for depth and view count."""
    params = _session_params(sources)
    increase = float(params.get("fatigue_increase_per_view", 0.08))
    meaningful_limit = int(params.get("max_meaningful_views_per_session", 6))
    if viewed_count > meaningful_limit:
        increase += 0.03
    if dwell_ms >= 60000:
        increase += 0.02
    increase += max(0.0, float(rank_position - 1)) * 0.0015
    return round(clip_0_1(fatigue + increase), 6)


def compute_hook_strength(post: PostRecord, *, observed_quality: float) -> float:
    """Estimate hook strength from quality, format, and social affordances."""
    format_bonus = {
        "qa_post": 0.22,
        "experience_post": 0.16,
        "short_post": 0.10,
        "project_log": 0.14,
        "resource_post": 0.12,
        "study_note": 0.08,
        "reflection_post": 0.06,
    }.get(post.format, 0.05)
    social_bonus = {
        "question_inviting": 0.18,
        "controversial": 0.22,
        "high_agreement": 0.10,
        "accountability_friendly": 0.13,
        "low_discussion": 0.03,
    }.get(post.social_affordance, 0.05)
    return round(clip_0_1(0.55 * observed_quality + format_bonus + social_bonus), 6)


def compute_utility_match(activity_state: ActivityState, post: PostRecord) -> float:
    """Score how useful the post style is for the current short-term intent."""
    intent = activity_state.activity_intent
    style = post.utility_style

    if intent in {"Exam_Preparation", "Revision_Queueing"}:
        return 1.0 if style in {"worked_example", "checklist", "comparison_breakdown"} else 0.3
    if intent in {"Project_Execution", "Portfolio_Building"}:
        return 1.0 if style in {"checklist", "reference_dump"} else 0.35
    if intent in {"Concept_Learning", "Resource_Collecting"}:
        return 1.0 if style in {"overview", "worked_example", "reference_dump"} else 0.4
    return 0.45


def compute_discussion_affordance(post: PostRecord) -> float:
    """Map social affordance label to a normalized discussion propensity signal."""
    return {
        "question_inviting": 1.0,
        "controversial": 0.9,
        "accountability_friendly": 0.65,
        "high_agreement": 0.45,
        "low_discussion": 0.15,
    }.get(post.social_affordance, 0.25)


def _generate_action_event(
    *,
    event_type: str,
    user: UserProfile,
    exposure: ExposureRecord,
    post: PostRecord,
    rng: random.Random,
    timestamp_offset_s: int,
    session_started_at,
    deterministic_prob: float,
    final_prob: float,
    prob_jitter: float,
    comment_text: str | None,
) -> InteractionRecord:
    """Build a generic post-view action event (`like`/`save`/`comment`)."""
    return InteractionRecord(
        interaction_id=new_id("i", rng=rng),
        event_type=event_type,
        user_id=user.user_id,
        post_id=post.post_id,
        session_id=exposure.session_id,
        exposure_id=exposure.exposure_id,
        timestamp=session_started_at + timedelta(seconds=timestamp_offset_s),
        comment_text=comment_text,
        deterministic_prob=deterministic_prob,
        final_prob=final_prob,
        prob_jitter=prob_jitter,
        sampling_policy="internal_heuristic_v1",
        sampled_outcome=True,
    )


def _hide_after_view_probability(user: UserProfile, post: PostRecord, fatigue: float) -> float:
    """Compute hide probability after view from mismatch and fatigue."""
    topic_match = compute_topic_match(user, post)
    return round(clip_0_1(0.015 + 0.09 * (1.0 - topic_match) + 0.06 * fatigue), 6)


def _view_depth_from_dwell(dwell_ms: int) -> str:
    """Bucket dwell time into shallow/medium/deep view depth labels."""
    if dwell_ms < 9000:
        return "shallow"
    if dwell_ms < 35000:
        return "medium"
    return "deep"


def _session_params(sources: SourceBundle) -> dict[str, object]:
    """Read session dynamic parameters from loaded source bundle."""
    return sources.require("session_dynamics").get("parameters", {})


def _jitter_range(sources: SourceBundle, rule_name: str, default: tuple[float, float]) -> tuple[float, float]:
    """Fetch jitter range for a rule, with explicit default fallback."""
    rule = (
        sources.require("jitter_noise_rules")
        .get("rules", {})
        .get(rule_name, {})
        .get("range", [default[0], default[1]])
    )
    return float(rule[0]), float(rule[1])


def _dwell_range(sources: SourceBundle, key: str, default: tuple[int, int]) -> tuple[int, int]:
    """Fetch dwell-time range for a configured key with fallback values."""
    values = _session_params(sources).get(key, [default[0], default[1]])
    return int(values[0]), int(values[1])


def _lookup_post(world_state: WorldState, post_id: str) -> PostRecord:
    """Resolve a post by id from world state."""
    for post in world_state.posts:
        if post.post_id == post_id:
            return post
    raise KeyError(f"post_id not found: {post_id}")


def _negative_strength(sources: SourceBundle, event_type: str) -> str:
    """Map negative event type to strength label from taxonomy."""
    entries = sources.require("negative_interaction_taxonomy").get("events", [])
    for entry in entries:
        if entry.get("event_type") == event_type:
            return str(entry.get("strength", "weak_negative"))
    return "weak_negative"
