"""User-user and item-item similarity computation for one CF version."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from psycopg import Connection

from .common import build_user_item_map, invert_interactions, top_k_similarities


class SimilarityBuilderTask:
    """Build sparse cosine similarities and top-k neighbor tables."""

    def __init__(self, connection: Connection, *, top_k: int = 10) -> None:
        self.connection = connection
        self.top_k = top_k

    def run(self, *, version: str) -> dict[str, Any]:
        """Populate versioned user/item similarity tables from user_item_interest."""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, item_id AS post_id, interest_score
                FROM user_item_interest
                WHERE version = %s
                """,
                (version,),
            )
            interest_rows = cursor.fetchall()

        user_map = build_user_item_map(interest_rows)
        item_map = invert_interactions(user_map)
        user_similarities = top_k_similarities(user_map, self.top_k)
        item_similarities = top_k_similarities(item_map, self.top_k)
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)

        user_similarity_rows = []
        user_rank_rows = []
        for user_id, scored in user_similarities.items():
            for rank, (other_id, score) in enumerate(scored, start=1):
                user_similarity_rows.append((user_id, other_id, float(score), version, created_at))
                user_rank_rows.append((user_id, other_id, float(score), rank, version, created_at))

        item_similarity_rows = []
        item_rank_rows = []
        for item_id, scored in item_similarities.items():
            for rank, (other_id, score) in enumerate(scored, start=1):
                item_similarity_rows.append((item_id, other_id, float(score), version, created_at))
                item_rank_rows.append((item_id, other_id, float(score), rank, version, created_at))

        with self.connection.cursor() as cursor:
            if user_similarity_rows:
                cursor.executemany(
                    """
                    INSERT INTO user_user_similarity (
                        userA_id,
                        userB_id,
                        similarity_score,
                        version,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    user_similarity_rows,
                )
                cursor.executemany(
                    """
                    INSERT INTO user_similar_users (
                        user_id,
                        similar_user_id,
                        similarity_score,
                        rank,
                        version,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    user_rank_rows,
                )
            if item_similarity_rows:
                cursor.executemany(
                    """
                    INSERT INTO item_item_similarity (
                        itemA_id,
                        itemB_id,
                        similarity_score,
                        version,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    item_similarity_rows,
                )
                cursor.executemany(
                    """
                    INSERT INTO item_similar_items (
                        item_id,
                        similar_item_id,
                        similarity_score,
                        rank,
                        version,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    item_rank_rows,
                )
        self.connection.commit()

        return {
            "job": "similarity-builder",
            "version": version,
            "user_similarity_row_count": len(user_similarity_rows),
            "user_rank_row_count": len(user_rank_rows),
            "item_similarity_row_count": len(item_similarity_rows),
            "item_rank_row_count": len(item_rank_rows),
        }
