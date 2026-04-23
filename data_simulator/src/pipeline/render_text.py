"""Phase-8/9 text rendering pipelines and batch-artifact helpers."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from config.models import (
    CommentRenderTarget,
    CommentSetRenderPrompt,
    InteractionRecord,
    PostRecord,
    PostRenderPrompt,
    RenderedCommentText,
    RenderedPostText,
    UserProfile,
    WorldState,
)
from exporters.simulator_json import _to_jsonable
from renderers.prompts import (
    build_comment_render_prompt,
    build_comment_render_target,
    build_post_render_prompt,
)
from renderers.text_render import (
    GeminiBatchBuilder,
    OpenAISeedBatchBuilder,
    StubSeedTextRenderer,
)
from validators.text_llm import validate_text_with_llm
from validators.text_rules import validate_rendered_comments, validate_rendered_posts, validate_rendered_text_bundle


def render_seed_text(
    world_state: WorldState,
    *,
    output_dir: str | Path | None = None,
    sync_renderer: StubSeedTextRenderer | None = None,
    llm_validator=None,
    seed_model_name: str = "gpt-5.4-nano",
    post_target_count: int = 12,
    comment_target_count: int = 12,
    max_comments_per_post_request: int = 4,
) -> dict[str, Any]:
    """Render a small seed-text subset locally for tests and offline validation."""
    users_by_id = {user.user_id: user for user in world_state.users}
    posts_by_id = {post.post_id: post for post in world_state.posts}
    prepared = prepare_openai_seed_batches(
        world_state,
        output_dir=output_dir,
        seed_model_name=seed_model_name,
        post_target_count=post_target_count,
        comment_target_count=comment_target_count,
        max_comments_per_post_request=max_comments_per_post_request,
    )
    renderer = sync_renderer or StubSeedTextRenderer()

    rendered_posts = renderer.render_posts(prepared["post_prompts"])
    rendered_posts_by_post_id = {record.post_id: record for record in rendered_posts}
    comment_target_groups = select_seed_comment_target_groups(
        world_state,
        limit=comment_target_count,
        max_comments_per_post_request=max_comments_per_post_request,
    )
    comment_prompts = [
        build_comment_render_prompt(
            post,
            rendered_post=rendered_posts_by_post_id.get(post.post_id),
            comment_targets=[
                build_comment_render_target(interaction, users_by_id.get(interaction.user_id))
                for interaction in interactions
            ],
        )
        for post, interactions in comment_target_groups
        if post.post_id in rendered_posts_by_post_id
    ]
    rendered_comments = renderer.render_comments(comment_prompts)

    interactions_by_id = {interaction.interaction_id: interaction for interaction in world_state.interactions}
    rule_issues = validate_rendered_text_bundle(
        rendered_posts=rendered_posts,
        rendered_comments=rendered_comments,
        posts_by_id=posts_by_id,
        interactions_by_id=interactions_by_id,
    )
    llm_issues = validate_text_with_llm(
        rendered_posts=rendered_posts,
        rendered_comments=rendered_comments,
        llm_validator=llm_validator,
        sample_size=None,
    )

    failed_post_ids = {
        issue["context"]["record_id"]
        for issue in rule_issues + llm_issues
        if issue["context"]["record_id"] in {record.post_id for record in rendered_posts}
    }
    failed_comment_ids = {
        issue["context"]["record_id"]
        for issue in rule_issues + llm_issues
        if issue["context"]["record_id"] in {record.interaction_id for record in rendered_comments}
    }

    passed_posts = [
        _mark_post_render_status(record, "passed")
        for record in rendered_posts
        if record.post_id not in failed_post_ids
    ]
    passed_comments = [
        _mark_comment_render_status(record, "passed")
        for record in rendered_comments
        if record.interaction_id not in failed_comment_ids
    ]

    artifacts: dict[str, Any] = {
        "rendered_posts": passed_posts,
        "rendered_comments": passed_comments,
        "post_prompts": prepared["post_prompts"],
        "comment_prompts": comment_prompts,
        "rule_issues": rule_issues,
        "llm_issues": llm_issues,
        "status": "passed" if not (rule_issues or llm_issues) else "failed",
        "files": dict(prepared.get("files", {})),
    }

    if output_dir is not None:
        files = write_render_seed_artifacts(
            output_dir=output_dir,
            rendered_posts=passed_posts,
            rendered_comments=passed_comments,
            issues=rule_issues + llm_issues,
        )
        artifacts["files"].update(files)
    return artifacts


def prepare_scale_text_batches(
    world_state: WorldState,
    *,
    output_dir: str | Path | None = None,
    openai_model_name: str = "gpt-5-nano",
    gemini_model_name: str = "gemini-2.5-flash-lite",
    gemini_share_percentage: int = 0,
    rendered_posts_path: str | Path | None = None,
    post_target_count: int | None = None,
    comment_target_count: int | None = None,
    max_comments_per_post_request: int = 6,
) -> dict[str, Any]:
    """Prepare scale-stage OpenAI/Gemini batch artifacts without local rendering.

    Phase 9 is now explicitly two-stage:
    1. Prepare post render requests.
    2. After post sidecars are collected, prepare comment-set requests using the
       concrete rendered post text rather than only structured metadata.
    """

    if not 0 <= gemini_share_percentage <= 100:
        raise ValueError("gemini_share_percentage must be between 0 and 100")

    users_by_id = {user.user_id: user for user in world_state.users}
    posts_by_id = {post.post_id: post for post in world_state.posts}
    openai_builder = OpenAISeedBatchBuilder(model_name=openai_model_name)
    gemini_builder = GeminiBatchBuilder(model_name=gemini_model_name)

    user_provider_assignments = _build_user_provider_assignments(
        world_state.users,
        gemini_share_percentage=gemini_share_percentage,
    )

    post_targets = select_seed_post_targets(world_state, limit=post_target_count)
    post_prompts_by_provider = {"openai": [], "gemini": []}
    for post in post_targets:
        provider = user_provider_assignments.get(post.author_id, "openai")
        post_prompts_by_provider[provider].append(
            build_post_render_prompt(post, author_profile=users_by_id.get(post.author_id))
        )
    post_prompts = post_prompts_by_provider["openai"] + post_prompts_by_provider["gemini"]

    artifacts: dict[str, Any] = {
        "status": "prepared_posts_only" if rendered_posts_path is None else "prepared",
        "post_prompts": post_prompts,
        "comment_prompts": [],
        "post_request_counts": {
            "openai": len(post_prompts_by_provider["openai"]),
            "gemini": len(post_prompts_by_provider["gemini"]),
        },
        "comment_request_counts": {
            "openai": 0,
            "gemini": 0,
        },
        "comment_stage_status": "blocked_missing_rendered_posts" if rendered_posts_path is None else "prepared",
        "missing_rendered_post_ids": [],
        "files": {},
    }

    if output_dir is not None:
        artifacts["files"].update(
            write_provider_batch_artifacts(
                output_dir=output_dir,
                stage_name="scale_posts",
                openai_builder=openai_builder,
                gemini_builder=gemini_builder,
                openai_prompts=post_prompts_by_provider["openai"],
                gemini_prompts=post_prompts_by_provider["gemini"],
                request_kind="posts",
            )
        )
        split_report = {
            "stage": "posts",
            "gemini_share_percentage": gemini_share_percentage,
            "openai_prompt_ids": [prompt.prompt_id for prompt in post_prompts_by_provider["openai"]],
            "gemini_prompt_ids": [prompt.prompt_id for prompt in post_prompts_by_provider["gemini"]],
            "provider_user_counts": _count_provider_assignments(user_provider_assignments),
        }
        artifacts["files"]["scale_posts_provider_split"] = str(
            _write_json(split_report, Path(output_dir).expanduser().resolve() / "scale_posts_provider_split.json")
        )

    if rendered_posts_path is None:
        return artifacts

    rendered_posts_by_post_id = _load_rendered_posts_sidecars(rendered_posts_path)
    comment_target_groups = select_scale_comment_target_groups_by_provider(
        world_state,
        user_provider_assignments=user_provider_assignments,
        limit=comment_target_count,
        max_comments_per_post_request=max_comments_per_post_request,
    )
    comment_prompts_by_provider = {"openai": [], "gemini": []}
    missing_rendered_post_ids: set[str] = set()
    for provider, post, interactions in comment_target_groups:
        rendered_post = rendered_posts_by_post_id.get(post.post_id)
        if rendered_post is None:
            missing_rendered_post_ids.add(post.post_id)
            continue
        comment_prompts_by_provider[provider].append(
            build_comment_render_prompt(
                post,
                rendered_post=rendered_post,
                comment_targets=[
                    build_comment_render_target(interaction, users_by_id.get(interaction.user_id))
                    for interaction in interactions
                ],
            )
        )
    comment_prompts = comment_prompts_by_provider["openai"] + comment_prompts_by_provider["gemini"]
    artifacts["comment_prompts"] = comment_prompts
    artifacts["comment_request_counts"] = {
        "openai": len(comment_prompts_by_provider["openai"]),
        "gemini": len(comment_prompts_by_provider["gemini"]),
    }
    artifacts["missing_rendered_post_ids"] = sorted(missing_rendered_post_ids)
    if missing_rendered_post_ids:
        artifacts["comment_stage_status"] = "partial_missing_rendered_posts"
        artifacts["status"] = "prepared_with_warnings"

    if output_dir is not None:
        artifacts["files"].update(
            write_provider_batch_artifacts(
                output_dir=output_dir,
                stage_name="scale_comment_sets",
                openai_builder=openai_builder,
                gemini_builder=gemini_builder,
                openai_prompts=comment_prompts_by_provider["openai"],
                gemini_prompts=comment_prompts_by_provider["gemini"],
                request_kind="comment_sets",
            )
        )
        split_report = {
            "stage": "comment_sets",
            "gemini_share_percentage": gemini_share_percentage,
            "openai_prompt_ids": [prompt.prompt_id for prompt in comment_prompts_by_provider["openai"]],
            "gemini_prompt_ids": [prompt.prompt_id for prompt in comment_prompts_by_provider["gemini"]],
            "missing_rendered_post_ids": sorted(missing_rendered_post_ids),
            "provider_user_counts": _count_provider_assignments(user_provider_assignments),
        }
        artifacts["files"]["scale_comment_sets_provider_split"] = str(
            _write_json(split_report, Path(output_dir).expanduser().resolve() / "scale_comment_sets_provider_split.json")
        )
    return artifacts


def collect_scale_batch_results(
    *,
    provider: str,
    batch_kind: str,
    manifest_path: str | Path,
    batch_status_path: str | Path,
    output_jsonl_path: str | Path | None = None,
    error_jsonl_path: str | Path | None = None,
) -> dict[str, Any]:
    """Collect one prepared scale batch from OpenAI or Gemini without polling."""
    manifest = json.loads(Path(manifest_path).expanduser().resolve().read_text(encoding="utf-8"))
    batch_status = json.loads(Path(batch_status_path).expanduser().resolve().read_text(encoding="utf-8"))
    report: dict[str, Any] = {
        "provider": provider,
        "batch_kind": batch_kind,
        "status": batch_status.get("status", batch_status.get("metadata", {}).get("state", "unknown")),
        "manifest_path": str(Path(manifest_path).expanduser().resolve()),
        "batch_status_path": str(Path(batch_status_path).expanduser().resolve()),
        "output_jsonl_path": None if output_jsonl_path is None else str(Path(output_jsonl_path).expanduser().resolve()),
        "error_jsonl_path": None if error_jsonl_path is None else str(Path(error_jsonl_path).expanduser().resolve()),
        "batch_id": batch_status.get("id", batch_status.get("name")),
        "rendered_posts": [],
        "rendered_comments": [],
        "failed_custom_ids": [],
        "files": {},
    }

    if output_jsonl_path is not None and _batch_job_completed(provider, batch_status):
        registry = _load_jsonl_registry(manifest["prompt_registry_path"])
        outputs = _parse_provider_outputs(
            provider=provider,
            output_jsonl_path=output_jsonl_path,
            model_name=str(manifest["model_name"]),
        )
        if batch_kind == "posts":
            report["rendered_posts"] = _parse_rendered_posts_from_outputs(
                outputs,
                registry,
                str(manifest["model_name"]),
                provider_name=str(manifest["provider"]),
            )
        elif batch_kind == "comment_sets":
            report["rendered_comments"] = _parse_rendered_comments_from_outputs(
                outputs,
                registry,
                str(manifest["model_name"]),
                provider_name=str(manifest["provider"]),
            )

    if error_jsonl_path is not None:
        report["failed_custom_ids"] = _collect_failed_custom_ids(error_jsonl_path, provider=provider)

    return report


def prepare_openai_seed_batches(
    world_state: WorldState,
    *,
    output_dir: str | Path | None = None,
    seed_model_name: str = "gpt-5.4-nano",
    rendered_posts_path: str | Path | None = None,
    post_target_count: int = 12,
    comment_target_count: int = 12,
    max_comments_per_post_request: int = 4,
) -> dict[str, Any]:
    """Prepare seed-stage OpenAI Batch artifacts in explicit post-then-comment stages."""
    users_by_id = {user.user_id: user for user in world_state.users}
    posts_by_id = {post.post_id: post for post in world_state.posts}
    post_targets = select_seed_post_targets(world_state, limit=post_target_count)
    post_prompts = [
        build_post_render_prompt(post, author_profile=users_by_id.get(post.author_id))
        for post in post_targets
    ]
    builder = OpenAISeedBatchBuilder(model_name=seed_model_name)
    post_requests = builder.build_post_requests(post_prompts)
    comment_prompts: list[CommentSetRenderPrompt] = []
    comment_requests: list[dict[str, Any]] = []
    missing_rendered_post_ids: set[str] = set()

    if rendered_posts_path is not None:
        rendered_posts_by_post_id = _load_rendered_posts_sidecars(rendered_posts_path)
        comment_target_groups = select_seed_comment_target_groups(
            world_state,
            limit=comment_target_count,
            max_comments_per_post_request=max_comments_per_post_request,
        )
        for post, interactions in comment_target_groups:
            rendered_post = rendered_posts_by_post_id.get(post.post_id)
            if rendered_post is None:
                missing_rendered_post_ids.add(post.post_id)
                continue
            comment_prompts.append(
                build_comment_render_prompt(
                    post,
                    rendered_post=rendered_post,
                    comment_targets=[
                        build_comment_render_target(interaction, users_by_id.get(interaction.user_id))
                        for interaction in interactions
                    ],
                )
            )
        comment_requests = builder.build_comment_set_requests(comment_prompts)

    artifacts: dict[str, Any] = {
        "post_prompts": post_prompts,
        "comment_prompts": comment_prompts,
        "post_requests": post_requests,
        "comment_requests": comment_requests,
        "comment_stage_status": "blocked_missing_rendered_posts" if rendered_posts_path is None else "prepared",
        "missing_rendered_post_ids": sorted(missing_rendered_post_ids),
        "status": "prepared_posts_only" if rendered_posts_path is None else "prepared",
        "files": {},
    }
    if missing_rendered_post_ids:
        artifacts["comment_stage_status"] = "partial_missing_rendered_posts"
        artifacts["status"] = "prepared_with_warnings"
    if output_dir is not None:
        artifacts["files"] = write_openai_batch_artifacts(
            output_dir=output_dir,
            builder=builder,
            post_prompts=post_prompts,
            comment_prompts=comment_prompts,
            post_requests=post_requests,
            comment_requests=comment_requests,
            posts_by_id=posts_by_id,
        )
    return artifacts


def collect_openai_seed_batch_results(
    *,
    batch_kind: str,
    manifest_path: str | Path,
    batch_status_path: str | Path,
    output_jsonl_path: str | Path | None = None,
    error_jsonl_path: str | Path | None = None,
) -> dict[str, Any]:
    """Collect one completed or in-progress batch without polling or auto-retry."""
    manifest = json.loads(Path(manifest_path).expanduser().resolve().read_text(encoding="utf-8"))
    batch_status = json.loads(Path(batch_status_path).expanduser().resolve().read_text(encoding="utf-8"))
    report: dict[str, Any] = {
        "batch_kind": batch_kind,
        "status": batch_status.get("status", "unknown"),
        "manifest_path": str(Path(manifest_path).expanduser().resolve()),
        "batch_status_path": str(Path(batch_status_path).expanduser().resolve()),
        "output_jsonl_path": None if output_jsonl_path is None else str(Path(output_jsonl_path).expanduser().resolve()),
        "error_jsonl_path": None if error_jsonl_path is None else str(Path(error_jsonl_path).expanduser().resolve()),
        "batch_id": batch_status.get("id"),
        "rendered_posts": [],
        "rendered_comments": [],
        "failed_custom_ids": [],
        "files": {},
    }

    if output_jsonl_path is not None and batch_status.get("status") == "completed":
        builder = OpenAISeedBatchBuilder(model_name=str(manifest.get("model_name", "gpt-5.4-nano")))
        parsed = builder.parse_batch_output(output_jsonl_path)
        if batch_kind == "posts":
            registry = _load_jsonl_registry(manifest["prompt_registry_path"])
            report["rendered_posts"] = _parse_rendered_posts_from_outputs(
                parsed,
                registry,
                builder.model_name,
                provider_name=str(manifest.get("provider", "openai_batch")),
            )
        elif batch_kind == "comment_sets":
            registry = _load_jsonl_registry(manifest["prompt_registry_path"])
            report["rendered_comments"] = _parse_rendered_comments_from_outputs(
                parsed,
                registry,
                builder.model_name,
                provider_name=str(manifest.get("provider", "openai_batch")),
            )

    if error_jsonl_path is not None:
        report["failed_custom_ids"] = _collect_failed_custom_ids(error_jsonl_path, provider="openai")

    return report


def prepare_batch_retry_artifacts(
    *,
    collect_report_path: str | Path,
    output_dir: str | Path,
) -> dict[str, str]:
    """Prepare a retry shard from a prior collect report, without auto-submitting it."""
    report = json.loads(Path(collect_report_path).expanduser().resolve().read_text(encoding="utf-8"))
    failed_custom_ids = list(report.get("failed_custom_ids", []))
    if not failed_custom_ids:
        raise ValueError("No failed_custom_ids available for retry preparation")

    manifest_path = Path(report["manifest_path"]).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    registry = _load_jsonl_registry(manifest["prompt_registry_path"])
    selected = [item for item in registry if str(item.get("prompt_id")) in set(failed_custom_ids)]
    if not selected:
        raise ValueError("Retry selection produced an empty shard")

    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    retry_registry_path = _write_jsonl_records(selected, root / f"{report['batch_kind']}_retry_prompt_registry.jsonl")
    retry_input_path = _write_jsonl_records(
        [item["batch_request"] for item in selected],
        root / f"{report['batch_kind']}_retry_batch_input.jsonl",
    )
    retry_manifest_payload = {
        "provider": manifest["provider"],
        "model_name": manifest["model_name"],
        "request_kind": manifest["request_kind"],
        "request_count": len(selected),
        "batch_input_path": str(retry_input_path),
        "prompt_registry_path": str(retry_registry_path),
        "source_collect_report_path": str(Path(collect_report_path).expanduser().resolve()),
        "notes": [
            "This retry batch was prepared from failed_custom_ids only.",
            "Submission is manual and separate from preparation.",
        ],
    }
    if "endpoint" in manifest:
        retry_manifest_payload["endpoint"] = manifest["endpoint"]
    if "completion_window" in manifest:
        retry_manifest_payload["completion_window"] = manifest["completion_window"]
    retry_manifest_path = _write_json(
        retry_manifest_payload,
        root / f"{report['batch_kind']}_retry_submit_manifest.json",
    )
    return {
        "retry_batch_input": str(retry_input_path),
        "retry_prompt_registry": str(retry_registry_path),
        "retry_submit_manifest": str(retry_manifest_path),
    }


def prepare_openai_seed_retry_batches(
    *,
    collect_report_path: str | Path,
    output_dir: str | Path,
) -> dict[str, str]:
    """Backward-compatible wrapper for seed retry preparation."""
    return prepare_batch_retry_artifacts(
        collect_report_path=collect_report_path,
        output_dir=output_dir,
    )


def _repair_or_discard_posts(
    *,
    rendered_posts: list[RenderedPostText],
    posts_by_id: dict[str, PostRecord],
    users_by_id: dict[str, UserProfile],
    llm_validator,
    llm_sample_size: int,
    max_repair_rounds: int,
) -> dict[str, Any]:
    """Validate post text, repair textual failures, then discard unresolved records."""
    current_records = list(rendered_posts)
    repaired_ids: set[str] = set()
    discarded_ids: set[str] = set()
    rule_issues_all: list[dict[str, Any]] = []
    llm_issues_all: list[dict[str, Any]] = []
    round_reports: list[dict[str, Any]] = []
    sampled_payload_count = 0
    failed_on_first_round: set[str] = set()

    for round_index in range(max(0, max_repair_rounds) + 1):
        rule_issues = validate_rendered_posts(current_records, posts_by_id)
        llm_issues = validate_text_with_llm(
            rendered_posts=current_records,
            rendered_comments=[],
            llm_validator=llm_validator,
            sample_size=llm_sample_size,
        )
        sampled_payload_count += _effective_llm_sample_count(len(current_records), llm_sample_size)
        rule_issues_all.extend(rule_issues)
        llm_issues_all.extend(llm_issues)
        failed_ids = _collect_failed_record_ids(rule_issues + llm_issues, {record.post_id for record in current_records})
        if round_index == 0:
            failed_on_first_round = set(failed_ids)

        round_reports.append(
            {
                "record_type": "post",
                "round_index": round_index,
                "candidate_count": len(current_records),
                "failed_count": len(failed_ids),
                "failed_record_ids": sorted(failed_ids),
            }
        )
        if not failed_ids:
            break
        if round_index >= max_repair_rounds:
            discarded_ids.update(failed_ids)
            current_records = [record for record in current_records if record.post_id not in failed_ids]
            break

        repaired_records: dict[str, RenderedPostText] = {}
        current_by_post_id = {record.post_id: record for record in current_records}
        for post_id in failed_ids:
            post = posts_by_id.get(post_id)
            record = current_by_post_id.get(post_id)
            if post is None or record is None:
                continue
            repaired_records[post_id] = _repair_post_render_text(
                record,
                post,
                author_profile=users_by_id.get(post.author_id),
            )
            repaired_ids.add(post_id)
        current_records = [repaired_records.get(record.post_id, record) for record in current_records]

    records = [
        _mark_post_render_status(
            record,
            "repaired" if record.post_id in repaired_ids else "passed",
        )
        for record in current_records
    ]
    return {
        "records": records,
        "repaired_ids": repaired_ids,
        "discarded_ids": discarded_ids,
        "failed_on_first_round_ids": failed_on_first_round,
        "rule_issues": rule_issues_all,
        "llm_issues": llm_issues_all,
        "round_reports": round_reports,
        "sampled_payload_count": sampled_payload_count,
    }


def _repair_or_discard_comments(
    *,
    rendered_comments: list[RenderedCommentText],
    posts_by_id: dict[str, PostRecord],
    interactions_by_id: dict[str, InteractionRecord],
    users_by_id: dict[str, UserProfile],
    llm_validator,
    llm_sample_size: int,
    max_repair_rounds: int,
) -> dict[str, Any]:
    """Validate comment text, repair textual failures, then discard unresolved records."""
    current_records = list(rendered_comments)
    repaired_ids: set[str] = set()
    discarded_ids: set[str] = set()
    rule_issues_all: list[dict[str, Any]] = []
    llm_issues_all: list[dict[str, Any]] = []
    round_reports: list[dict[str, Any]] = []
    sampled_payload_count = 0
    failed_on_first_round: set[str] = set()

    for round_index in range(max(0, max_repair_rounds) + 1):
        rule_issues = validate_rendered_comments(current_records, interactions_by_id, posts_by_id)
        llm_issues = validate_text_with_llm(
            rendered_posts=[],
            rendered_comments=current_records,
            llm_validator=llm_validator,
            sample_size=llm_sample_size,
        )
        sampled_payload_count += _effective_llm_sample_count(len(current_records), llm_sample_size)
        rule_issues_all.extend(rule_issues)
        llm_issues_all.extend(llm_issues)
        failed_ids = _collect_failed_record_ids(
            rule_issues + llm_issues,
            {record.interaction_id for record in current_records},
        )
        if round_index == 0:
            failed_on_first_round = set(failed_ids)

        round_reports.append(
            {
                "record_type": "comment",
                "round_index": round_index,
                "candidate_count": len(current_records),
                "failed_count": len(failed_ids),
                "failed_record_ids": sorted(failed_ids),
            }
        )
        if not failed_ids:
            break
        if round_index >= max_repair_rounds:
            discarded_ids.update(failed_ids)
            current_records = [record for record in current_records if record.interaction_id not in failed_ids]
            break

        repaired_records: dict[str, RenderedCommentText] = {}
        current_by_interaction_id = {record.interaction_id: record for record in current_records}
        for interaction_id in failed_ids:
            interaction = interactions_by_id.get(interaction_id)
            record = current_by_interaction_id.get(interaction_id)
            if interaction is None or record is None:
                continue
            post = posts_by_id.get(interaction.post_id)
            if post is None:
                continue
            repaired_records[interaction_id] = _repair_comment_render_text(
                record,
                interaction,
                post,
                commenter_profile=users_by_id.get(interaction.user_id),
            )
            repaired_ids.add(interaction_id)
        current_records = [repaired_records.get(record.interaction_id, record) for record in current_records]

    records = [
        _mark_comment_render_status(
            record,
            "repaired" if record.interaction_id in repaired_ids else "passed",
        )
        for record in current_records
    ]
    return {
        "records": records,
        "repaired_ids": repaired_ids,
        "discarded_ids": discarded_ids,
        "failed_on_first_round_ids": failed_on_first_round,
        "rule_issues": rule_issues_all,
        "llm_issues": llm_issues_all,
        "round_reports": round_reports,
        "sampled_payload_count": sampled_payload_count,
    }


def _repair_post_render_text(
    record: RenderedPostText,
    post: PostRecord,
    *,
    author_profile: UserProfile | None,
) -> RenderedPostText:
    """Create a persona-aware post rewrite while preserving structured-truth constraints."""
    difficulty_label = {
        1: "entry level",
        2: "intro level",
        3: "intermediate level",
        4: "advanced level",
        5: "expert level",
    }.get(post.difficulty, "intermediate level")
    repaired_title = f"{post.topic}: {post.post_style.replace('_', ' ')}"
    if post.format == "qa_post" and "?" not in repaired_title:
        repaired_title = f"{repaired_title}?"
    include_subtopic = True
    if post.difficulty <= 2 and any(token in post.subtopic.lower() for token in ("advanced", "expert", "senior")):
        include_subtopic = False
    topic_phrase = (
        f"{post.topic.lower()} and {post.subtopic.lower()}"
        if include_subtopic
        else post.topic.lower()
    )
    register_prefix = _register_sentence_prefix(author_profile.register_level if author_profile else None)
    style_sentence = _style_sentence(author_profile.writing_style_family if author_profile else None)
    preserved_clause = _preserve_original_clause(record.content, post.topic, post.subtopic)
    repaired_content = (
        f"{register_prefix} This {post.format.replace('_', ' ')} covers {topic_phrase} "
        f"in a {difficulty_label} explanation. "
        f"{style_sentence} "
        f"{preserved_clause} "
        f"{_format_repair_cue(post.format)} "
        f"It stays consistent with the {post.goal_relation_type.replace('_', ' ')} context."
    )
    return RenderedPostText(
        render_id=record.render_id,
        post_id=record.post_id,
        prompt_id=record.prompt_id,
        model_name=record.model_name,
        provider=f"{record.provider}_repair",
        title=repaired_title,
        content=repaired_content,
    )


def _format_repair_cue(content_format: str) -> str:
    """Return one format-specific cue phrase used by rule-based post repair."""
    if content_format == "project_log":
        return "The project log notes build and debug checkpoints."
    if content_format == "resource_post":
        return "This resource post links to a practical reference guide."
    if content_format == "reflection_post":
        return "I reflect on the lesson learned from this study attempt."
    if content_format == "qa_post":
        return "The question is answered with a direct rationale."
    return "The structure stays specific instead of generic filler."


def _repair_comment_render_text(
    record: RenderedCommentText,
    interaction: InteractionRecord,
    post: PostRecord,
    *,
    commenter_profile: UserProfile | None,
) -> RenderedCommentText:
    """Create a persona-aware comment rewrite that remains metadata-consistent."""
    prefix = "Replying to your point, " if interaction.reply_to_interaction_id else ""
    register_phrase = _register_comment_phrase(commenter_profile.register_level if commenter_profile else None)
    style_phrase = _style_comment_phrase(commenter_profile.writing_style_family if commenter_profile else None)
    preserved_clause = _preserve_original_clause(record.comment_text, post.topic, post.subtopic)
    repaired_text = (
        f"{prefix}{register_phrase} this {post.topic.lower()} post on {post.subtopic.lower()} is clear and useful. "
        f"{style_phrase} {preserved_clause} "
        "I can apply the same idea in my next study session."
    ).strip()
    return RenderedCommentText(
        render_id=record.render_id,
        interaction_id=record.interaction_id,
        post_id=record.post_id,
        prompt_id=record.prompt_id,
        model_name=record.model_name,
        provider=f"{record.provider}_repair",
        comment_text=repaired_text,
    )


def _register_sentence_prefix(register_level: str | None) -> str:
    """Return a light register-specific opener for repaired post text."""
    if register_level == "formal":
        return "In summary,"
    if register_level == "casual":
        return "Quick take,"
    return "Overall,"


def _style_sentence(writing_style_family: str | None) -> str:
    """Return one persona-style sentence for repaired post text."""
    if writing_style_family == "analytical":
        return "I break it into steps and keep the reasoning explicit."
    if writing_style_family == "encouraging":
        return "The tone stays supportive and practical for peers."
    if writing_style_family == "reflective":
        return "I connect the point to what I learned from prior attempts."
    return "I keep the explanation short and concrete."


def _register_comment_phrase(register_level: str | None) -> str:
    """Return a register-aware phrase for repaired comments."""
    if register_level == "formal":
        return "From my perspective,"
    if register_level == "casual":
        return "Honestly,"
    return "For me,"


def _style_comment_phrase(writing_style_family: str | None) -> str:
    """Return a writing-style-aware phrase for repaired comments."""
    if writing_style_family == "analytical":
        return "The key mechanism is easy to follow."
    if writing_style_family == "encouraging":
        return "It is motivating and actionable."
    if writing_style_family == "reflective":
        return "It matches what I observed in my own practice."
    return "The point is direct and clear."


def _preserve_original_clause(text: str, topic: str, subtopic: str) -> str:
    """Preserve a short safe clause from failed text when it references target topics."""
    normalized = " ".join(text.strip().split())
    if not normalized:
        return ""
    lower = normalized.lower()
    if topic.lower() in lower or subtopic.lower() in lower:
        words = normalized.split()
        return f"Original intent retained: {' '.join(words[:14])}."
    return ""


def _build_scale_text_validation_report(
    *,
    total_post_candidates: int,
    total_comment_candidates: int,
    post_reconcile: dict[str, Any],
    comment_reconcile: dict[str, Any],
    rule_issues: list[dict[str, Any]],
    llm_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one normalized validation report for Phase-9 scale text rendering."""
    discarded_total = len(post_reconcile["discarded_ids"]) + len(comment_reconcile["discarded_ids"])
    total_issues = len(rule_issues) + len(llm_issues)
    return {
        "status": "failed" if discarded_total > 0 else "passed",
        "total_post_candidates": total_post_candidates,
        "total_comment_candidates": total_comment_candidates,
        "post_round_reports": post_reconcile["round_reports"],
        "comment_round_reports": comment_reconcile["round_reports"],
        "post_repaired_ids": sorted(post_reconcile["repaired_ids"]),
        "post_discarded_ids": sorted(post_reconcile["discarded_ids"]),
        "comment_repaired_ids": sorted(comment_reconcile["repaired_ids"]),
        "comment_discarded_ids": sorted(comment_reconcile["discarded_ids"]),
        "rule_issue_count": len(rule_issues),
        "llm_issue_count": len(llm_issues),
        "issue_count": total_issues,
        "issues": rule_issues + llm_issues,
    }


