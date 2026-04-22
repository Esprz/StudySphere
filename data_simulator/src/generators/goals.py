"""Goal generation for simulator v2 Phase 1."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from config.models import SourceBundle, UserGoal, UserProfile
from core.ids import new_id
from core.time import clip_0_1


def generate_initial_goals(
    users: list[UserProfile],
    sources: SourceBundle,
    rng: random.Random,
    *,
    now: datetime | None = None,
) -> dict[str, list[UserGoal]]:
    now_utc = now or datetime.now(timezone.utc)
    goal_categories = sources.require("goal_taxonomy").get("categories", [])
    goal_interest_bridge = sources.require("goal_interest_bridge").get("mappings", [])
    interest_to_category = _build_interest_to_category_lookup(sources)
    category_weights_lookup = {
        str(item["goal_category"]): dict(item.get("interest_category_weights", {}))
        for item in goal_interest_bridge
    }

    goals_by_user: dict[str, list[UserGoal]] = {}
    for user in users:
        user_interest_category = interest_to_category.get(user.primary_interest)
        goal_count = _sample_goal_count(user.learning_intensity, rng)

        user_goals: list[UserGoal] = []
        for _ in range(goal_count):
            goal_category_entry = _sample_goal_category(
                goal_categories,
                category_weights_lookup,
                user_interest_category,
                rng,
            )
            goal_category_name = str(goal_category_entry["category"])
            goal_type = str(rng.choice(goal_category_entry.get("goals", [])))
            related_topics = _sample_related_topics(user, rng)
            priority = _sample_goal_priority(user, rng)
            strength = _sample_goal_strength(user, rng)
            start_at = now_utc - timedelta(days=rng.randint(0, 10))
            end_at = start_at + timedelta(days=rng.randint(30, 120))

            user_goals.append(
                UserGoal(
                    goal_id=new_id("g", rng=rng),
                    user_id=user.user_id,
                    goal_category=goal_category_name,
                    goal_type=goal_type,
                    related_topics=related_topics,
                    priority=priority,
                    strength=strength,
                    progress_state="active",
                    start_at=start_at,
                    end_at=end_at,
                )
            )

        goals_by_user[user.user_id] = user_goals
    return goals_by_user


def select_active_goal(user: UserProfile, user_goals: list[UserGoal], now: datetime) -> UserGoal:
    valid = [goal for goal in user_goals if goal.progress_state == "active" and goal.start_at <= now <= goal.end_at]
    if not valid:
        valid = [goal for goal in user_goals if goal.progress_state == "active"] or user_goals
    return max(valid, key=lambda g: (g.priority, g.strength))


def maybe_generate_replacement_goal(
    user: UserProfile,
    sources: SourceBundle,
    rng: random.Random,
    *,
    now: datetime,
) -> UserGoal:
    generated = generate_initial_goals([user], sources, rng, now=now)
    return generated[user.user_id][0]


def _sample_goal_count(learning_intensity: str, rng: random.Random) -> int:
    if learning_intensity == "light":
        return 1
    if learning_intensity == "medium":
        return rng.choice((1, 2))
    return rng.choice((2, 3))


def _sample_goal_category(
    categories: list[dict],
    category_weights_lookup: dict[str, dict[str, float]],
    user_interest_category: str | None,
    rng: random.Random,
) -> dict:
    if not categories:
        raise ValueError("No goal categories found")

    if not user_interest_category:
        return rng.choice(categories)

    weights: list[float] = []
    for category in categories:
        category_name = str(category["category"])
        interest_weights = category_weights_lookup.get(category_name, {})
        weights.append(float(interest_weights.get(user_interest_category, 0.05)))
    return _weighted_choice(categories, weights, rng)


def _sample_related_topics(user: UserProfile, rng: random.Random) -> list[str]:
    topics = [user.primary_interest]
    if user.secondary_interests:
        topics.append(rng.choice(user.secondary_interests))
    return list(dict.fromkeys(topics))


def _sample_goal_priority(user: UserProfile, rng: random.Random) -> float:
    base = 0.45 * user.diligence_level + 0.35 * user.curiosity_level + 0.10
    noisy = base + rng.uniform(-0.15, 0.15)
    return round(clip_0_1(noisy), 4)


def _sample_goal_strength(user: UserProfile, rng: random.Random) -> float:
    base = 0.50 * user.diligence_level + 0.30 * (1.0 - user.drift_rate) + 0.10
    noisy = base + rng.uniform(-0.12, 0.12)
    return round(clip_0_1(noisy), 4)


def _build_interest_to_category_lookup(sources: SourceBundle) -> dict[str, str]:
    taxonomy = sources.require("interest_taxonomy")
    lookup: dict[str, str] = {}
    for category in taxonomy.get("categories", []):
        category_name = str(category.get("category"))
        for theme in category.get("themes", []):
            label = theme.get("label")
            if label:
                lookup[str(label)] = category_name
    return lookup


def _weighted_choice(items: list[dict], weights: list[float], rng: random.Random) -> dict:
    total = sum(max(0.0, w) for w in weights)
    if total <= 0:
        return rng.choice(items)

    threshold = rng.uniform(0.0, total)
    running = 0.0
    for item, weight in zip(items, weights):
        running += max(0.0, weight)
        if threshold <= running:
            return item
    return items[-1]
