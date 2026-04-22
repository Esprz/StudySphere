"""Content generation for simulator v2 Phase 1."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from config.models import PostRecord, SourceBundle, UserProfile
from core.ids import new_id
from core.time import clip_0_1


def generate_initial_content(
    users: list[UserProfile],
    sources: SourceBundle,
    rng: random.Random,
    *,
    now: datetime | None = None,
) -> list[PostRecord]:
    now_utc = now or datetime.now(timezone.utc)
    content_taxonomy = sources.require("content_taxonomy")
    formats = list(content_taxonomy.get("formats", []))
    creator_types = list(content_taxonomy.get("creator_types", []))
    difficulty_levels = [int(x) for x in content_taxonomy.get("difficulty_levels", [1, 2, 3, 4, 5])]
    study_contexts = list(content_taxonomy.get("study_contexts", []))
    utility_styles = list(content_taxonomy.get("utility_styles", []))
    social_affordances = list(content_taxonomy.get("social_affordances", []))

    theme_to_formats = _theme_format_preferences(sources)
    posts: list[PostRecord] = []
    for user in users:
        post_count = _sample_post_count(user.posting_tendency, rng)
        for _ in range(post_count):
            topic = _sample_post_topic(user, rng)
            preferred_formats = theme_to_formats.get(topic, formats)
            content_format = rng.choice(preferred_formats or formats)
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
                    creator_type=rng.choice(creator_types),
                    difficulty=rng.choice(difficulty_levels),
                    true_latent_quality=true_quality,
                    observed_quality=observed_quality,
                    freshness_hours=freshness_hours,
                    study_context=rng.choice(study_contexts),
                    utility_style=rng.choice(utility_styles),
                    social_affordance=rng.choice(social_affordances),
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
    return generate_initial_content(selected_authors, sources, rng, now=time_tick)


def _sample_post_count(posting_tendency: str, rng: random.Random) -> int:
    if posting_tendency == "low":
        return rng.randint(2, 4)
    if posting_tendency == "medium":
        return rng.randint(4, 7)
    return rng.randint(7, 10)


def _sample_post_topic(user: UserProfile, rng: random.Random) -> str:
    exploration_roll = rng.random()
    if exploration_roll < 0.65:
        return user.primary_interest
    if exploration_roll < 0.90 and user.secondary_interests:
        return rng.choice(user.secondary_interests)

    pool = [user.primary_interest, *user.secondary_interests]
    if not pool:
        return user.primary_interest
    return rng.choice(pool)


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