def _build_scale_text_metrics(
    *,
    total_post_candidates: int,
    total_comment_candidates: int,
    post_reconcile: dict[str, Any],
    comment_reconcile: dict[str, Any],
    rule_issues: list[dict[str, Any]],
    llm_issues: list[dict[str, Any]],
    llm_sample_size: int,
) -> dict[str, Any]:
    """Build batch-level Phase-9 text-quality metrics for monitoring and tuning."""
    total_candidates = max(1, total_post_candidates + total_comment_candidates)
    initial_failed = len(post_reconcile["failed_on_first_round_ids"]) + len(comment_reconcile["failed_on_first_round_ids"])
    repaired_total = len(post_reconcile["repaired_ids"]) + len(comment_reconcile["repaired_ids"])
    discarded_total = len(post_reconcile["discarded_ids"]) + len(comment_reconcile["discarded_ids"])
    contradiction_issue_count = sum(
        1
        for issue in rule_issues + llm_issues
        if str(issue.get("code", "")).endswith("contradiction") or "topic_missing" in str(issue.get("code", ""))
    )
    return {
        "candidate_count": total_post_candidates + total_comment_candidates,
        "rendered_post_count": len(post_reconcile["records"]),
        "rendered_comment_count": len(comment_reconcile["records"]),
        "initial_validation_failure_rate": initial_failed / float(total_candidates),
        "text_contradiction_rate": contradiction_issue_count / float(total_candidates),
        "repair_rate": repaired_total / float(total_candidates),
        "discard_rate": discarded_total / float(total_candidates),
        "llm_sample_size_requested": llm_sample_size,
        "llm_sampled_payload_count": post_reconcile["sampled_payload_count"]
        + comment_reconcile["sampled_payload_count"],
        "issue_count_by_code": _count_issues_by_code(rule_issues + llm_issues),
    }


