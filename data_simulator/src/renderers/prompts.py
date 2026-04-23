"""Prompt builders for post/comment seed text rendering."""

from __future__ import annotations

from config.models import (
    CommentRenderTarget,
    CommentSetRenderPrompt,
    InteractionRecord,
    PostRecord,
    PostRenderPrompt,
    PromptMessage,
    RenderedPostText,
    UserProfile,
)
from core.ids import new_id


def build_post_render_prompt(
    post: PostRecord,
    *,
    author_profile: UserProfile | None = None,
) -> PostRenderPrompt:
    """Build a chat-style prompt package for one rendered post sidecar."""
    system = PromptMessage(
        role="system",
        content=(
            "You write realistic English learning-community posts. "
            "Stay faithful to the structured metadata. "
            "The response structure is enforced by the API, so focus on semantic fidelity and natural writing."
        ),
    )
    user = PromptMessage(
        role="user",
        content=(
            "Render a StudySphere seed post from this structured truth.\n"
            f"topic: {post.topic}\n"
            f"subtopic: {post.subtopic}\n"
            f"format: {post.format}\n"
            f"post_style: {post.post_style}\n"
            f"creator_type: {post.creator_type}\n"
            f"difficulty: {post.difficulty}\n"
            f"study_context: {post.study_context}\n"
            f"utility_style: {post.utility_style}\n"
            f"social_affordance: {post.social_affordance}\n"
            f"goal_relation_type: {post.goal_relation_type}\n"
            f"{_format_author_persona(author_profile)}\n"
            f"{_format_post_length_guidance(post)}\n"
            "Constraints:\n"
            "- Keep the text consistent with the topic and difficulty.\n"
            "- Do not mention events that did not happen.\n"
            "- Avoid generic filler.\n"
            "- Let the writing style reflect the author persona when provided.\n"
        ),
    )
    return PostRenderPrompt(
        prompt_id=new_id("pp"),
        post_id=post.post_id,
        topic=post.topic,
        subtopic=post.subtopic,
        content_format=post.format,
        post_style=post.post_style,
        goal_relation_type=post.goal_relation_type,
        difficulty=post.difficulty,
        messages=[system, user],
    )


def build_comment_render_prompt(
    post: PostRecord,
    *,
    rendered_post: RenderedPostText | None,
    comment_targets: list[CommentRenderTarget],
) -> CommentSetRenderPrompt:
    """Build a chat-style prompt package for one post-level comment set."""
    system = PromptMessage(
        role="system",
        content=(
            "You write short, realistic English comments for a study-focused social product. "
            "Each comment should react to the target post and loosely reflect the assigned commenter persona. "
            "The response structure is enforced by the API, so focus on semantic fidelity and natural writing."
        ),
    )
    user = PromptMessage(
        role="user",
        content=(
            "Render a StudySphere comment set from this structured truth.\n"
            f"topic: {post.topic}\n"
            f"subtopic: {post.subtopic}\n"
            f"post_format: {post.format}\n"
            f"post_style: {post.post_style}\n"
            f"post_difficulty: {post.difficulty}\n"
            f"study_context: {post.study_context}\n"
            f"goal_relation_type: {post.goal_relation_type}\n"
            f"{_format_target_post(rendered_post, post)}\n"
            f"{_format_comment_targets(comment_targets)}\n"
            f"{_format_comment_length_guidance()}\n"
            "Constraints:\n"
            "- Produce one comment for each listed interaction_id.\n"
            "- Sound like real peer responses.\n"
            "- Stay aligned with the topic.\n"
            "- React to the actual post content, not just the metadata.\n"
            "- Let each tone loosely reflect the matching commenter persona.\n"
            "- Avoid near-duplicate comments within the set.\n"
            "- No emojis.\n"
        ),
    )
    return CommentSetRenderPrompt(
        prompt_id=new_id("cp"),
        post_id=post.post_id,
        topic=post.topic,
        subtopic=post.subtopic,
        post_format=post.format,
        post_style=post.post_style,
        goal_relation_type=post.goal_relation_type,
        comment_targets=comment_targets,
        messages=[system, user],
    )


