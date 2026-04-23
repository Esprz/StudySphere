"""Top-level simulator run pipeline with optional Phase 8 seed-text artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from config.loader import load_sources
from config.models import RunConfig
from exporters.analytics_logs import export_analytics_logs
from exporters.simulator_json import export_simulator_jsonl
from pipeline.build_truth import build_truth
from pipeline.render_text import render_seed_text
from pipeline.validate import validate_world_state, write_validation_report


def run_simulation(
    *,
    config: RunConfig,
    design_root: str | Path,
    output_dir: str | Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run build/validate/export pipeline and write a complete output directory."""
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    sources = load_sources(design_root)
    world_state = build_truth(config, sources, now=now)

    entity_files = export_simulator_jsonl(world_state, root)
    analytics_files = export_analytics_logs(world_state, root)

    validation_report = validate_world_state(world_state, sources)
    validation_report_path = write_validation_report(validation_report, root / "validation_report.json")
    text_artifacts = None
    if config.render_text:
        text_artifacts = render_seed_text(
            world_state,
            output_dir=root,
            seed_model_name="gpt-5.4-nano",
        )

    summary = _build_run_summary(
        config=config,
        output_dir=root,
        entity_files=entity_files,
        analytics_files=analytics_files,
        validation_report=validation_report,
        validation_report_path=validation_report_path,
        text_artifacts=text_artifacts,
    )
    summary_path = root / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary["files"]["run_summary"] = str(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _build_run_summary(
    *,
    config: RunConfig,
    output_dir: Path,
    entity_files: dict[str, Path],
    analytics_files: dict[str, Path],
    validation_report: dict[str, Any],
    validation_report_path: Path,
    text_artifacts: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build one compact run summary payload for output bundle introspection."""
    return {
        "status": validation_report.get("status", "unknown"),
        "output_dir": str(output_dir),
        "run_config": asdict(config),
        "record_counts": validation_report.get("total_records_by_type", {}),
        "validation": {
            "total_hard_fails": validation_report.get("total_hard_fails", 0),
            "total_soft_fails": validation_report.get("total_soft_fails", 0),
            "hard_fail_count_by_validator": validation_report.get("hard_fail_count_by_validator", {}),
            "soft_fail_count_by_validator": validation_report.get("soft_fail_count_by_validator", {}),
        },
        "text_render": None
        if text_artifacts is None
        else {
            "status": text_artifacts.get("status"),
            "rendered_post_count": len(text_artifacts.get("rendered_posts", [])),
            "rendered_comment_count": len(text_artifacts.get("rendered_comments", [])),
            "files": text_artifacts.get("files", {}),
        },
        "files": {
            "entities": {name: str(path) for name, path in entity_files.items()},
            "analytics": {name: str(path) for name, path in analytics_files.items()},
            "validation_report": str(validation_report_path),
            "run_summary": None,
        },
    }


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for one simulator run."""
    parser = argparse.ArgumentParser(description="StudySphere data simulator run pipeline")
    parser.add_argument("--seed", type=int, required=True, help="Deterministic RNG seed")
    parser.add_argument("--user-count", type=int, default=100, help="Number of users to generate")
    parser.add_argument("--timeline-ticks", type=int, default=30, help="Number of simulation ticks")
    parser.add_argument("--items-per-session", type=int, default=12, help="Number of exposures per session")
    parser.add_argument(
        "--max-candidate-pool-size",
        type=int,
        default=80,
        help="Max candidate pool size before ranking",
    )
    parser.add_argument(
        "--design-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "design" / "design_final",
        help="Path to design_final root",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for exported artifacts")
    parser.add_argument(
        "--render-text",
        action="store_true",
        help="Render seed text sidecars and OpenAI Batch input artifacts",
    )
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="Optional ISO timestamp override, e.g. 2026-04-22T16:00:00+00:00",
    )
    return parser.parse_args()


def main() -> None:
    """Execute one pipeline run from CLI args and print compact summary JSON."""
    args = _parse_args()
    now = datetime.fromisoformat(args.now) if args.now else None

    config = RunConfig(
        seed=args.seed,
        user_count=args.user_count,
        timeline_ticks=args.timeline_ticks,
        items_per_session=args.items_per_session,
        max_candidate_pool_size=args.max_candidate_pool_size,
        render_text=args.render_text,
    )
    summary = run_simulation(
        config=config,
        design_root=args.design_root,
        output_dir=args.output_dir,
        now=now,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