def write_render_scale_artifacts(
    *,
    output_dir: str | Path,
    rendered_posts: list[RenderedPostText],
    rendered_comments: list[RenderedCommentText],
    validation_report: dict[str, Any],
    metrics: dict[str, Any],
) -> dict[str, str]:
    """Write Phase-9 scale text outputs, validation report, and metrics bundle."""
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    rendered_posts_path = _write_jsonl_records(rendered_posts, root / "scale_rendered_posts.jsonl")
    rendered_comments_path = _write_jsonl_records(rendered_comments, root / "scale_rendered_comments.jsonl")
    validation_path = _write_json(validation_report, root / "scale_text_validation_report.json")
    metrics_path = _write_json(metrics, root / "scale_text_metrics.json")
    return {
        "scale_rendered_posts": str(rendered_posts_path),
        "scale_rendered_comments": str(rendered_comments_path),
        "scale_text_validation_report": str(validation_path),
        "scale_text_metrics": str(metrics_path),
    }


def select_seed_post_targets(world_state: WorldState, *, limit: int | None) -> list[PostRecord]:
    """Select a deterministic small post subset for seed rendering."""
    ordered = sorted(world_state.posts, key=lambda post: (post.created_at, post.post_id), reverse=True)
    if limit is None:
        return ordered
    return ordered[:limit]


