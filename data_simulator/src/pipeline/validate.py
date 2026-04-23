"""Validation pipeline orchestration for structured simulator truth."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.models import SourceBundle, WorldState
from validators.causality import (
    summarize_propensity_completeness,
    validate_causality,
    validate_propensity_logging,
)
from validators.dependencies import validate_signal_dependencies
from validators.distributions import summarize_batch_metrics, validate_batch_distributions
from validators.schema import validate_schema

ValidationIssue = dict[str, Any]


def validate_world_state(world_state: WorldState, sources: SourceBundle) -> dict[str, Any]:
    """Run all Phase-6 validators and return a normalized batch report."""
    issues_by_validator = {
        "schema": validate_schema(world_state),
        "dependencies": validate_signal_dependencies(world_state, sources),
        "causality": validate_causality(world_state),
        "propensity": validate_propensity_logging(world_state),
        "distributions": validate_batch_distributions(world_state),
    }
    all_issues = [issue for issues in issues_by_validator.values() for issue in issues]
    hard_counts, soft_counts = _count_issues_by_validator(all_issues)

    batch_metrics = summarize_batch_metrics(world_state)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": _status_from_counts(hard_counts, soft_counts),
        "total_records_by_type": batch_metrics["totals"],
        "hard_fail_count_by_validator": hard_counts,
        "soft_fail_count_by_validator": soft_counts,
        "total_hard_fails": sum(hard_counts.values()),
        "total_soft_fails": sum(soft_counts.values()),
        "topic_distribution_summary": batch_metrics["topic_distribution"],
        "interaction_funnel_summary": batch_metrics["interaction_funnel"],
        "propensity_logging_completeness": summarize_propensity_completeness(world_state),
        "text_contradiction_rate": None,
        "repair_rate": 0.0,
        "issues": all_issues,
    }
    return report


def write_validation_report(report: dict[str, Any], output_path: str | Path) -> Path:
    """Persist one validation report as pretty JSON."""
    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return target


def validate_and_write(
    world_state: WorldState,
    sources: SourceBundle,
    output_path: str | Path,
) -> dict[str, Any]:
    """Run validators and write `validation_report.json` to disk."""
    report = validate_world_state(world_state, sources)
    write_validation_report(report, output_path)
    return report


def _count_issues_by_validator(issues: list[ValidationIssue]) -> tuple[dict[str, int], dict[str, int]]:
    """Return per-validator hard-fail and soft-fail counts."""
    hard: dict[str, int] = {}
    soft: dict[str, int] = {}
    for issue in issues:
        validator = str(issue.get("validator", "unknown"))
        severity = str(issue.get("severity", "error"))
        if severity == "warning":
            soft[validator] = soft.get(validator, 0) + 1
        else:
            hard[validator] = hard.get(validator, 0) + 1
    return hard, soft


def _status_from_counts(hard_counts: dict[str, int], soft_counts: dict[str, int]) -> str:
    """Convert fail counts into a single report status field."""
    if sum(hard_counts.values()) > 0:
        return "failed"
    if sum(soft_counts.values()) > 0:
        return "passed_with_warnings"
    return "passed"
