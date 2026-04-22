"""State seeding and updates for simulator simulator."""

from __future__ import annotations

from config.models import PostRecord, UserGoal, UserProfile


def seed_user_memory(
    users: list[UserProfile],
    goals_by_user: dict[str, list[UserGoal]],
) -> dict[str, dict]:
    memory: dict[str, dict] = {}
    for user in users:
        memory[user.user_id] = {
            "active_goals": goals_by_user.get(user.user_id, []),
            "completed_goals": [],
            "recent_sessions": [],
            "recent_topics_viewed": [],
            "recent_topics_hidden": [],
            "recent_authors_followed": [],
            "fatigue_carryover": 0.0,
        }
    return memory


def seed_content_memory(posts: list[PostRecord]) -> dict[str, dict]:
    memory: dict[str, dict] = {}
    for post in posts:
        memory[post.post_id] = {
            "true_latent_quality": post.true_latent_quality,
            "observed_quality": post.observed_quality,
            "exposure_count": 0,
            "view_count": 0,
            "like_count": 0,
            "save_count": 0,
            "comment_count": 0,
            "hide_count": 0,
        }
    return memory


def initialize_follow_graph(users: list[UserProfile]) -> dict[str, set[str]]:
    return {user.user_id: set() for user in users}