def select_seed_comment_target_groups(
    world_state: WorldState,
    *,
    limit: int | None,
    max_comments_per_post_request: int,
) -> list[tuple[PostRecord, list[InteractionRecord]]]:
    """Select comment targets grouped by post for one-post-per-request rendering."""
    posts_by_id = {post.post_id: post for post in world_state.posts}
    grouped: dict[str, list[InteractionRecord]] = {}
    for interaction in sorted(world_state.interactions, key=lambda item: (item.timestamp, item.interaction_id)):
        if interaction.event_type != "comment":
            continue
        grouped.setdefault(interaction.post_id, []).append(interaction)

    groups: list[tuple[PostRecord, list[InteractionRecord]]] = []
    for post_id, interactions in grouped.items():
        post = posts_by_id.get(post_id)
        if post is None:
            continue
        for start in range(0, len(interactions), max(1, max_comments_per_post_request)):
            chunk = interactions[start : start + max(1, max_comments_per_post_request)]
            groups.append((post, chunk))
    groups.sort(key=lambda item: (item[0].created_at, item[0].post_id), reverse=True)
    if limit is None:
        return groups
    return groups[:limit]


def select_scale_comment_target_groups_by_provider(
    world_state: WorldState,
    *,
    user_provider_assignments: dict[str, str],
    limit: int | None,
    max_comments_per_post_request: int,
) -> list[tuple[str, PostRecord, list[InteractionRecord]]]:
    """Group scale comment targets by post and assigned provider.

    This preserves the one-post request shape while ensuring every request is
    provider-consistent at the user level: a single user's comments always go to
    the same model, even if that means one post fans out into two provider shards.
    """
    posts_by_id = {post.post_id: post for post in world_state.posts}
    grouped: dict[tuple[str, str], list[InteractionRecord]] = {}
    for interaction in sorted(world_state.interactions, key=lambda item: (item.timestamp, item.interaction_id)):
        if interaction.event_type != "comment":
            continue
        provider = user_provider_assignments.get(interaction.user_id, "openai")
        grouped.setdefault((interaction.post_id, provider), []).append(interaction)

    groups: list[tuple[str, PostRecord, list[InteractionRecord]]] = []
    chunk_size = max(1, max_comments_per_post_request)
    for (post_id, provider), interactions in grouped.items():
        post = posts_by_id.get(post_id)
        if post is None:
            continue
        for start in range(0, len(interactions), chunk_size):
            groups.append((provider, post, interactions[start : start + chunk_size]))
    groups.sort(key=lambda item: (item[1].created_at, item[1].post_id, item[0]), reverse=True)
    if limit is None:
        return groups
    return groups[:limit]


