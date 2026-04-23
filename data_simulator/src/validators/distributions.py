"""Batch-level distribution realism validation."""

from __future__ import annotations

from collections import Counter
from math import fsum
from statistics import mean
from typing import Any

from config.models import WorldState
from core.time import clip_0_1

ValidationIssue = dict[str, Any]


def validate_batch_distributions(world_state: WorldState) -> list[ValidationIssue]:
    """Validate coarse realism constraints at batch level."""
    issues: list[ValidationIssue] = []
    summary = summarize_batch_metrics(world_state)

    totals = summary["totals"]
    funnel = summary["interaction_funnel"]
    concentration = summary["concentration"]
    quality = summary["quality_distribution"]
    activity = summary["user_activity"]

    if totals["exposures"] == 0:
        _add_issue(
            issues,
            severity="error",
            code="empty_exposure_batch",
            message="batch contains no exposures",
            context={"exposure_count": 0},
        )
        return issues

    if summary["topic_distribution"]["coverage_ratio"] < 0.2:
        _add_issue(
            issues,
            severity="warning",
            code="low_topic_coverage",
            message="topic coverage ratio is low; batch may be too narrow",
            context={"coverage_ratio": summary["topic_distribution"]["coverage_ratio"]},
        )

    if funnel["view_rate"] <= 0.0:
        _add_issue(
            issues,
            severity="warning",
            code="zero_view_rate",
            message="view rate is zero; ranking/interaction dynamics may be degenerate",
            context={"view_rate": funnel["view_rate"]},
        )

    if funnel["save_rate"] > funnel["view_rate"] + 1e-9:
        _add_issue(
            issues,
            severity="error",
            code="save_rate_exceeds_view_rate",
            message="save rate cannot exceed view rate",
            context={"save_rate": funnel["save_rate"], "view_rate": funnel["view_rate"]},
        )

    if funnel["comment_rate"] > funnel["view_rate"] + 1e-9:
        _add_issue(
            issues,
            severity="error",
            code="comment_rate_exceeds_view_rate",
            message="comment rate cannot exceed view rate",
            context={"comment_rate": funnel["comment_rate"], "view_rate": funnel["view_rate"]},
        )

    off_interest_share = funnel["off_interest_click_share"]
    if off_interest_share < 0.005:
        _add_issue(
            issues,
            severity="warning",
            code="off_interest_click_share_too_low",
            message="off-interest click share is near zero; simulator may be too deterministic",
            context={"off_interest_click_share": off_interest_share},
        )
    if off_interest_share > 0.25:
        _add_issue(
            issues,
            severity="warning",
            code="off_interest_click_share_too_high",
            message="off-interest click share is unusually high",
            context={"off_interest_click_share": off_interest_share},
        )

    if concentration["top_creator_20pct_share"] < 0.30:
        _add_issue(
            issues,
            severity="warning",
            code="flat_creator_exposure_distribution",
            message="creator exposure concentration is too flat",
            context={"top_creator_20pct_share": concentration["top_creator_20pct_share"]},
        )
    if concentration["creator_exposure_gini"] < 0.12:
        _add_issue(
            issues,
            severity="warning",
            code="flat_creator_long_tail_shape",
            message="creator exposure gini is too low for expected long-tail behavior",
            context={"creator_exposure_gini": concentration["creator_exposure_gini"]},
        )

    if activity["session_count_gini"] < 0.08:
        _add_issue(
            issues,
            severity="warning",
            code="flat_user_activity_distribution",
            message="user session activity distribution is too flat",
            context={"session_count_gini": activity["session_count_gini"]},
        )

    if quality["true_quality_std"] < 0.05:
        _add_issue(
            issues,
            severity="warning",
            code="flat_true_quality_distribution",
            message="true_latent_quality has low variance; expected a skewed beta-like distribution",
            context={"true_quality_std": quality["true_quality_std"]},
        )

    return issues


