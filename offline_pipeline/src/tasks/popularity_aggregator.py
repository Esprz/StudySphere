"""Trending/popularity build and Redis push."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from psycopg import Connection

from ..feature_store import FeatureStore, TRENDING_FEATURE_NAME


class PopularityAggregatorTask:
    """Compute time-bounded popularity and activate a fresh trending version."""

    def __init__(
        self,
        connection: Connection,
        feature_store: FeatureStore,
        cache,
        *,
        limit: int = 50,
        lookback_hours: int = 24,
    ) -> None:
        self.connection = connection
        self.feature_store = feature_store
        self.cache = cache
        self.limit = limit
        self.lookback_hours = lookback_hours

    def run(self) -> dict[str, Any]:
        """Compute `item_popularity`, versioned `trending_items`, and `rec:trending`."""
        self.feature_store.ensure_runtime_schema()
        self.feature_store.apply_runtime_resource_limits()
        computed_at = datetime.now(timezone.utc)
        version = self.feature_store.create_version_tag(
            TRENDING_FEATURE_NAME,
            computed_at=computed_at,
        )

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                WITH recent_events AS (
                    SELECT
                        post_id,
                        CASE
                            WHEN event_type = 'POST_VIEWED' THEN GREATEST(COALESCE(dwell_ms, 0) / 15000.0, 0.1)
                            WHEN event_type = 'POST_LIKED' THEN 2.0
                            WHEN event_type = 'POST_SAVED' THEN 2.5
                            WHEN event_type = 'COMMENT_CREATED' THEN 1.6
                            WHEN event_type = 'POST_CREATED' THEN 1.2
                            ELSE 0.2
                        END * EXP(
                            -EXTRACT(EPOCH FROM (NOW() - COALESCE(processed_at, NOW()))) / 3600.0 / 12.0
                        ) AS score
                    FROM etl_behavior_events
                    WHERE post_id IS NOT NULL
                      AND COALESCE(processed_at, NOW()) > NOW() - (%s::text || ' hours')::interval
                      AND event_type IN (
                          'POST_CREATED',
                          'POST_VIEWED',
                          'POST_LIKED',
                          'POST_SAVED',
                          'COMMENT_CREATED'
                      )
                ),
                ranked AS (
                    SELECT
                        post_id,
                        SUM(score)::float8 AS popularity,
                        ROW_NUMBER() OVER (
                            ORDER BY SUM(score) DESC, post_id ASC
                        ) AS rank
                    FROM recent_events
                    GROUP BY post_id
                )
                SELECT post_id, popularity, rank
                FROM ranked
                WHERE rank <= %s
                ORDER BY rank ASC
                """,
                (self.lookback_hours, max(self.limit, 200)),
            )
            rows = cursor.fetchall()

        current_at = computed_at.replace(tzinfo=None)
        popularity_rows = [(str(row["post_id"]), int(round(float(row["popularity"]))), current_at) for row in rows]
        trending_rows = [
            (
                str(row["post_id"]),
                float(row["popularity"]),
                version,
                int(row["rank"]),
                current_at,
            )
            for row in rows
        ]
        with self.connection.cursor() as cursor:
            if popularity_rows:
                cursor.executemany(
                    """
                    INSERT INTO item_popularity (item_id, popularity, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (item_id)
                    DO UPDATE SET
                        popularity = EXCLUDED.popularity,
                        updated_at = EXCLUDED.updated_at
                    """,
                    popularity_rows,
                )
            if trending_rows:
                cursor.executemany(
                    """
                    INSERT INTO trending_items (
                        item_id,
                        popularity,
                        version,
                        rank,
                        updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    trending_rows,
                )
        self.connection.commit()

        cutover = self.feature_store.activate_version(
            feature_name=TRENDING_FEATURE_NAME,
            version=version,
            row_count=len(trending_rows),
            computed_at=computed_at,
        )
        self.cache.set_json(
            "rec:trending",
            [row[0] for row in trending_rows[: self.limit]],
            ttl_seconds=3600,
        )
        return {
            "job": "popularity-aggregator",
            "version": version,
            "row_count": len(trending_rows),
            "previous_version": cutover.previous_version,
            "redis_key": "rec:trending",
        }