def write_provider_batch_artifacts(
    *,
    output_dir: str | Path,
    stage_name: str,
    openai_builder: OpenAISeedBatchBuilder,
    gemini_builder: GeminiBatchBuilder,
    openai_prompts: list[PostRenderPrompt | CommentSetRenderPrompt],
    gemini_prompts: list[PostRenderPrompt | CommentSetRenderPrompt],
    request_kind: str,
) -> dict[str, str]:
    """Write provider-specific batch inputs, registries, and manifests for one stage."""
    files: dict[str, str] = {}
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    if openai_prompts:
        if request_kind == "posts":
            openai_requests = openai_builder.build_post_requests(openai_prompts)
        else:
            openai_requests = openai_builder.build_comment_set_requests(openai_prompts)
        files.update(
            _write_single_provider_batch_artifacts(
                root=root,
                provider_name="openai",
                stage_name=stage_name,
                request_kind=request_kind,
                prompts=openai_prompts,
                requests=openai_requests,
                builder=openai_builder,
            )
        )

    if gemini_prompts:
        if request_kind == "posts":
            gemini_requests = gemini_builder.build_post_requests(gemini_prompts)
        else:
            gemini_requests = gemini_builder.build_comment_set_requests(gemini_prompts)
        files.update(
            _write_single_provider_batch_artifacts(
                root=root,
                provider_name="gemini",
                stage_name=stage_name,
                request_kind=request_kind,
                prompts=gemini_prompts,
                requests=gemini_requests,
                builder=gemini_builder,
            )
        )
    return files