def _format_author_persona(author_profile: UserProfile | None) -> str:
    """Render a compact author-persona block for post generation."""
    if author_profile is None:
        return "author_persona: unknown"
    return (
        "author_persona:\n"
        f"- primary_interest: {author_profile.primary_interest}\n"
        f"- secondary_interests: {', '.join(author_profile.secondary_interests) or 'none'}\n"
        f"- learning_intensity: {author_profile.learning_intensity}\n"
        f"- posting_tendency: {author_profile.posting_tendency}\n"
        f"- writing_style_family: {author_profile.writing_style_family}\n"
        f"- register_level: {author_profile.register_level}\n"
        f"- curiosity_level: {author_profile.curiosity_level}\n"
        f"- diligence_level: {author_profile.diligence_level}\n"
        f"- social_affinity: {author_profile.social_affinity}"
    )


def build_comment_render_target(
    interaction: InteractionRecord,
    commenter_profile: UserProfile | None,
) -> CommentRenderTarget:
    """Build one lightweight commenter persona block for grouped comment rendering."""
    if commenter_profile is None:
        return CommentRenderTarget(
            interaction_id=interaction.interaction_id,
            user_id=interaction.user_id,
            interaction_type=interaction.event_type,
            primary_interest="unknown",
            interaction_tendency="unknown",
            writing_style_family="concise",
            register_level="plain",
            curiosity_level=0.5,
            social_affinity=0.5,
            exploration_rate=0.1,
            reply_to_interaction_id=interaction.reply_to_interaction_id,
            thread_depth=interaction.thread_depth,
            reply_delay_seconds=interaction.reply_delay_seconds,
        )
    return CommentRenderTarget(
        interaction_id=interaction.interaction_id,
        user_id=interaction.user_id,
        interaction_type=interaction.event_type,
        primary_interest=commenter_profile.primary_interest,
        interaction_tendency=commenter_profile.interaction_tendency,
        writing_style_family=commenter_profile.writing_style_family,
        register_level=commenter_profile.register_level,
        curiosity_level=commenter_profile.curiosity_level,
        social_affinity=commenter_profile.social_affinity,
        exploration_rate=commenter_profile.exploration_rate,
        reply_to_interaction_id=interaction.reply_to_interaction_id,
        thread_depth=interaction.thread_depth,
        reply_delay_seconds=interaction.reply_delay_seconds,
    )


def _format_comment_targets(comment_targets: list[CommentRenderTarget]) -> str:
    """Render grouped comment targets and personas into the prompt."""
    lines = ["comment_targets:"]
    for target in comment_targets:
        lines.append(f"- interaction_id: {target.interaction_id}")
        lines.append(f"  user_id: {target.user_id}")
        lines.append(f"  interaction_type: {target.interaction_type}")
        lines.append(f"  primary_interest: {target.primary_interest}")
        lines.append(f"  interaction_tendency: {target.interaction_tendency}")
        lines.append(f"  writing_style_family: {target.writing_style_family}")
        lines.append(f"  register_level: {target.register_level}")
        lines.append(f"  curiosity_level: {target.curiosity_level}")
        lines.append(f"  social_affinity: {target.social_affinity}")
        lines.append(f"  exploration_rate: {target.exploration_rate}")
        if target.reply_to_interaction_id is not None:
            lines.append(f"  reply_to_interaction_id: {target.reply_to_interaction_id}")
        if target.thread_depth is not None:
            lines.append(f"  thread_depth: {target.thread_depth}")
        if target.reply_delay_seconds is not None:
            lines.append(f"  reply_delay_seconds: {target.reply_delay_seconds}")
    return "\n".join(lines)


def _format_target_post(rendered_post: RenderedPostText | None, post: PostRecord) -> str:
    """Render the concrete post content that a comment should respond to."""
    if rendered_post is not None:
        return (
            "target_post_text:\n"
            f"- title: {rendered_post.title}\n"
            f"- content: {rendered_post.content}"
        )
    return (
        "target_post_text:\n"
        f"- title: unavailable\n"
        f"- content_summary: {post.topic} / {post.subtopic} / {post.format}"
    )


def _format_post_length_guidance(post: PostRecord) -> str:
    """Return approximate title/body length guidance by post format."""
    body_words = {
        "short_post": "60-110 words",
        "qa_post": "70-130 words",
        "experience_post": "120-220 words",
        "project_log": "140-260 words",
        "resource_post": "90-170 words",
        "study_note": "100-180 words",
        "reflection_post": "110-200 words",
    }.get(post.format, "90-160 words")
    return (
        "length_guidance:\n"
        "- title: 6-14 words\n"
        f"- content: {body_words}"
    )


def _format_comment_length_guidance() -> str:
    """Return approximate length guidance for generated comments."""
    return (
        "length_guidance:\n"
        "- comment: 12-40 words"
    )
