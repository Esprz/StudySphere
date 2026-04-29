"""Top-level simulator run pipeline with optional Phase 8/9 text artifacts."""

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
from pipeline.render_text import prepare_openai_seed_batches, prepare_scale_text_batches
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
        text_artifacts = prepare_openai_seed_batches(
            world_state,
            output_dir=root,
            seed_model_name=config.seed_model_name,
            post_target_count=config.seed_post_target_count,
            comment_target_count=config.seed_comment_target_count,
            max_comments_per_post_request=config.seed_max_comments_per_post_request,
            rendered_posts_path=config.seed_rendered_posts_path,
        )
    scale_text_artifacts = None
    if config.render_scale_text:
        scale_text_artifacts = prepare_scale_text_batches(
            world_state,
            output_dir=root,
            openai_model_name=config.scale_openai_model_name,
            gemini_model_name=config.scale_gemini_model_name,
            gemini_share_percentage=config.scale_gemini_share_percentage,
            post_target_count=config.scale_post_target_count,
            comment_target_count=config.scale_comment_target_count,
            max_comments_per_post_request=config.scale_max_comments_per_post_request,
            rendered_posts_path=config.scale_rendered_posts_path,
        )

    summary = _build_run_summary(
        config=config,
        output_dir=root,
        entity_files=entity_files,
        analytics_files=analytics_files,
        validation_report=validation_report,
        validation_report_path=validation_report_path,
        text_artifacts=text_artifacts,
        scale_text_artifacts=scale_text_artifacts,
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
    scale_text_artifacts: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build one compact run summary payload for output bundle introspection."""
    return {
        "status": _merge_run_status(
            validation_status=validation_report.get("status", "unknown"),
            seed_text_status=None if text_artifacts is None else text_artifacts.get("status"),
            scale_text_status=None if scale_text_artifacts is None else scale_text_artifacts.get("status"),
        ),
        "output_dir": str(output_dir),
        "run_config": asdict(config),
        "record_counts": validation_report.get("total_records_by_type", {}),
        "validation": {
            "total_hard_fails": validation_report.get("total_hard_fails", 0),
            "total_soft_fails": validation_report.get("total_soft_fails", 0),
            "hard_fail_count_by_validator": validation_report.get("hard_fail_count_by_validator", {}),
            "soft_fail_count_by_validator": validation_report.get("soft_fail_count_by_validator", {}),
        },
        "seed_text_batch": None
        if text_artifacts is None
        else {
            "status": text_artifacts.get("status"),
            "prepared_post_request_count": len(text_artifacts.get("post_requests", [])),
            "prepared_comment_request_count": len(text_artifacts.get("comment_requests", [])),
            "files": text_artifacts.get("files", {}),
        },
        "scale_text_batch": None
        if scale_text_artifacts is None
        else {
            "status": scale_text_artifacts.get("status"),
            "comment_stage_status": scale_text_artifacts.get("comment_stage_status"),
            "prepared_post_request_count": sum(scale_text_artifacts.get("post_request_counts", {}).values()),
            "prepared_comment_request_count": sum(scale_text_artifacts.get("comment_request_counts", {}).values()),
            "post_request_counts_by_provider": scale_text_artifacts.get("post_request_counts", {}),
            "comment_request_counts_by_provider": scale_text_artifacts.get("comment_request_counts", {}),
            "files": scale_text_artifacts.get("files", {}),
            "missing_rendered_post_ids": scale_text_artifacts.get("missing_rendered_post_ids", []),
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
        default=Path(__file__).resolve().parents[2] / "default_source_bundle",
        help="Path to runtime source bundle root",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for exported artifacts")
    parser.add_argument(
        "--render-text",
        action="store_true",
        help="Prepare OpenAI Batch artifacts for seed post/comment text",
    )
    parser.add_argument(
        "--seed-model-name",
        type=str,
        default="gpt-5.4-nano",
        help="OpenAI core model used for seed post/comment batches",
    )
    parser.add_argument(
        "--seed-post-target-count",
        type=int,
        default=12,
        help="Number of seed posts to render into text during prepare",
    )
    parser.add_argument(
        "--seed-comment-target-count",
        type=int,
        default=12,
        help="Number of seed comment-set requests to prepare",
    )
    parser.add_argument(
        "--seed-max-comments-per-post-request",
        type=int,
        default=4,
        help="Maximum comments packed into one seed comment-set request",
    )
    parser.add_argument(
        "--seed-rendered-posts-path",
        type=str,
        default=None,
        help="Collected rendered-post sidecars used to unlock seed comment-set batch preparation",
    )
    parser.add_argument(
        "--render-scale-text",
        action="store_true",
        help="Prepare scale-stage OpenAI/Gemini Batch artifacts",
    )
    parser.add_argument(
        "--scale-openai-model-name",
        type=str,
        default="gpt-5-nano",
        help="OpenAI model used for the OpenAI share of scale batches",
    )
    parser.add_argument(
        "--scale-gemini-model-name",
        type=str,
        default="gemini-2.5-flash-lite",
        help="Gemini model used for the Gemini share of scale batches",
    )
    parser.add_argument(
        "--scale-gemini-share-percentage",
        type=int,
        default=0,
        help="Percentage of scale prompts routed to Gemini; remaining prompts go to OpenAI",
    )
    parser.add_argument(
        "--scale-post-target-count",
        type=int,
        default=None,
        help="Optional number of scale posts to prepare; default prepares all eligible posts",
    )
    parser.add_argument(
        "--scale-comment-target-count",
        type=int,
        default=None,
        help="Optional number of scale comment-set requests to prepare; default prepares all eligible groups",
    )
    parser.add_argument(
        "--scale-max-comments-per-post-request",
        type=int,
        default=6,
        help="Maximum comments packed into one scale comment-set request",
    )
    parser.add_argument(
        "--scale-rendered-posts-path",
        type=str,
        default=None,
        help="Collected rendered-post sidecars used to unlock comment-set batch preparation",
    )
    parser.add_argument(
        "--render-scale-text-strict",
        action="store_true",
        help="Reserved flag; kept for config compatibility while scale is batch-only",
    )
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="Optional ISO timestamp override, e.g. 2026-04-22T16:00:00+00:00",
    )
    return parser.parse_args()


def _merge_run_status(
    *,
    validation_status: str,
    seed_text_status: str | None,
    scale_text_status: str | None,
) -> str:
    """Promote any failed text-render stage into the top-level run status."""
    statuses = [validation_status]
    if seed_text_status is not None:
        statuses.append(seed_text_status)
    if scale_text_status is not None:
        statuses.append(scale_text_status)
    if "failed" in statuses:
        return "failed"
    if "passed_with_warnings" in statuses or "prepared_with_warnings" in statuses:
        return "passed_with_warnings"
    return validation_status


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
        seed_model_name=args.seed_model_name,
        seed_post_target_count=args.seed_post_target_count,
        seed_comment_target_count=args.seed_comment_target_count,
        seed_max_comments_per_post_request=args.seed_max_comments_per_post_request,
        seed_rendered_posts_path=args.seed_rendered_posts_path,
        render_scale_text=args.render_scale_text,
        render_scale_text_strict=args.render_scale_text_strict,
        scale_openai_model_name=args.scale_openai_model_name,
        scale_gemini_model_name=args.scale_gemini_model_name,
        scale_gemini_share_percentage=args.scale_gemini_share_percentage,
        scale_post_target_count=args.scale_post_target_count,
        scale_comment_target_count=args.scale_comment_target_count,
        scale_max_comments_per_post_request=args.scale_max_comments_per_post_request,
        scale_rendered_posts_path=args.scale_rendered_posts_path,
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