def _write_single_provider_batch_artifacts(
    *,
    root: Path,
    provider_name: str,
    stage_name: str,
    request_kind: str,
    prompts: list[PostRenderPrompt | CommentSetRenderPrompt],
    requests: list[dict[str, Any]],
    builder: OpenAISeedBatchBuilder | GeminiBatchBuilder,
) -> dict[str, str]:
    """Write one provider shard for one stage."""
    stem = f"{stage_name}_{provider_name}"
    batch_input_path = builder.write_batch_input(requests, root / f"{stem}_batch_input.jsonl")
    prompt_registry_path = _write_jsonl_records(
        [
            _batch_registry_record(prompt, request, provider_name=provider_name, request_kind=request_kind)
            for prompt, request in zip(prompts, requests)
        ],
        root / f"{stem}_prompt_registry.jsonl",
    )
    manifest_path = builder.write_batch_manifest(
        batch_input_path=batch_input_path,
        request_count=len(requests),
        path=root / f"{stem}_submit_manifest.json",
        request_kind=request_kind,
        prompt_registry_path=prompt_registry_path,
    )
    return {
        f"{stem}_batch_input": str(batch_input_path),
        f"{stem}_prompt_registry": str(prompt_registry_path),
        f"{stem}_submit_manifest": str(manifest_path),
    }


