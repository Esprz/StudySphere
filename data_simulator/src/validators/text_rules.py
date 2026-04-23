"""Rule-based text validators for rendered post/comment sidecars."""

from __future__ import annotations

from typing import Any

from config.models import InteractionRecord, PostRecord, RenderedCommentText, RenderedPostText

ValidationIssue = dict[str, Any]


def validate_rendered_posts(
    rendered_posts: list[RenderedPostText],
    posts_by_id: dict[str, PostRecord],
) -> list[ValidationIssue]:
    """Validate rendered post text against structured post metadata."""
    issues: list[ValidationIssue] = []
    for rendered in rendered_posts:
        post = posts_by_id.get(rendered.post_id)
        if post is None:
            issues.append(_issue("missing_post_reference", "rendered post references unknown post_id", rendered.post_id))
            continue

        combined = f"{rendered.title}\n{rendered.content}".lower()
        if not rendered.title.strip() or not rendered.content.strip():
            issues.append(_issue("empty_post_text", "rendered post text must not be empty", rendered.post_id))
        if post.topic.lower() not in combined and post.subtopic.lower() not in combined:
            issues.append(_issue("topic_missing", "rendered post text does not mention topic/subtopic", rendered.post_id))
        if post.difficulty >= 4 and any(term in combined for term in ("absolute beginner", "for beginners", "beginner guide")):
            issues.append(_issue("difficulty_contradiction", "high-difficulty post sounds beginner-only", rendered.post_id))
        if post.difficulty <= 2 and any(term in combined for term in ("advanced", "expert-only", "senior-level")):
            issues.append(_issue("difficulty_contradiction", "low-difficulty post sounds too advanced", rendered.post_id))
        _validate_post_format(issues, rendered, post, combined)
    return issues


def validate_rendered_comments(
    rendered_comments: list[RenderedCommentText],
    interactions_by_id: dict[str, InteractionRecord],
    posts_by_id: dict[str, PostRecord],
) -> list[ValidationIssue]:
    """Validate rendered comment sidecars against interaction/post metadata."""
    issues: list[ValidationIssue] = []
    for rendered in rendered_comments:
        interaction = interactions_by_id.get(rendered.interaction_id)
        if interaction is None:
            issues.append(
                _issue("missing_interaction_reference", "rendered comment references unknown interaction_id", rendered.interaction_id)
            )
            continue
        if interaction.event_type != "comment":
            issues.append(
                _issue("interaction_type_mismatch", "rendered comment must point to a comment interaction", rendered.interaction_id)
            )
        post = posts_by_id.get(rendered.post_id)
        if post is None:
            issues.append(_issue("missing_post_reference", "rendered comment references unknown post_id", rendered.post_id))
            continue
        text = rendered.comment_text.strip().lower()
        if not text:
            issues.append(_issue("empty_comment_text", "rendered comment text must not be empty", rendered.interaction_id))
        if post.topic.lower() not in text and post.subtopic.lower() not in text:
            issues.append(
                _issue("comment_topic_missing", "rendered comment does not mention topic/subtopic", rendered.interaction_id)
            )
    return issues


def validate_rendered_text_bundle(
    *,
    rendered_posts: list[RenderedPostText],
    rendered_comments: list[RenderedCommentText],
    posts_by_id: dict[str, PostRecord],
    interactions_by_id: dict[str, InteractionRecord],
) -> list[ValidationIssue]:
    """Validate the full rendered seed-text bundle with rule-based checks."""
    issues = validate_rendered_posts(rendered_posts, posts_by_id)
    issues.extend(validate_rendered_comments(rendered_comments, interactions_by_id, posts_by_id))
    return issues


def _validate_post_format(
    issues: list[ValidationIssue],
    rendered: RenderedPostText,
    post: PostRecord,
    combined: str,
) -> None:
    """Apply lightweight format-specific heuristics for obvious contradictions."""
    format_name = post.format
    if format_name == "qa_post" and "?" not in combined:
        issues.append(_issue("format_contradiction", "qa_post should look like a question", rendered.post_id))
    if format_name == "project_log" and not any(term in combined for term in ("project", "build", "debug", "log")):
        issues.append(_issue("format_contradiction", "project_log lacks project/log cues", rendered.post_id))
    if format_name == "resource_post" and not any(term in combined for term in ("resource", "reference", "guide", "roundup")):
        issues.append(_issue("format_contradiction", "resource_post lacks resource cues", rendered.post_id))
    if format_name == "reflection_post" and not any(term in combined for term in ("reflect", "learned", "lesson")):
        issues.append(_issue("format_contradiction", "reflection_post lacks reflection cues", rendered.post_id))


def _issue(code: str, message: str, record_id: str) -> ValidationIssue:
    """Construct one normalized text-rule validation issue."""
    return {
        "validator": "text_rules",
        "severity": "error",
        "code": code,
        "message": message,
        "context": {"record_id": record_id},
    }
