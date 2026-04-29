"""Shared math and read helpers for offline feature jobs."""

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Dict, Iterable, List, Tuple

from psycopg import Connection


InteractionMap = Dict[str, Dict[str, float]]


def fetch_recent_interest_rows(connection: Connection, *, lookback_days: int = 90) -> list[dict]:
    """Aggregate recent ETL behavior events into user-item interest scores."""
    query = """
    WITH recent_events AS (
        SELECT
            e.user_id,
            e.post_id,
            CASE
                WHEN e.event_type = 'POST_CREATED' THEN 2.0
                WHEN e.event_type = 'POST_VIEWED' THEN GREATEST(COALESCE(e.dwell_ms, 0) / 12000.0, 0.2)
                WHEN e.event_type = 'POST_LIKED' THEN 1.5
                WHEN e.event_type = 'POST_SAVED' THEN 2.0
                WHEN e.event_type = 'COMMENT_CREATED' THEN 1.7
                ELSE 0.4
            END * EXP(
                -EXTRACT(EPOCH FROM (NOW() - COALESCE(e.processed_at, NOW()))) / 86400.0 / 30.0
            ) AS weighted_score
        FROM etl_behavior_events e
        WHERE e.post_id IS NOT NULL
          AND e.user_id IS NOT NULL
          AND COALESCE(e.processed_at, NOW()) > NOW() - (%s::text || ' days')::interval
          AND e.event_type IN (
              'POST_CREATED',
              'POST_VIEWED',
              'POST_LIKED',
              'POST_SAVED',
              'COMMENT_CREATED'
          )
    )
    SELECT user_id, post_id, SUM(weighted_score)::float8 AS interest_score
    FROM recent_events
    GROUP BY user_id, post_id
    HAVING SUM(weighted_score) > 0
    """

    with connection.cursor() as cursor:
        cursor.execute(query, (lookback_days,))
        return cursor.fetchall()


def build_user_item_map(rows: Iterable[dict]) -> InteractionMap:
    """Build sparse user-item vectors from interest rows."""
    interaction_map: InteractionMap = defaultdict(dict)
    for row in rows:
        interaction_map[str(row["user_id"])][str(row["post_id"])] = float(
            row.get("interest_score", row.get("weight", 0.0))
        )
    return dict(interaction_map)


def invert_interactions(user_item_map: InteractionMap) -> InteractionMap:
    """Invert sparse vectors from user->item into item->user orientation."""
    item_user_map: InteractionMap = defaultdict(dict)
    for user_id, items in user_item_map.items():
        for item_id, weight in items.items():
            item_user_map[item_id][user_id] = weight
    return dict(item_user_map)


def cosine_sparse(left: Dict[str, float], right: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""
    if not left or not right:
        return 0.0

    common_keys = set(left).intersection(right)
    if not common_keys:
        return 0.0

    dot = sum(left[key] * right[key] for key in common_keys)
    left_norm = sqrt(sum(value * value for value in left.values()))
    right_norm = sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def top_k_similarities(
    source_vectors: InteractionMap,
    top_k: int,
) -> Dict[str, List[Tuple[str, float]]]:
    """Return bounded symmetric top-k cosine neighbors for each source vector."""
    keys = list(source_vectors)
    results: Dict[str, List[Tuple[str, float]]] = {}

    for index, source_id in enumerate(keys):
        source_vector = source_vectors[source_id]
        scored: List[Tuple[str, float]] = []
        for other_id in keys[index + 1 :]:
            score = cosine_sparse(source_vector, source_vectors[other_id])
            if score <= 0:
                continue
            scored.append((other_id, score))
            results.setdefault(other_id, []).append((source_id, score))

        existing = results.setdefault(source_id, [])
        existing.extend(scored)

    for source_id, scored in results.items():
        scored.sort(key=lambda item: item[1], reverse=True)
        results[source_id] = scored[:top_k]

    return results

