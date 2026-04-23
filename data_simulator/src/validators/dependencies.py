"""Signal dependency validation for generated simulator batches."""

from __future__ import annotations

from typing import Any

from config.models import SourceBundle, WorldState

ValidationIssue = dict[str, Any]

_FORMULA_STAGE_STEPS: dict[str, int] = {
    "score_exposure": 8,
    "compute_view_probability": 10,
    "sample_like_probability": 10,
    "sample_save_probability": 10,
    "sample_comment_probability": 10,
    "sample_focus_trigger": 10,
}
_ALLOW_UNCATALOGED_FORMULA_TERMS = {
    "rank_position",
    "post_difficulty",
    "saved_in_session",
    "liked_in_session",
}


def validate_signal_dependencies(
    world_state: WorldState,
    sources: SourceBundle,
) -> list[ValidationIssue]:
    """Validate signal-catalog integrity and runtime dependency ordering."""
    issues: list[ValidationIssue] = []
    signal_steps = _load_signal_steps(sources)

    _validate_formula_dependencies(issues, sources, signal_steps)
    _validate_jitter_dependencies(issues, sources, signal_steps)
    _validate_runtime_dependencies(issues, world_state)
    return issues


def _validate_formula_dependencies(
    issues: list[ValidationIssue],
    sources: SourceBundle,
    signal_steps: dict[str, int | None],
) -> None:
    """Validate decision formula inputs are defined and generated before use."""
    functions = sources.require("decision_formulas").get("functions", [])
    for function in functions:
        function_name = str(function.get("name", ""))
        use_step = _FORMULA_STAGE_STEPS.get(function_name)

        used_signals = [str(item) for item in function.get("inputs", [])]

        for signal_name in used_signals:
            _validate_signal_step(
                issues=issues,
                signal_steps=signal_steps,
                signal_name=signal_name,
                use_step=use_step,
                context={"function": function_name, "signal": signal_name},
            )


def _validate_jitter_dependencies(
    issues: list[ValidationIssue],
    sources: SourceBundle,
    signal_steps: dict[str, int | None],
) -> None:
    """Validate jitter-driven signals are cataloged and available at the right stage."""
    rules = sources.require("jitter_noise_rules").get("rules", {})
    required_rules = {
        "candidate_score_jitter": ("small_jitter", 8),
        "view_probability_jitter": ("small_jitter", 10),
        "post_action_probability_jitter": ("action_prob_jitter", 10),
        "off_interest_click_floor": ("off_interest_click_floor", 10),
    }
    for rule_name, (signal_name, use_step) in required_rules.items():
        if rule_name not in rules:
            _add_issue(
                issues,
                code="missing_jitter_rule",
                message=f"required jitter rule '{rule_name}' is missing",
                context={"rule": rule_name},
            )
            continue
        _validate_signal_step(
            issues=issues,
            signal_steps=signal_steps,
            signal_name=signal_name,
            use_step=use_step,
            context={"rule": rule_name, "signal": signal_name},
        )