def _batch_registry_record(
    prompt: PostRenderPrompt | CommentSetRenderPrompt,
    request: dict[str, Any],
    *,
    provider_name: str,
    request_kind: str,
) -> dict[str, Any]:
    """Normalize prompt metadata into a compact registry record for later collection."""
    record: dict[str, Any] = {
        "prompt_id": prompt.prompt_id,
        "post_id": prompt.post_id,
        "topic": prompt.topic,
        "provider": provider_name,
        "request_kind": request_kind,
        "batch_request": request,
    }
    if isinstance(prompt, PostRenderPrompt):
        record.update(
            {
                "author_id": prompt.author_id,
                "content_format": prompt.content_format,
                "difficulty": prompt.difficulty,
            }
        )
        return record
    record.update(
        {
            "commenter_user_ids": [target.user_id for target in prompt.comment_targets],
            "comment_interaction_ids": [target.interaction_id for target in prompt.comment_targets],
        }
    )
    return record


def _build_user_provider_assignments(
    users: list[UserProfile],
    *,
    gemini_share_percentage: int,
) -> dict[str, str]:
    """Assign each user to one provider so all of their text stays model-consistent."""
    ordered_users = sorted(users, key=lambda user: _stable_user_shuffle_key(user.user_id))
    gemini_count = round(len(ordered_users) * (gemini_share_percentage / 100.0))
    assignments: dict[str, str] = {}
    for index, user in enumerate(ordered_users):
        assignments[user.user_id] = "gemini" if index < gemini_count else "openai"
    return assignments


def _stable_user_shuffle_key(user_id: str) -> str:
    """Return a stable shuffle key so provider assignment is deterministic across stages."""
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()


def _count_provider_assignments(user_provider_assignments: dict[str, str]) -> dict[str, int]:
    """Count how many users are assigned to each provider."""
    counts = {"openai": 0, "gemini": 0}
    for provider in user_provider_assignments.values():
        counts[provider] = counts.get(provider, 0) + 1
    return counts


def _load_rendered_posts_sidecars(path: str | Path) -> dict[str, RenderedPostText]:
    """Load rendered post sidecars keyed by post id for comment-stage prompt preparation."""
    rendered_by_post_id: dict[str, RenderedPostText] = {}
    for payload in _load_jsonl_registry(path):
        post_id = str(payload.get("post_id", "")).strip()
        if not post_id:
            continue
        rendered_by_post_id[post_id] = RenderedPostText(
            render_id=str(payload.get("render_id", f"rpost_{post_id}")),
            post_id=post_id,
            prompt_id=str(payload.get("prompt_id", "")),
            model_name=str(payload.get("model_name", "unknown")),
            provider=str(payload.get("provider", "unknown")),
            title=str(payload.get("title", "")).strip(),
            content=str(payload.get("content", "")).strip(),
            validator_status=str(payload.get("validator_status", "collected")),
        )
    return rendered_by_post_id


def write_openai_batch_artifacts(
    *,
    output_dir: str | Path,
    builder: OpenAISeedBatchBuilder,
    post_prompts: list[Any],
    comment_prompts: list[Any],
    post_requests: list[dict[str, Any]],
    comment_requests: list[dict[str, Any]],
    posts_by_id: dict[str, PostRecord],
) -> dict[str, str]:
    """Write separate post/comment-set batch inputs, registries, and submit manifests."""
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}

    post_registry = [
        {
            "prompt_id": prompt.prompt_id,
            "post_id": prompt.post_id,
            "topic": prompt.topic,
            "content_format": prompt.content_format,
            "difficulty": prompt.difficulty,
            "batch_request": request,
        }
        for prompt, request in zip(post_prompts, post_requests)
    ]
    comment_registry = [
        {
            "prompt_id": prompt.prompt_id,
            "post_id": prompt.post_id,
            "topic": prompt.topic,
            "comment_interaction_ids": [target.interaction_id for target in prompt.comment_targets],
            "batch_request": request,
        }
        for prompt, request in zip(comment_prompts, comment_requests)
    ]

    post_input_path = builder.write_batch_input(post_requests, root / "openai_posts_batch_input.jsonl")
    post_registry_path = _write_jsonl_records(post_registry, root / "openai_posts_prompt_registry.jsonl")
    rendered_post_targets_path = _write_jsonl_records(
        [posts_by_id[prompt.post_id] for prompt in post_prompts],
        root / "seed_post_targets.jsonl",
    )

    post_manifest_path = builder.write_batch_manifest(
        batch_input_path=post_input_path,
        request_count=len(post_requests),
        path=root / "openai_posts_submit_manifest.json",
        request_kind="posts",
        prompt_registry_path=post_registry_path,
    )
    files.update(
        {
            "seed_post_targets": str(rendered_post_targets_path),
            "openai_posts_batch_input": str(post_input_path),
            "openai_posts_prompt_registry": str(post_registry_path),
            "openai_posts_submit_manifest": str(post_manifest_path),
        }
    )
    if comment_requests:
        comment_input_path = builder.write_batch_input(comment_requests, root / "openai_comment_sets_batch_input.jsonl")
        comment_registry_path = _write_jsonl_records(comment_registry, root / "openai_comment_sets_prompt_registry.jsonl")
        comment_manifest_path = builder.write_batch_manifest(
            batch_input_path=comment_input_path,
            request_count=len(comment_requests),
            path=root / "openai_comment_sets_submit_manifest.json",
            request_kind="comment_sets",
            prompt_registry_path=comment_registry_path,
        )
        files.update(
            {
                "openai_comment_sets_batch_input": str(comment_input_path),
                "openai_comment_sets_prompt_registry": str(comment_registry_path),
                "openai_comment_sets_submit_manifest": str(comment_manifest_path),
            }
        )

    return files


def write_render_seed_artifacts(
    *,
    output_dir: str | Path,
    rendered_posts: list[RenderedPostText],
    rendered_comments: list[RenderedCommentText],
    issues: list[dict[str, Any]],
) -> dict[str, str]:
    """Write locally rendered seed sidecars and text validation report."""
    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    rendered_posts_path = _write_jsonl_records(rendered_posts, root / "rendered_posts.jsonl")
    rendered_comments_path = _write_jsonl_records(rendered_comments, root / "rendered_comments.jsonl")
    text_validation_path = _write_json(
        {
            "status": "passed" if not issues else "failed",
            "issue_count": len(issues),
            "issues": issues,
        },
        root / "text_validation_report.json",
    )
    return {
        "rendered_posts": str(rendered_posts_path),
        "rendered_comments": str(rendered_comments_path),
        "text_validation_report": str(text_validation_path),
    }


