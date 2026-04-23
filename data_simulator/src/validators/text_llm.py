"""Sampled LLM-style cross-check hooks for rendered text validation."""

from __future__ import annotations

from typing import Any, Callable

from config.models import RenderedCommentText, RenderedPostText

ValidationIssue = dict[str, Any]
LlmTextValidator = Callable[[dict[str, Any]], list[ValidationIssue]]


def validate_text_with_llm(
    *,
    rendered_posts: list[RenderedPostText],
    rendered_comments: list[RenderedCommentText],
    llm_validator: LlmTextValidator | None = None,
    sample_size: int | None = None,
) -> list[ValidationIssue]:
    """Run sampled LLM-style cross-check validation when a validator hook is supplied."""
    if llm_validator is None:
        return []

    sampled_payloads = _select_sample_payloads(
        rendered_posts=rendered_posts,
        rendered_comments=rendered_comments,
        sample_size=sample_size,
    )
    issues: list[ValidationIssue] = []
    for payload in sampled_payloads:
        issues.extend(llm_validator(payload))
    return issues


def _select_sample_payloads(
    *,
    rendered_posts: list[RenderedPostText],
    rendered_comments: list[RenderedCommentText],
    sample_size: int | None,
) -> list[dict[str, Any]]:
    """Select a deterministic prefix sample for seed-only cross-check validation."""
    payloads: list[dict[str, Any]] = []
    for record in rendered_posts:
        payloads.append(
            {
                "record_type": "post",
                "record_id": record.post_id,
                "prompt_id": record.prompt_id,
                "text": {"title": record.title, "content": record.content},
            }
        )
    for record in rendered_comments:
        payloads.append(
            {
                "record_type": "comment",
                "record_id": record.interaction_id,
                "prompt_id": record.prompt_id,
                "text": {"comment_text": record.comment_text},
            }
        )

    if sample_size is None or sample_size >= len(payloads):
        return payloads
    return payloads[:sample_size]
