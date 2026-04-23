"""Content generation for simulator v2 Phase 1."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from config.models import PostRecord, SourceBundle, UserGoal, UserProfile
from core.ids import new_id
from core.time import clip_0_1


def generate_initial_content(
    users: list[UserProfile],
    sources: SourceBundle,
    rng: random.Random,
    *,
    now: datetime | None = None,
    goals_by_user: dict[str, list[UserGoal]] | None = None,
) -> list[PostRecord]:
    now_utc = now or datetime.now(timezone.utc)
    content_taxonomy = sources.require("content_taxonomy")
    formats = list(content_taxonomy.get("formats", []))
    post_styles = list(content_taxonomy.get("post_styles", []))
    goal_relation_types = list(content_taxonomy.get("goal_relation_types", []))
    goal_relation_sampling = dict(content_taxonomy.get("goal_relation_sampling", {}))
    post_style_by_goal_relation = dict(content_taxonomy.get("post_style_by_goal_relation", {}))
    creator_types = list(content_taxonomy.get("creator_types", []))
    difficulty_levels = [int(x) for x in content_taxonomy.get("difficulty_levels", [1, 2, 3, 4, 5])]
    study_contexts = list(content_taxonomy.get("study_contexts", []))
    utility_styles = list(content_taxonomy.get("utility_styles", []))
    social_affordances = list(content_taxonomy.get("social_affordances", []))

    theme_to_formats = _theme_format_preferences(sources)
    all_themes = _all_interest_themes(sources)
    posts: list[PostRecord] = []
    for user in users:
        post_count = _sample_post_count(user.posting_tendency, rng)
        user_goals = [] if goals_by_user is None else list(goals_by_user.get(user.user_id, []))
        for _ in range(post_count):
            goal_relation_type = _sample_goal_relation_type(
                user=user,
                user_goals=user_goals,
                goal_relation_types=goal_relation_types,
                sampling_config=goal_relation_sampling,
                rng=rng,
            )
            topic = _sample_post_topic(user, user_goals, all_themes, goal_relation_type, rng)
            preferred_formats = theme_to_formats.get(topic, formats)
            content_format = rng.choice(preferred_formats or formats)
            post_style = _sample_post_style(
                post_styles=post_styles,
                goal_relation_type=goal_relation_type,
                style_by_relation=post_style_by_goal_relation,
                rng=rng,
            )
            freshness_hours = rng.randint(0, 24 * 14)
            true_quality = round(rng.betavariate(2, 5), 4)
            observed_quality = round(
                clip_0_1(true_quality + rng.uniform(-0.15, 0.15)),
                4,
            )

            posts.append(
                PostRecord(
                    post_id=new_id("p", rng=rng),
                    author_id=user.user_id,
                    topic=topic,
                    subtopic=_sample_subtopic(topic, rng),
                    format=content_format,
                    post_style=post_style,
                    creator_type=rng.choice(creator_types),
                    difficulty=rng.choice(difficulty_levels),
                    true_latent_quality=true_quality,
                    observed_quality=observed_quality,
                    freshness_hours=freshness_hours,
                    study_context=rng.choice(study_contexts),
                    utility_style=rng.choice(utility_styles),
                    social_affordance=rng.choice(social_affordances),
                    goal_relation_type=goal_relation_type,
                    created_at=now_utc - timedelta(hours=freshness_hours),
                )
            )
    return posts


def maybe_inject_new_content(
    time_tick: datetime,
    users: list[UserProfile],
    world_state: Any,
    global_time_context: Any,
    rng: random.Random,
    *,
    max_injected_posts: int = 3,
) -> list[PostRecord]:
    if not users:
        return []

    injected_count = rng.randint(0, max_injected_posts)
    if injected_count == 0:
        return []

    selected_authors = [rng.choice(users) for _ in range(injected_count)]
    sources = world_state.sources if hasattr(world_state, "sources") else None
    if sources is None:
        return []
    goals_by_user = world_state.goals_by_user if hasattr(world_state, "goals_by_user") else None
    return generate_initial_content(
        selected_authors,
        sources,
        rng,
        now=time_tick,
        goals_by_user=goals_by_user,
    )


def _sample_post_count(posting_tendency: str, rng: random.Random) -> int:
    if posting_tendency == "low":
        return rng.randint(2, 4)
    if posting_tendency == "medium":
        return rng.randint(4, 7)
    return rng.randint(7, 10)


def _sample_post_topic(
    user: UserProfile,
    user_goals: list[UserGoal],
    all_themes: list[str],
    goal_relation_type: str,
    rng: random.Random,
) -> str:
    goal_topics = _goal_topics(user_goals)
    interest_topics = [user.primary_interest, *user.secondary_interests]
    interest_topics = [topic for topic in interest_topics if topic]

    if goal_relation_type == "on_goal" and goal_topics:
        return rng.choice(goal_topics)

    if goal_relation_type == "interest_adjacent":
        pool = [*goal_topics, *interest_topics]
        if pool:
            return rng.choice(pool)

    if goal_relation_type == "off_topic_noise":
        excluded = set(goal_topics) | set(interest_topics)
        off_topic_pool = [theme for theme in all_themes if theme not in excluded]
        if off_topic_pool:
            return rng.choice(off_topic_pool)

    fallback_pool = [*goal_topics, *interest_topics]
    if fallback_pool:
        return rng.choice(fallback_pool)
    return rng.choice(all_themes)


def _sample_goal_relation_type(
    user: UserProfile,
    user_goals: list[UserGoal],
    goal_relation_types: list[str],
    sampling_config: dict[str, object],
    rng: random.Random,
) -> str:
    allowed = set(goal_relation_types or ["on_goal", "interest_adjacent", "off_topic_noise"])
    if not allowed:
        return "on_goal"

    has_goals = bool(_goal_topics(user_goals))
    off_topic_base = float(sampling_config.get("off_topic_base", 0.06))
    off_topic_exploration_weight = float(sampling_config.get("off_topic_exploration_weight", 0.35))
    on_goal_base_with_goals = float(sampling_config.get("on_goal_base_with_goals", 0.66))
    on_goal_exploration_weight = float(sampling_config.get("on_goal_exploration_weight", 0.22))
    on_goal_base_without_goals = float(sampling_config.get("on_goal_base_without_goals", 0.0))

    off_topic_share = clip_0_1(off_topic_base + off_topic_exploration_weight * user.exploration_rate)
    if has_goals:
        on_goal_share = clip_0_1(on_goal_base_with_goals - on_goal_exploration_weight * user.exploration_rate)
    else:
        on_goal_share = clip_0_1(on_goal_base_without_goals)
    adjacent_share = clip_0_1(1.0 - on_goal_share - off_topic_share)

    weighted: list[tuple[str, float]] = []
    if "on_goal" in allowed:
        weighted.append(("on_goal", on_goal_share))
    if "interest_adjacent" in allowed:
        weighted.append(("interest_adjacent", adjacent_share))
    if "off_topic_noise" in allowed:
        weighted.append(("off_topic_noise", off_topic_share))
    weighted = [(label, weight) for label, weight in weighted if weight > 0.0]
    if not weighted:
        return rng.choice(sorted(allowed))

    total = sum(weight for _, weight in weighted)
    roll = rng.random() * total
    cursor = 0.0
    for label, weight in weighted:
        cursor += weight
        if roll <= cursor:
            return label
    return weighted[-1][0]


def _sample_post_style(
    *,
    post_styles: list[str],
    goal_relation_type: str,
    style_by_relation: dict[str, object],
    rng: random.Random,
) -> str:
    if not post_styles:
        return "knowledge_share"

    configured = style_by_relation.get(goal_relation_type)
    if isinstance(configured, list):
        preferred = [str(style) for style in configured if str(style) in post_styles]
    else:
        preferred = []
    if preferred:
        return rng.choice(preferred)

    fallback = [style for style in _default_post_style_map().get(goal_relation_type, []) if style in post_styles]
    preferred = fallback
    return rng.choice(preferred or post_styles)


def _default_post_style_map() -> dict[str, list[str]]:
    return {
        "on_goal": [
            "progress_update",
            "knowledge_share",
            "question_help",
            "build_in_public",
        ],
        "interest_adjacent": [
            "knowledge_share",
            "resource_share",
            "reflection",
            "question_help",
        ],
        "off_topic_noise": [
            "reflection",
            "achievement_update",
            "resource_share",
        ],
    }


def _sample_subtopic(topic: str, rng: random.Random) -> str:
    suffixes = (
        "foundations",
        "case study",
        "debugging",
        "advanced practice",
        "exam strategy",
        "resource breakdown",
    )
    return f"{topic.lower()} {rng.choice(suffixes)}"


def _theme_format_preferences(sources: SourceBundle) -> dict[str, list[str]]:
    mapping = sources.require("topic_activity_bridge").get("mappings", [])
    result: dict[str, list[str]] = {}
    for item in mapping:
        theme = item.get("theme")
        if not theme:
            continue
        formats = [str(f) for f in item.get("preferred_formats", [])]
        result[str(theme)] = formats
    return result


def _all_interest_themes(sources: SourceBundle) -> list[str]:
    taxonomy = sources.require("interest_taxonomy")
    themes: list[str] = []
    for category in taxonomy.get("categories", []):
        for theme in category.get("themes", []):
            label = theme.get("label")
            if label:
                themes.append(str(label))
    if not themes:
        raise ValueError("No themes found in interest taxonomy")
    return themes


def _goal_topics(user_goals: list[UserGoal]) -> list[str]:
    topics: list[str] = []
    for goal in user_goals:
        for topic in goal.related_topics:
            if topic not in topics:
                topics.append(topic)
    return topics
