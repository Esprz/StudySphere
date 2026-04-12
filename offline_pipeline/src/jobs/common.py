"""Shared utilities for offline recommendation jobs."""

from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Dict, Iterable, List, Tuple

from psycopg import Connection


InteractionMap = Dict[str, Dict[str, float]]


def fetch_interactions(connection: Connection) -> list[dict]:
    query = """
    WITH weighted_events AS (
        SELECT l.user_id, l.post_id, 1.0::float8 AS weight
        FROM "Like" l
        UNION ALL
        SELECT s.user_id, s.post_id, 1.5::float8 AS weight
        FROM "Save" s
        UNION ALL
        SELECT c.user_id, c.post_id, 1.2::float8 AS weight
        FROM "Comment" c
        UNION ALL
        SELECT e.user_id, e.post_id,
               CASE
                   WHEN e.event_type = 'POST_CREATED' THEN 2.0
                   WHEN e.event_type = 'POST_VIEWED' THEN GREATEST(COALESCE(e.dwell_ms, 0) / 10000.0, 0.2)
                   ELSE 0.5
               END AS weight
        FROM etl_behavior_events e
        WHERE e.post_id IS NOT NULL
          AND e.event_type IN ('POST_CREATED', 'POST_VIEWED', 'POST_LIKED', 'POST_SAVED', 'COMMENT_CREATED')
    )
    SELECT user_id, post_id, SUM(weight) AS weight
    FROM weighted_events
    GROUP BY user_id, post_id
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def build_user_item_map(rows: Iterable[dict]) -> InteractionMap:
    interaction_map: InteractionMap = defaultdict(dict)
    for row in rows:
        interaction_map[row["user_id"]][row["post_id"]] = float(row["weight"])
    return dict(interaction_map)


def invert_interactions(user_item_map: InteractionMap) -> InteractionMap:
    item_user_map: InteractionMap = defaultdict(dict)
    for user_id, items in user_item_map.items():
        for item_id, weight in items.items():
            item_user_map[item_id][user_id] = weight
    return dict(item_user_map)


def cosine_sparse(left: Dict[str, float], right: Dict[str, float]) -> float:
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

