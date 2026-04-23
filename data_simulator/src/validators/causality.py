"""Causal-order and propensity consistency validation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from config.models import WorldState
from core.time import clip_0_1

ValidationIssue = dict[str, Any]

_POST_VIEW_EVENTS = {"quick_bounce", "like", "save", "comment"}
_INTERACTION_STAGE_TO_EVENT = {
    "view_decision": "view",
    "like_decision": "like",
    "save_decision": "save",
    "comment_decision": "comment",
    "hide_after_view_decision": "hide",
}
_OUTCOME_STAGES = {
    "focus_decision",
    "follow_decision",
    "task_create_decision",
    "task_complete_decision",
}


def validate_causality(world_state: WorldState) -> list[ValidationIssue]:
    """Validate impossible event orders and cross-entity causal constraints."""
    issues: list[ValidationIssue] = []

    exposures = {exposure.exposure_id: exposure for exposure in world_state.exposures}
    sessions = {session.session_id: session for session in world_state.sessions}
    interactions_by_session = defaultdict(list)
    viewed_posts_by_session: dict[str, set[str]] = defaultdict(set)
    viewed_exposures: set[str] = set()
    last_timestamp_by_session: dict[str, object] = {}

    ordered_interactions = sorted(
        world_state.interactions,
        key=lambda item: (item.timestamp, item.session_id, item.interaction_id),
    )
    for interaction in ordered_interactions:
        exposure = exposures.get(interaction.exposure_id)
        if exposure is None:
            _add_issue(
                issues,
                code="view_without_exposure",
                message="interaction references missing exposure",
                context={"interaction_id": interaction.interaction_id, "event_type": interaction.event_type},
                validator="causality",
            )
            continue

        session = sessions.get(interaction.session_id)
        if session is None:
            _add_issue(
                issues,
                code="interaction_without_session",
                message="interaction references missing session",
                context={"interaction_id": interaction.interaction_id, "session_id": interaction.session_id},
                validator="causality",
            )
            continue

        if interaction.timestamp < session.started_at:
            _add_issue(
                issues,
                code="interaction_before_session_start",
                message="interaction timestamp is earlier than session start",
                context={"interaction_id": interaction.interaction_id, "session_id": session.session_id},
                validator="causality",
            )

        previous_timestamp = last_timestamp_by_session.get(interaction.session_id)
        if previous_timestamp is not None and interaction.timestamp < previous_timestamp:
            _add_issue(
                issues,
                code="non_monotonic_session_timestamps",
                message="interaction timestamps must be monotonic within one session",
                context={"interaction_id": interaction.interaction_id, "session_id": interaction.session_id},
                validator="causality",
            )
        last_timestamp_by_session[interaction.session_id] = interaction.timestamp

        interactions_by_session[interaction.session_id].append(interaction)
        if interaction.event_type == "view":
            viewed_exposures.add(interaction.exposure_id)
            viewed_posts_by_session[interaction.session_id].add(interaction.post_id)
            continue

        if interaction.event_type in _POST_VIEW_EVENTS and interaction.exposure_id not in viewed_exposures:
            _add_issue(
                issues,
                code="post_view_action_without_view",
                message="post-view action occurred before a valid view",
                context={
                    "interaction_id": interaction.interaction_id,
                    "event_type": interaction.event_type,
                    "exposure_id": interaction.exposure_id,
                },
                validator="causality",
            )

    for focus in world_state.focus_sessions:
        session = sessions.get(focus.session_id)
        if session is None:
            _add_issue(
                issues,
                code="focus_without_session",
                message="focus session references missing parent session",
                context={"focus_id": focus.focus_id, "session_id": focus.session_id},
                validator="causality",
            )
            continue

        session_interactions = interactions_by_session.get(focus.session_id, [])
        if not session_interactions:
            _add_issue(
                issues,
                code="focus_without_completed_session",
                message="focus session must follow a session with interactions",
                context={"focus_id": focus.focus_id, "session_id": focus.session_id},
                validator="causality",
            )
        if focus.started_at < session.started_at:
            _add_issue(
                issues,
                code="focus_before_session_start",
                message="focus session starts before the parent session",
                context={"focus_id": focus.focus_id, "session_id": focus.session_id},
                validator="causality",
            )
        viewed_posts = viewed_posts_by_session.get(focus.session_id, set())
        if focus.trigger_post_id not in viewed_posts:
            _add_issue(
                issues,
                code="focus_trigger_without_view",
                message="focus trigger post must have a preceding view in the same session",
                context={"focus_id": focus.focus_id, "trigger_post_id": focus.trigger_post_id},
                validator="causality",
            )

    return issues


def validate_propensity_logging(world_state: WorldState) -> list[ValidationIssue]:
    """Validate propensity-log completeness and sampled-outcome consistency."""
    issues: list[ValidationIssue] = []
    interactions = world_state.interactions
    logs = world_state.propensity_logs

    interactions_by_key: dict[tuple[str, str, str, str], int] = defaultdict(int)
    viewed_exposures: set[str] = set()
    sessions_with_view: set[str] = set()
    for interaction in interactions:
        key = (interaction.session_id, interaction.exposure_id, interaction.post_id, interaction.event_type)
        interactions_by_key[key] += 1
        if interaction.event_type == "view":
            viewed_exposures.add(interaction.exposure_id)
            sessions_with_view.add(interaction.session_id)

    focus_keys = {
        (focus.session_id, focus.trigger_post_id, focus.related_goal_id)
        for focus in world_state.focus_sessions
    }

    view_decision_logs_by_exposure: dict[str, int] = defaultdict(int)
    post_view_logs_by_exposure_stage: dict[tuple[str, str], int] = defaultdict(int)
    outcome_logs_by_session_stage: dict[tuple[str, str], int] = defaultdict(int)

    for log in logs:
        _validate_propensity_fields(issues, log)
        if log.deterministic_prob is None or log.final_prob is None or log.prob_jitter is None:
            continue
        _validate_propensity_formula(issues, log)

        if log.decision_stage == "view_decision" and log.exposure_id:
            view_decision_logs_by_exposure[log.exposure_id] += 1

        if log.decision_stage in {"like_decision", "save_decision", "comment_decision", "hide_after_view_decision"}:
            if log.exposure_id:
                post_view_logs_by_exposure_stage[(log.exposure_id, log.decision_stage)] += 1

        if log.decision_stage in _OUTCOME_STAGES:
            outcome_logs_by_session_stage[(log.session_id, log.decision_stage)] += 1

        _validate_propensity_outcome_match(
            issues=issues,
            log=log,
            interactions_by_key=interactions_by_key,
            viewed_exposures=viewed_exposures,
            focus_keys=focus_keys,
            world_state=world_state,
        )

    for exposure in world_state.exposures:
        log_count = view_decision_logs_by_exposure.get(exposure.exposure_id, 0)
        if log_count == 0:
            _add_issue(
                issues,
                code="missing_view_propensity_log",
                message="every exposure must have one view_decision propensity log",
                context={"exposure_id": exposure.exposure_id},
                validator="propensity",
            )
        elif log_count > 1:
            _add_issue(
                issues,
                code="duplicate_view_propensity_log",
                message="view_decision propensity log should be unique per exposure",
                context={"exposure_id": exposure.exposure_id, "count": log_count},
                validator="propensity",
            )

    for interaction in interactions:
        if interaction.event_type != "view":
            continue
        for stage in ("like_decision", "save_decision", "comment_decision", "hide_after_view_decision"):
            if post_view_logs_by_exposure_stage.get((interaction.exposure_id, stage), 0) == 0:
                _add_issue(
                    issues,
                    code="missing_post_view_propensity_log",
                    message="every viewed exposure must log all post-view decision stages",
                    context={"exposure_id": interaction.exposure_id, "decision_stage": stage},
                    validator="propensity",
                )

    for session_id in sessions_with_view:
        for stage in _OUTCOME_STAGES:
            if outcome_logs_by_session_stage.get((session_id, stage), 0) == 0:
                _add_issue(
                    issues,
                    code="missing_outcome_propensity_log",
                    message="session with views must include outcome-decision propensity logs",
                    context={"session_id": session_id, "decision_stage": stage},
                    validator="propensity",
                )

    return issues


def summarize_propensity_completeness(world_state: WorldState) -> dict[str, Any]:
    """Summarize propensity logging coverage for reporting."""
    expected_view_logs = len(world_state.exposures)
    observed_view_logs = sum(1 for log in world_state.propensity_logs if log.decision_stage == "view_decision")
    expected_post_view = 4 * sum(1 for item in world_state.interactions if item.event_type == "view")
    observed_post_view = sum(
        1
        for log in world_state.propensity_logs
        if log.decision_stage in {"like_decision", "save_decision", "comment_decision", "hide_after_view_decision"}
    )
    sessions_with_view = {item.session_id for item in world_state.interactions if item.event_type == "view"}
    expected_outcome = 4 * len(sessions_with_view)
    observed_outcome = sum(1 for log in world_state.propensity_logs if log.decision_stage in _OUTCOME_STAGES)

    expected_total = expected_view_logs + expected_post_view + expected_outcome
    observed_total = observed_view_logs + observed_post_view + observed_outcome
    completeness = 1.0 if expected_total == 0 else clip_0_1(observed_total / float(expected_total))
    return {
        "expected_total_logs": expected_total,
        "observed_total_logs": observed_total,
        "completeness_rate": round(completeness, 6),
        "expected_view_logs": expected_view_logs,
        "observed_view_logs": observed_view_logs,
        "expected_post_view_logs": expected_post_view,
        "observed_post_view_logs": observed_post_view,
        "expected_outcome_logs": expected_outcome,
        "observed_outcome_logs": observed_outcome,
    }


def _validate_propensity_fields(issues: list[ValidationIssue], log: Any) -> None:
    """Validate required propensity-log fields exist for stochastic decisions."""
    required_fields = (
        "deterministic_prob",
        "final_prob",
        "prob_jitter",
        "sampling_policy",
        "sampling_policy_version",
        "sampled_outcome",
    )
    for field_name in required_fields:
        if getattr(log, field_name) is None:
            _add_issue(
                issues,
                code="missing_propensity_field",
                message=f"propensity log is missing required field '{field_name}'",
                context={"log_id": log.log_id, "decision_stage": log.decision_stage, "field": field_name},
                validator="propensity",
            )


def _validate_propensity_formula(issues: list[ValidationIssue], log: Any) -> None:
    """Validate `final_prob` equals the probability used for sampling."""
    deterministic = float(log.deterministic_prob or 0.0)
    final = float(log.final_prob or 0.0)
    jitter = float(log.prob_jitter or 0.0)
    if log.decision_stage == "view_decision":
        floor = float((log.metadata or {}).get("off_interest_click_floor", 0.0))
        expected = clip_0_1(max(deterministic, floor) + jitter)
    else:
        expected = clip_0_1(deterministic + jitter)

    if abs(final - expected) > 2e-6:
        _add_issue(
            issues,
            code="propensity_probability_mismatch",
            message="final_prob does not match deterministic probability expression",
            context={
                "log_id": log.log_id,
                "decision_stage": log.decision_stage,
                "expected_final_prob": round(expected, 6),
                "actual_final_prob": final,
            },
            validator="propensity",
        )


def _validate_propensity_outcome_match(
    *,
    issues: list[ValidationIssue],
    log: Any,
    interactions_by_key: dict[tuple[str, str, str, str], int],
    viewed_exposures: set[str],
    focus_keys: set[tuple[str, str, str]],
    world_state: WorldState,
) -> None:
    """Validate propensity sampled outcome matches realized world-state outcome."""
    if log.sampled_outcome is None:
        return

    if log.decision_stage in _INTERACTION_STAGE_TO_EVENT:
        event_type = _INTERACTION_STAGE_TO_EVENT[log.decision_stage]
        observed = False
        if log.exposure_id and log.post_id:
            observed = interactions_by_key.get((log.session_id, log.exposure_id, log.post_id, event_type), 0) > 0
            if log.decision_stage == "hide_after_view_decision":
                observed = observed and log.exposure_id in viewed_exposures
        if bool(log.sampled_outcome) != observed:
            _add_issue(
                issues,
                code="propensity_outcome_mismatch",
                message="propensity sampled_outcome does not match realized interaction outcome",
                context={
                    "log_id": log.log_id,
                    "decision_stage": log.decision_stage,
                    "sampled_outcome": bool(log.sampled_outcome),
                    "observed_outcome": observed,
                },
                validator="propensity",
            )
        return

    if log.decision_stage == "focus_decision":
        observed = (
            log.post_id is not None
            and log.goal_id is not None
            and (log.session_id, log.post_id, log.goal_id) in focus_keys
        )
        if bool(log.sampled_outcome) != observed:
            _add_issue(
                issues,
                code="propensity_outcome_mismatch",
                message="focus propensity sampled_outcome does not match realized focus session",
                context={
                    "log_id": log.log_id,
                    "decision_stage": log.decision_stage,
                    "sampled_outcome": bool(log.sampled_outcome),
                    "observed_outcome": observed,
                },
                validator="propensity",
            )
        return

    if log.decision_stage == "follow_decision" and bool(log.sampled_outcome):
        target_author_id = (log.metadata or {}).get("target_author_id")
        observed = (
            target_author_id is not None
            and target_author_id in world_state.follow_graph.get(log.user_id, set())
        )
        if not observed:
            _add_issue(
                issues,
                code="propensity_outcome_mismatch",
                message="follow propensity sampled_outcome=true but follow edge not found",
                context={
                    "log_id": log.log_id,
                    "decision_stage": log.decision_stage,
                    "target_author_id": target_author_id,
                },
                validator="propensity",
            )


def _add_issue(
    issues: list[ValidationIssue],
    *,
    code: str,
    message: str,
    context: dict[str, Any],
    validator: str,
) -> None:
    """Append one hard-fail causality/propensity issue."""
    issues.append(
        {
            "validator": validator,
            "severity": "error",
            "code": code,
            "message": message,
            "context": context,
        }
    )
