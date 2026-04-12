"""Trending batch job."""

from __future__ import annotations

from typing import Any, Dict

from .base import OfflineJob


class TrendingJob(OfflineJob):
    name = "trending"

    def __init__(self, connection, cache, limit: int):
        self.connection = connection
        self.cache = cache
        self.limit = limit

    def run(self) -> Dict[str, Any]:
        query = """
        WITH recent_posts AS (
            SELECT p.post_id,
                   p.created_at,
                   EXTRACT(EPOCH FROM (NOW() - p.created_at)) / 3600.0 AS hours_old
            FROM "Post" p
        ),
        likes AS (
            SELECT post_id, COUNT(*)::float8 AS cnt
            FROM "Like"
            GROUP BY post_id
        ),
        saves AS (
            SELECT post_id, COUNT(*)::float8 AS cnt
            FROM "Save"
            GROUP BY post_id
        ),
        comments AS (
            SELECT post_id, COUNT(*)::float8 AS cnt
            FROM "Comment"
            GROUP BY post_id
        )
        SELECT rp.post_id,
               (
                   COALESCE(l.cnt, 0) * 2.0 +
                   COALESCE(s.cnt, 0) * 2.5 +
                   COALESCE(c.cnt, 0) * 1.5 +
                   GREATEST(48.0 - COALESCE(rp.hours_old, 48.0), 0) / 48.0
               ) AS score
        FROM recent_posts rp
        LEFT JOIN likes l ON l.post_id = rp.post_id
        LEFT JOIN saves s ON s.post_id = rp.post_id
        LEFT JOIN comments c ON c.post_id = rp.post_id
        ORDER BY score DESC, rp.created_at DESC
        LIMIT %s
        """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (self.limit,))
            rows = cursor.fetchall()

        payload = [
            {"post_id": row["post_id"], "score": float(row["score"]), "source": "offline_trending"}
            for row in rows
        ]
        self.cache.set_json("offline:trending:global", payload, ttl_seconds=3600)
        return {"job": self.name, "count": len(payload)}

