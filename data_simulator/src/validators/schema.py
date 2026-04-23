"""Schema validation for simulator world state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from config.models import WorldState

ValidationIssue = dict[str, Any]


def validate_schema(world_state: WorldState) -> list[ValidationIssue]:
    """Validate required fields, numeric ranges, and type constraints."""
    issues: list[ValidationIssue] = []
    allowed_interaction_events = {"scroll_past", "hide", "view", "quick_bounce", "like", "save", "comment"}

    for user in world_state.users:
        _check_type(issues, "schema", "user_id_type", isinstance(user.user_id, str), {"user_id": user.user_id})
        _check_range(issues, "user_curiosity_range", user.curiosity_level, 0.0, 1.0, {"user_id": user.user_id})
        _check_range(issues, "user_diligence_range", user.diligence_level, 0.0, 1.0, {"user_id": user.user_id})
        _check_range(issues, "user_social_affinity_range", user.social_affinity, 0.0, 1.0, {"user_id": user.user_id})
        _check_range(issues, "user_exploration_rate_range", user.exploration_rate, 0.0, 0.5, {"user_id": user.user_id})
        _check_range(issues, "user_drift_rate_range", user.drift_rate, 0.0, 0.3, {"user_id": user.user_id})

    allowed_goal_states = {"active", "completed", "dropped"}
    for goal_list in world_state.goals_by_user.values():
        for goal in goal_list:
            _check_range(issues, "goal_priority_range", goal.priority, 0.0, 1.0, {"goal_id": goal.goal_id})
            _check_range(issues, "goal_strength_range", goal.strength, 0.0, 1.0, {"goal_id": goal.goal_id})
            _check_range(issues, "goal_progress_range", goal.progress, 0.0, 1.0, {"goal_id": goal.goal_id})
            _check_type(
                issues,
                "schema",
                "goal_progress_state_enum",
                goal.progress_state in allowed_goal_states,
                {"goal_id": goal.goal_id, "progress_state": goal.progress_state},
            )

    for post in world_state.posts:
        _check_range(issues, "post_difficulty_range", float(post.difficulty), 1.0, 5.0, {"post_id": post.post_id})
        _check_range(issues, "post_true_quality_range", post.true_latent_quality, 0.0, 1.0, {"post_id": post.post_id})
        _check_range(issues, "post_observed_quality_range", post.observed_quality, 0.0, 1.0, {"post_id": post.post_id})

    for exposure in world_state.exposures:
        _check_range(
            issues,
            "exposure_candidate_score_range",
            exposure.candidate_score,
            0.0,
            1.0,
            {"exposure_id": exposure.exposure_id},
        )
        _check_type(
            issues,
            "schema",
            "exposure_rank_position_positive",
            exposure.rank_position >= 1,
            {"exposure_id": exposure.exposure_id, "rank_position": exposure.rank_position},
        )

    for interaction in world_state.interactions:
        _check_type(
            issues,
            "schema",
            "interaction_event_type_enum",
            interaction.event_type in allowed_interaction_events,
            {"interaction_id": interaction.interaction_id, "event_type": interaction.event_type},
        )
        _check_type(
            issues,
            "schema",
            "interaction_timestamp_type",
            isinstance(interaction.timestamp, datetime),
            {"interaction_id": interaction.interaction_id},
        )
        if interaction.deterministic_prob is not None:
            _check_range(
                issues,
                "interaction_deterministic_prob_range",
                interaction.deterministic_prob,
                0.0,
                1.0,
                {"interaction_id": interaction.interaction_id},
            )
        if interaction.final_prob is not None:
            _check_range(
                issues,
                "interaction_final_prob_range",
                interaction.final_prob,
                0.0,
                1.0,
                {"interaction_id": interaction.interaction_id},
            )
        if interaction.sampled_outcome is not None:
            _check_type(
                issues,
                "schema",
                "interaction_sampled_outcome_bool",
                isinstance(interaction.sampled_outcome, bool),
                {"interaction_id": interaction.interaction_id},
            )

    for focus in world_state.focus_sessions:
        _check_type(
            issues,
            "schema",
            "focus_time_order",
            focus.ended_at >= focus.started_at,
            {"focus_id": focus.focus_id},
        )
        if focus.deterministic_focus_prob is not None:
            _check_range(
                issues,
                "focus_deterministic_prob_range",
                focus.deterministic_focus_prob,
                0.0,
                1.0,
                {"focus_id": focus.focus_id},
            )
        if focus.final_focus_prob is not None:
            _check_range(
                issues,
                "focus_final_prob_range",
                focus.final_focus_prob,
                0.0,
                1.0,
                {"focus_id": focus.focus_id},
            )

    for log in world_state.propensity_logs:
        if log.deterministic_prob is not None:
            _check_range(
                issues,
                "propensity_deterministic_prob_range",
                log.deterministic_prob,
                0.0,
                1.0,
                {"log_id": log.log_id},
            )
        if log.final_prob is not None:
            _check_range(
                issues,
                "propensity_final_prob_range",
                log.final_prob,
                0.0,
                1.0,
                {"log_id": log.log_id},
            )
        if log.sampled_outcome is not None:
            _check_type(
                issues,
                "schema",
                "propensity_sampled_outcome_bool",
                isinstance(log.sampled_outcome, bool),
                {"log_id": log.log_id},
            )

    return issues


def _check_range(
    issues: list[ValidationIssue],
    code: str,
    value: float,
    low: float,
    high: float,
    context: dict[str, Any],
) -> None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        issues.append(
            {
                "validator": "schema",
                "severity": "error",
                "code": code,
                "message": f"value '{value}' is not numeric",
                "context": context,
            }
        )
        return
    if low <= numeric <= high:
        return
    issues.append(
        {
            "validator": "schema",
            "severity": "error",
            "code": code,
            "message": f"value {value} outside [{low}, {high}]",
            "context": context,
        }
    )


def _check_type(
    issues: list[ValidationIssue],
    validator: str,
    code: str,
    condition: bool,
    context: dict[str, Any],
) -> None:
    if condition:
        return
    issues.append(
        {
            "validator": validator,
            "severity": "error",
            "code": code,
            "message": "type/constraint check failed",
            "context": context,
        }
    )
