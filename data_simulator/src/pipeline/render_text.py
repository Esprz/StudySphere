"""Phase-8 seed text rendering and batch-artifact pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.models import (
    CommentRenderTarget,
    CommentSetRenderPrompt,
    InteractionRecord,
    PostRecord,
    RenderedCommentText,
    RenderedPostText,
    WorldState,
)
from exporters.simulator_json import _to_jsonable
from renderers.prompts import (
    build_comment_render_prompt,
    build_comment_render_target,
    build_post_render_prompt,
)
from renderers.text_render import OpenAISeedBatchBuilder, StubSeedTextRenderer
from validators.text_llm import validate_text_with_llm
from validators.text_rules import validate_rendered_text_bundle


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
    rendered_comments = renderer.render_comments(
        _attach_rendered_posts_to_comment_prompts(
            prepared["comment_prompts"],
            rendered_posts_by_post_id,
            {post.post_id: post for post in world_state.posts},
        )
    )

    posts_by_id = {post.post_id: post for post in world_state.posts}
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
        "comment_prompts": prepared["comment_prompts"],
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


def prepare_openai_seed_batches(
    world_state: WorldState,
    *,
    output_dir: str | Path | None = None,
    seed_model_name: str = "gpt-5.4-nano",
    post_target_count: int = 12,
    comment_target_count: int = 12,
    max_comments_per_post_request: int = 4,
) -> dict[str, Any]:
    """Prepare separate OpenAI Batch submit artifacts for posts and comment sets."""
    users_by_id = {user.user_id: user for user in world_state.users}
    posts_by_id = {post.post_id: post for post in world_state.posts}

    post_targets = select_seed_post_targets(world_state, limit=post_target_count)
    comment_target_groups = select_seed_comment_target_groups(
        world_state,
        limit=comment_target_count,
        max_comments_per_post_request=max_comments_per_post_request,
    )

    post_prompts = [
        build_post_render_prompt(post, author_profile=users_by_id.get(post.author_id))
        for post in post_targets
    ]
    comment_prompts = [
        build_comment_render_prompt(
            post,
            rendered_post=None,
            comment_targets=[
                build_comment_render_target(interaction, users_by_id.get(interaction.user_id))
                for interaction in interactions
            ],
        )
        for post, interactions in comment_target_groups
    ]

    builder = OpenAISeedBatchBuilder(model_name=seed_model_name)
    post_requests = builder.build_post_requests(post_prompts)
    comment_requests = builder.build_comment_set_requests(comment_prompts)

    artifacts: dict[str, Any] = {
        "post_prompts": post_prompts,
        "comment_prompts": comment_prompts,
        "post_requests": post_requests,
        "comment_requests": comment_requests,
        "status": "prepared",
        "files": {},
    }
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
            report["rendered_posts"] = _parse_rendered_posts_from_outputs(parsed, registry, builder.model_name)
        elif batch_kind == "comment_sets":
            registry = _load_jsonl_registry(manifest["prompt_registry_path"])
            report["rendered_comments"] = _parse_rendered_comments_from_outputs(parsed, registry, builder.model_name)

    if error_jsonl_path is not None:
        report["failed_custom_ids"] = _collect_failed_custom_ids(error_jsonl_path)

    return report


def prepare_openai_seed_retry_batches(
    *,
    collect_report_path: str | Path,
    output_dir: str | Path,
) -> dict[str, str]:
    """Prepare a retry batch from a prior collect report, without auto-submitting it."""
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
    retry_manifest_path = _write_json(
        {
            "provider": manifest["provider"],
            "model_name": manifest["model_name"],
            "endpoint": manifest["endpoint"],
            "completion_window": manifest["completion_window"],
            "request_kind": manifest["request_kind"],
            "request_count": len(selected),
            "batch_input_path": str(retry_input_path),
            "prompt_registry_path": str(retry_registry_path),
            "source_collect_report_path": str(Path(collect_report_path).expanduser().resolve()),
            "notes": [
                "This retry batch was prepared from failed_custom_ids only.",
                "Submission is manual and separate from preparation.",
            ],
        },
        root / f"{report['batch_kind']}_retry_submit_manifest.json",
    )
    return {
        "retry_batch_input": str(retry_input_path),
        "retry_prompt_registry": str(retry_registry_path),
        "retry_submit_manifest": str(retry_manifest_path),
    }


def select_seed_post_targets(world_state: WorldState, *, limit: int) -> list[PostRecord]:
    """Select a deterministic small post subset for seed rendering."""
    ordered = sorted(world_state.posts, key=lambda post: (post.created_at, post.post_id), reverse=True)
    return ordered[:limit]


def select_seed_comment_target_groups(
    world_state: WorldState,
    *,
    limit: int,
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
    return groups[:limit]


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
    comment_input_path = builder.write_batch_input(comment_requests, root / "openai_comment_sets_batch_input.jsonl")
    post_registry_path = _write_jsonl_records(post_registry, root / "openai_posts_prompt_registry.jsonl")
    comment_registry_path = _write_jsonl_records(comment_registry, root / "openai_comment_sets_prompt_registry.jsonl")
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
    comment_manifest_path = builder.write_batch_manifest(
        batch_input_path=comment_input_path,
        request_count=len(comment_requests),
        path=root / "openai_comment_sets_submit_manifest.json",
        request_kind="comment_sets",
        prompt_registry_path=comment_registry_path,
    )

    return {
        "seed_post_targets": str(rendered_post_targets_path),
        "openai_posts_batch_input": str(post_input_path),
        "openai_posts_prompt_registry": str(post_registry_path),
        "openai_posts_submit_manifest": str(post_manifest_path),
        "openai_comment_sets_batch_input": str(comment_input_path),
        "openai_comment_sets_prompt_registry": str(comment_registry_path),
        "openai_comment_sets_submit_manifest": str(comment_manifest_path),
    }


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


def _parse_rendered_posts_from_outputs(
    outputs: dict[str, Any],
    registry: list[dict[str, Any]],
    model_name: str,
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
                provider="openai_batch",
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
                    provider="openai_batch",
                    comment_text=str(comment.get("comment_text", "")).strip(),
                    validator_status="collected",
                )
            )
    return rendered


def _collect_failed_custom_ids(error_jsonl_path: str | Path) -> list[str]:
    """Collect failed custom_id values from a downloaded error jsonl file."""
    failed: list[str] = []
    source = Path(error_jsonl_path).expanduser().resolve()
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            custom_id = payload.get("custom_id")
            if custom_id:
                failed.append(str(custom_id))
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