def _validate_runtime_dependencies(
    issues: list[ValidationIssue],
    world_state: WorldState,
) -> None:
    """Validate runtime entities only reference already-generated parent entities/signals."""
    user_ids = {user.user_id for user in world_state.users}
    session_ids = {session.session_id for session in world_state.sessions}
    post_ids = {post.post_id for post in world_state.posts}
    goal_ids = {goal.goal_id for goals in world_state.goals_by_user.values() for goal in goals}

    exposures_by_id = {exposure.exposure_id: exposure for exposure in world_state.exposures}
    required_score_signals = {
        "topic_match",
        "goal_alignment",
        "activity_alignment",
        "freshness_bonus",
        "observed_quality",
        "social_bonus",
        "exploration_bonus",
    }

    for exposure in world_state.exposures:
        if exposure.user_id not in user_ids:
            _add_issue(
                issues,
                code="missing_dependency_reference",
                message="exposure.user_id is not present in users",
                context={"entity": "exposure", "id": exposure.exposure_id, "field": "user_id"},
            )
        if exposure.session_id not in session_ids:
            _add_issue(
                issues,
                code="missing_dependency_reference",
                message="exposure.session_id is not present in sessions",
                context={"entity": "exposure", "id": exposure.exposure_id, "field": "session_id"},
            )
        if exposure.post_id not in post_ids:
            _add_issue(
                issues,
                code="missing_dependency_reference",
                message="exposure.post_id is not present in posts",
                context={"entity": "exposure", "id": exposure.exposure_id, "field": "post_id"},
            )
        if exposure.deterministic_exposure_score is None:
            _add_issue(
                issues,
                code="missing_exposure_score_signal",
                message="deterministic_exposure_score must exist before exposure emission",
                context={"exposure_id": exposure.exposure_id},
            )
        breakdown = exposure.score_breakdown or {}
        for signal_name in required_score_signals:
            if signal_name not in breakdown:
                _add_issue(
                    issues,
                    code="missing_exposure_score_signal",
                    message=f"score_breakdown missing '{signal_name}'",
                    context={"exposure_id": exposure.exposure_id, "signal": signal_name},
                )

    for interaction in world_state.interactions:
        exposure = exposures_by_id.get(interaction.exposure_id)
        if exposure is None:
            _add_issue(
                issues,
                code="missing_dependency_reference",
                message="interaction.exposure_id is not present in exposures",
                context={"entity": "interaction", "id": interaction.interaction_id, "field": "exposure_id"},
            )
            continue
        if interaction.user_id != exposure.user_id:
            _add_issue(
                issues,
                code="cross_entity_dependency_mismatch",
                message="interaction.user_id does not match parent exposure.user_id",
                context={"interaction_id": interaction.interaction_id, "exposure_id": exposure.exposure_id},
            )
        if interaction.post_id != exposure.post_id:
            _add_issue(
                issues,
                code="cross_entity_dependency_mismatch",
                message="interaction.post_id does not match parent exposure.post_id",
                context={"interaction_id": interaction.interaction_id, "exposure_id": exposure.exposure_id},
            )
        if interaction.session_id != exposure.session_id:
            _add_issue(
                issues,
                code="cross_entity_dependency_mismatch",
                message="interaction.session_id does not match parent exposure.session_id",
                context={"interaction_id": interaction.interaction_id, "exposure_id": exposure.exposure_id},
            )

        if interaction.event_type in {"view", "scroll_past", "hide", "like", "save", "comment"}:
            if interaction.deterministic_prob is None or interaction.final_prob is None:
                _add_issue(
                    issues,
                    code="missing_probability_signal",
                    message="stochastic interaction is missing deterministic/final probability signal",
                    context={"interaction_id": interaction.interaction_id, "event_type": interaction.event_type},
                )

    for focus in world_state.focus_sessions:
        if focus.user_id not in user_ids:
            _add_issue(
                issues,
                code="missing_dependency_reference",
                message="focus_session.user_id is not present in users",
                context={"entity": "focus_session", "id": focus.focus_id, "field": "user_id"},
            )
        if focus.session_id not in session_ids:
            _add_issue(
                issues,
                code="missing_dependency_reference",
                message="focus_session.session_id is not present in sessions",
                context={"entity": "focus_session", "id": focus.focus_id, "field": "session_id"},
            )
        if focus.trigger_post_id not in post_ids:
            _add_issue(
                issues,
                code="missing_dependency_reference",
                message="focus_session.trigger_post_id is not present in posts",
                context={"entity": "focus_session", "id": focus.focus_id, "field": "trigger_post_id"},
            )
        if focus.related_goal_id not in goal_ids:
            _add_issue(
                issues,
                code="missing_dependency_reference",
                message="focus_session.related_goal_id is not present in goals",
                context={"entity": "focus_session", "id": focus.focus_id, "field": "related_goal_id"},
            )


def _load_signal_steps(sources: SourceBundle) -> dict[str, int | None]:
    """Build a lookup from signal name to generation step from signal catalog."""
    lookup: dict[str, int | None] = {}
    for signal in sources.require("signal_catalog").get("signals", []):
        name = signal.get("name")
        if not name:
            continue
        lookup[str(name)] = _parse_step(signal.get("generated_in_step"))
    return lookup


def _parse_step(value: object) -> int | None:
    """Parse generated step metadata into an integer when possible."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _validate_signal_step(
    *,
    issues: list[ValidationIssue],
    signal_steps: dict[str, int | None],
    signal_name: str,
    use_step: int | None,
    context: dict[str, Any],
) -> None:
    """Validate that a signal exists and is generated no later than the use step."""
    generated_step = signal_steps.get(signal_name)
    if signal_name not in signal_steps:
        if signal_name in _ALLOW_UNCATALOGED_FORMULA_TERMS:
            return
        _add_issue(
            issues,
            code="undefined_signal_in_catalog",
            message=f"signal '{signal_name}' is used but not defined in signal catalog",
            context=context,
        )
        return
    if use_step is None or generated_step is None:
        return
    if generated_step > use_step:
        _add_issue(
            issues,
            code="future_step_signal_usage",
            message=f"signal '{signal_name}' generated in step {generated_step} but used in step {use_step}",
            context={**context, "generated_step": generated_step, "used_in_step": use_step},
        )


def _add_issue(
    issues: list[ValidationIssue],
    *,
    code: str,
    message: str,
    context: dict[str, Any],
) -> None:
    """Append one hard-fail dependency validation issue."""
    issues.append(
        {
            "validator": "dependencies",
            "severity": "error",
            "code": code,
            "message": message,
            "context": context,
        }
    )