def _effective_llm_sample_count(total_payload_count: int, sample_size: int | None) -> int:
    """Return how many payloads will be sampled by `validate_text_with_llm`."""
    if sample_size is None:
        return total_payload_count
    return min(max(0, sample_size), total_payload_count)


def _collect_failed_record_ids(issues: list[dict[str, Any]], valid_record_ids: set[str]) -> set[str]:
    """Extract failed record ids from validation issues for current candidate records."""
    failed: set[str] = set()
    for issue in issues:
        context = issue.get("context", {})
        if not isinstance(context, dict):
            continue
        record_id = str(context.get("record_id", ""))
        if record_id and record_id in valid_record_ids:
            failed.add(record_id)
    return failed


def _count_issues_by_code(issues: list[dict[str, Any]]) -> dict[str, int]:
    """Count validation issues grouped by `code` for batch monitoring."""
    counts: dict[str, int] = {}
    for issue in issues:
        code = str(issue.get("code", "unknown"))
        counts[code] = counts.get(code, 0) + 1
    return counts


def _attach_rendered_posts_to_comment_prompts(
    prompts: list[CommentSetRenderPrompt],
    rendered_posts_by_post_id: dict[str, RenderedPostText],
    posts_by_id: dict[str, PostRecord],
) -> list[CommentSetRenderPrompt]:
    """Rebuild comment prompts so local stub rendering can see target post text."""
    rebuilt: list[CommentSetRenderPrompt] = []
    for prompt in prompts:
        post = posts_by_id[prompt.post_id]
        rebuilt.append(
            build_comment_render_prompt(
                post,
                rendered_post=rendered_posts_by_post_id.get(prompt.post_id),
                comment_targets=prompt.comment_targets,
            )
        )
    return rebuilt


def _batch_job_completed(provider: str, batch_status: dict[str, Any]) -> bool:
    """Return whether a provider-specific batch status payload is terminal-success."""
    if provider == "gemini":
        return str(batch_status.get("metadata", {}).get("state", "")) == "JOB_STATE_SUCCEEDED"
    return str(batch_status.get("status", "")) == "completed"


def _parse_provider_outputs(
    *,
    provider: str,
    output_jsonl_path: str | Path,
    model_name: str,
) -> dict[str, Any]:
    """Parse output JSONL via the correct provider-specific builder."""
    if provider == "gemini":
        return GeminiBatchBuilder(model_name=model_name).parse_batch_output(output_jsonl_path)
    return OpenAISeedBatchBuilder(model_name=model_name).parse_batch_output(output_jsonl_path)


def _parse_rendered_posts_from_outputs(
    outputs: dict[str, Any],
    registry: list[dict[str, Any]],
    model_name: str,
    *,
    provider_name: str,
) -> list[RenderedPostText]:
    """Convert collected post batch outputs into rendered post sidecars."""
    items_by_prompt_id = {item["prompt_id"]: item for item in registry}
    rendered: list[RenderedPostText] = []
    for prompt_id, payload in outputs.items():
        registry_item = items_by_prompt_id.get(prompt_id)
        if registry_item is None or not isinstance(payload, dict):
            continue
        rendered.append(
            RenderedPostText(
                render_id=f"rpost_{prompt_id}",
                post_id=registry_item["post_id"],
                prompt_id=prompt_id,
                model_name=model_name,
                provider=provider_name,
                title=str(payload.get("title", "")).strip(),
                content=str(payload.get("content", "")).strip(),
                validator_status="collected",
            )
        )
    return rendered


def _parse_rendered_comments_from_outputs(
    outputs: dict[str, Any],
    registry: list[dict[str, Any]],
    model_name: str,
    *,
    provider_name: str,
) -> list[RenderedCommentText]:
    """Convert collected comment-set batch outputs into per-comment sidecars."""
    items_by_prompt_id = {item["prompt_id"]: item for item in registry}
    rendered: list[RenderedCommentText] = []
    for prompt_id, payload in outputs.items():
        registry_item = items_by_prompt_id.get(prompt_id)
        if registry_item is None or not isinstance(payload, dict):
            continue
        for comment in payload.get("comments", []):
            interaction_id = str(comment.get("interaction_id", "")).strip()
            if not interaction_id:
                continue
            rendered.append(
                RenderedCommentText(
                    render_id=f"rcmt_{interaction_id}",
                    interaction_id=interaction_id,
                    post_id=registry_item["post_id"],
                    prompt_id=prompt_id,
                    model_name=model_name,
                    provider=provider_name,
                    comment_text=str(comment.get("comment_text", "")).strip(),
                    validator_status="collected",
                )
            )
    return rendered


def _collect_failed_custom_ids(error_jsonl_path: str | Path, *, provider: str) -> list[str]:
    """Collect failed request ids from provider-specific error JSONL files."""
    failed: list[str] = []
    source = Path(error_jsonl_path).expanduser().resolve()
    if not source.is_file():
        return failed
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            request_id = payload.get("custom_id") if provider == "openai" else payload.get("key")
            if request_id:
                failed.append(str(request_id))
    return failed


def _load_jsonl_registry(path: str | Path) -> list[dict[str, Any]]:
    """Load a small JSONL registry file into memory."""
    records: list[dict[str, Any]] = []
    source = Path(path).expanduser().resolve()
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def _write_jsonl_records(records: list[Any], path: Path) -> Path:
    """Write JSONL records with stable encoding."""
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_to_jsonable(record), sort_keys=True))
            handle.write("\n")
    return path


def _write_json(payload: dict[str, Any], path: Path) -> Path:
    """Write one JSON document with stable formatting."""
    path.write_text(json.dumps(_to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")
    return path


def _mark_post_render_status(record: RenderedPostText, status: str) -> RenderedPostText:
    """Return a copied post render record with validator status set."""
    return RenderedPostText(
        render_id=record.render_id,
        post_id=record.post_id,
        prompt_id=record.prompt_id,
        model_name=record.model_name,
        provider=record.provider,
        title=record.title,
        content=record.content,
        validator_status=status,
    )


def _mark_comment_render_status(record: RenderedCommentText, status: str) -> RenderedCommentText:
    """Return a copied comment render record with validator status set."""
    return RenderedCommentText(
        render_id=record.render_id,
        interaction_id=record.interaction_id,
        post_id=record.post_id,
        prompt_id=record.prompt_id,
        model_name=record.model_name,
        provider=record.provider,
        comment_text=record.comment_text,
        validator_status=status,
    )