def summarize_batch_metrics(world_state: WorldState) -> dict[str, Any]:
    """Compute batch-level metrics consumed by validation and report output."""
    posts_by_id = {post.post_id: post for post in world_state.posts}
    users_by_id = {user.user_id: user for user in world_state.users}

    topic_counts = Counter()
    creator_counts = Counter()
    for exposure in world_state.exposures:
        post = posts_by_id.get(exposure.post_id)
        if post is None:
            continue
        topic_counts[post.topic] += 1
        creator_counts[post.author_id] += 1

    interaction_counts = Counter(item.event_type for item in world_state.interactions)
    view_interactions = [item for item in world_state.interactions if item.event_type == "view"]
    off_interest_clicks = 0
    for item in view_interactions:
        user = users_by_id.get(item.user_id)
        post = posts_by_id.get(item.post_id)
        if user is None or post is None:
            continue
        if post.topic not in {user.primary_interest, *user.secondary_interests}:
            off_interest_clicks += 1

    exposures_count = len(world_state.exposures)
    view_count = interaction_counts.get("view", 0)
    save_count = interaction_counts.get("save", 0)
    comment_count = interaction_counts.get("comment", 0)

    session_counts_by_user = Counter(session.user_id for session in world_state.sessions)
    true_quality_values = [float(post.true_latent_quality) for post in world_state.posts]

    creator_exposure_counts = list(creator_counts.values())
    sorted_creator_counts = sorted(creator_exposure_counts, reverse=True)
    creator_count = len(sorted_creator_counts)
    top_k = max(1, int(round(creator_count * 0.2))) if creator_count > 0 else 0
    top_share = (
        fsum(sorted_creator_counts[:top_k]) / fsum(sorted_creator_counts)
        if sorted_creator_counts and fsum(sorted_creator_counts) > 0
        else 0.0
    )

    topic_distribution = {
        "distinct_topics_in_exposure": len(topic_counts),
        "total_topics_in_content": len({post.topic for post in world_state.posts}),
        "coverage_ratio": round(
            clip_0_1(len(topic_counts) / float(max(1, len({post.topic for post in world_state.posts})))),
            6,
        ),
        "top_topics": topic_counts.most_common(8),
    }

    interaction_funnel = {
        "exposure_count": exposures_count,
        "view_count": view_count,
        "like_count": interaction_counts.get("like", 0),
        "save_count": save_count,
        "comment_count": comment_count,
        "hide_count": interaction_counts.get("hide", 0),
        "scroll_past_count": interaction_counts.get("scroll_past", 0),
        "quick_bounce_count": interaction_counts.get("quick_bounce", 0),
        "view_rate": round(view_count / float(max(1, exposures_count)), 6),
        "save_rate": round(save_count / float(max(1, exposures_count)), 6),
        "comment_rate": round(comment_count / float(max(1, exposures_count)), 6),
        "off_interest_click_share": round(
            off_interest_clicks / float(max(1, view_count)),
            6,
        ),
    }

    return {
        "totals": {
            "users": len(world_state.users),
            "posts": len(world_state.posts),
            "sessions": len(world_state.sessions),
            "exposures": len(world_state.exposures),
            "interactions": len(world_state.interactions),
            "focus_sessions": len(world_state.focus_sessions),
            "propensity_logs": len(world_state.propensity_logs),
        },
        "topic_distribution": topic_distribution,
        "interaction_funnel": interaction_funnel,
        "concentration": {
            "creator_count_in_exposure": creator_count,
            "top_creator_20pct_share": round(top_share, 6),
            "creator_exposure_gini": round(_gini(creator_exposure_counts), 6),
        },
        "user_activity": {
            "active_user_count": len(session_counts_by_user),
            "session_count_gini": round(_gini(list(session_counts_by_user.values())), 6),
            "mean_sessions_per_active_user": round(
                mean(session_counts_by_user.values()) if session_counts_by_user else 0.0,
                6,
            ),
        },
        "quality_distribution": {
            "true_quality_mean": round(mean(true_quality_values) if true_quality_values else 0.0, 6),
            "true_quality_std": round(_stddev(true_quality_values), 6),
        },
    }


def _stddev(values: list[float]) -> float:
    """Compute population standard deviation without external dependencies."""
    if not values:
        return 0.0
    m = mean(values)
    return (fsum((value - m) ** 2 for value in values) / float(len(values))) ** 0.5


def _gini(values: list[int | float]) -> float:
    """Compute Gini coefficient for concentration/skew estimates."""
    clean = [float(v) for v in values if float(v) >= 0.0]
    n = len(clean)
    if n == 0:
        return 0.0
    total = fsum(clean)
    if total <= 0.0:
        return 0.0

    sorted_values = sorted(clean)
    weighted_sum = fsum((idx + 1) * value for idx, value in enumerate(sorted_values))
    return max(0.0, min(1.0, (2.0 * weighted_sum) / (n * total) - (n + 1.0) / n))


def _add_issue(
    issues: list[ValidationIssue],
    *,
    severity: str,
    code: str,
    message: str,
    context: dict[str, Any],
) -> None:
    """Append one distribution validation issue with explicit severity."""
    issues.append(
        {
            "validator": "distributions",
            "severity": severity,
            "code": code,
            "message": message,
            "context": context,
        }
    )
