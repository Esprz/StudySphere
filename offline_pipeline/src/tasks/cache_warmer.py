"""Warm recommendation cache from active DB feature versions."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from psycopg import Connection

from ..feature_store import CF_FEATURE_NAME, FeatureStore


class CacheWarmerTask:
    """Warm `rec:feed:{user_id}` from active CF features with trending fallback."""

    def __init__(
        self,
        connection: Connection,
        feature_store: FeatureStore,
        cache,
        *,
        user_limit: int = 100,
        feed_limit: int = 50,
    ) -> None:
        self.connection = connection
        self.feature_store = feature_store
        self.cache = cache
        self.user_limit = user_limit
        self.feed_limit = feed_limit

    def run(self) -> dict[str, Any]:
        """Warm cache for the most active recent users."""
        cf_version = self.feature_store.get_active_version(CF_FEATURE_NAME)
        if not cf_version:
            return {"job": "cache-warmer", "count": 0, "status": "skipped_missing_cf_version"}

        trending_ids = self.cache.get_json("rec:trending") or []
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, COUNT(*) AS event_count
                FROM etl_behavior_events
                WHERE COALESCE(processed_at, NOW()) > NOW() - INTERVAL '7 days'
                GROUP BY user_id
                ORDER BY event_count DESC, user_id ASC
                LIMIT %s
                """,
                (self.user_limit,),
            )
            active_users = cursor.fetchall()

        warmed = 0
        for row in active_users:
            user_id = str(row["user_id"])
            payload = self._build_feed_for_user(user_id, cf_version, trending_ids)
            if payload:
                self.cache.set_json(f"rec:feed:{user_id}", payload, ttl_seconds=3600)
                warmed += 1

        return {"job": "cache-warmer", "count": warmed, "cf_version": cf_version}

    def _build_feed_for_user(self, user_id: str, version: str, trending_ids: list[str]) -> list[dict[str, Any]]:
        """Build one cached feed using top interested items and item-item neighbors."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT item_id, interest_score
                FROM user_item_interest
                WHERE user_id = %s AND version = %s
                """,
                (user_id, version),
            )
            seen_rows = cursor.fetchall()
            cursor.execute(
                """
                SELECT item_id, interest_score
                FROM user_interested_items
                WHERE user_id = %s AND version = %s
                ORDER BY rank ASC
                LIMIT 20
                """,
                (user_id, version),
            )
            seed_rows = cursor.fetchall()

        seen_ids = {str(row["item_id"]) for row in seen_rows}
        scores: dict[str, float] = defaultdict(float)
        for seed_row in seed_rows:
            item_id = str(seed_row["item_id"])
            interest = float(seed_row["interest_score"])
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT similar_item_id, similarity_score
                    FROM item_similar_items
                    WHERE item_id = %s AND version = %s
                    ORDER BY rank ASC
                    LIMIT 5
                    """,
                    (item_id, version),
                )
                similar_rows = cursor.fetchall()
            for similar_row in similar_rows:
                candidate_id = str(similar_row["similar_item_id"])
                if candidate_id in seen_ids:
                    continue
                scores[candidate_id] += interest * float(similar_row["similarity_score"])

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        payload = [
            {"post_id": post_id, "score": float(score), "source": "offline_cf"}
            for post_id, score in ranked[: self.feed_limit]
        ]
        if payload:
            return payload
        return [
            {"post_id": post_id, "score": float(self.feed_limit - index), "source": "trending_fallback"}
            for index, post_id in enumerate(trending_ids[: self.feed_limit])
        ]

