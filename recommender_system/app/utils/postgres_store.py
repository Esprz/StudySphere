import os
import psycopg
from psycopg.rows import dict_row
from typing import List, Dict, Any, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()


class PostgresStore:
    def __init__(self):
        self.db_connection_string = os.getenv("DATABASE_URL")
        # row_factory=dict_row gives you dict-like rows
        self.psycopg_conn = psycopg.connect(
            self.db_connection_string, row_factory=dict_row
        )
        self.psycopg_conn.autocommit = False  # explicit tx control if you want

    def get_session(self) -> psycopg.Connection:
        return self.psycopg_conn

    # ---------- SINGLE-ENTITY QUERIES (fixed to return id + score) ----------

    def get_user_topk_posts(
        self, user_id: str, k: int, version: str = "v1"
    ) -> List[Dict[str, Any]]:
        """
        Return the user's top-K interested posts with scores.
        Output: [{post_id, interest_score, rank}]
        """
        sql = """
            SELECT post_id, interest_score, rank
            FROM user_interested_items
            WHERE user_id = %s AND version = %s
            ORDER BY rank ASC
            LIMIT %s;
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (user_id, version, k))
            rows = cur.fetchall()  # list of dicts
        # keep shape consistent
        return rows

    def get_user_topk_neighbors(
        self, user_id: str, k: int, version: str = "v1"
    ) -> List[Dict[str, Any]]:
        """
        Return the user's top-K similar users with scores.
        Output: [{similar_user_id, similarity_score, rank}]
        """
        sql = """
            SELECT similar_user_id, similarity_score, rank
            FROM user_similar_users
            WHERE user_id = %s AND version = %s
            ORDER BY rank ASC
            LIMIT %s;
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (user_id, version, k))
            rows = cur.fetchall()
        return rows

    def get_item_topk_similar_items(
        self, item_id: str, k: int, version: str = "v1"
    ) -> List[Dict[str, Any]]:
        """
        Return an item's top-K similar items with scores.
        Output: [{similar_item_id, similarity_score, rank}]
        """
        sql = """
            SELECT similar_item_id, similarity_score, rank
            FROM item_similar_items
            WHERE item_id = %s AND version = %s
            ORDER BY rank ASC
            LIMIT %s;
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (item_id, version, k))
            rows = cur.fetchall()
        return rows

    # ---------- BATCH QUERIES (avoid N+1 in recall) ----------

    def get_items_topk_similar_items(
        self, seed_item_ids: List[str], per_seed_k: int, version: str = "v1"
    ) -> List[Dict[str, Any]]:
        """
        Batch: for many seeds, fetch each seed's top-K similar items.
        Output rows: [{seed_item_id, similar_item_id, similarity_score, rank}]
        """
        if not seed_item_ids:
            return []

        sql = """
            WITH seeds(item_id) AS (
                SELECT UNNEST(%s::text[])
            ),
            ranked AS (
                SELECT
                    i.item_id           AS seed_item_id,
                    i.similar_item_id   AS similar_item_id,
                    i.similarity_score  AS similarity_score,
                    i.rank              AS rank,
                    ROW_NUMBER() OVER (
                        PARTITION BY i.item_id
                        ORDER BY i.rank ASC
                    ) AS rn
                FROM item_similar_items i
                JOIN seeds s ON i.item_id = s.item_id
                WHERE i.version = %s
            )
            SELECT seed_item_id, similar_item_id, similarity_score, rank
            FROM ranked
            WHERE rn <= %s
            ORDER BY seed_item_id, rank ASC;
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (seed_item_ids, version, per_seed_k))
            rows = cur.fetchall()
        return rows

    def get_user_interacted_item_ids(
        self, user_id: str, version: str = "v1"
    ) -> List[str]:
        """
        Return items the user already interacted with for filtering.
        Uses user_item_interest to reflect CF-versioned interactions.
        """
        sql = """
            SELECT item_id
            FROM user_item_interest
            WHERE user_id = %s AND version = %s AND interest_score > 0
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (user_id, version))
            rows = cur.fetchall()
        return [r["item_id"] for r in rows]

    def get_posts_by_ids(self, post_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Return full post information by post IDs.
        This joins necessary tables to get complete post data.
        """
        if not post_ids:
            return []

        sql = """
            SELECT 
                p.id, 
                p.title, 
                p.content, 
                p.created_at,
                p.updated_at,
                u.id as author_id,
                u.username as author_name,
                u.avatar_url as author_avatar,
                COALESCE(
                    (SELECT json_agg(
                        json_build_object(
                            'id', t.id,
                            'name', t.name
                        )
                    )
                    FROM post_tags pt
                    JOIN tags t ON pt.tag_id = t.id
                    WHERE pt.post_id = p.id
                    ), '[]'::json
                ) as tags
            FROM posts p
            JOIN users u ON p.author_id = u.id
            WHERE p.id = ANY(%s)
            ORDER BY array_position(%s, p.id::text)
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (post_ids, post_ids))
            posts = cur.fetchall()
        return posts

    # ---------- small helpers ----------

    def close(self):
        try:
            self.psycopg_conn.close()
        except Exception:
            pass
