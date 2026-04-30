import psycopg
from psycopg.rows import dict_row
from typing import List, Dict, Any, Tuple, Optional
from .env_config import EnvConfig


class PostgresStore:
    def __init__(self):
        self.db_connection_string = EnvConfig.DATABASE_URL
        self.psycopg_conn = psycopg.connect(
            self.db_connection_string, row_factory=dict_row
        )
        # Read-heavy access is simpler and more resilient with autocommit enabled.
        self.psycopg_conn.autocommit = True

    def get_session(self) -> psycopg.Connection:
        return self.psycopg_conn

    # ---------- SINGLE-ENTITY QUERIES (fixed to return id + score) ----------

    def get_active_feature_version(
        self, feature_name: str, fallback: Optional[str] = "v1"
    ) -> Optional[str]:
        sql = """
            SELECT active_version
            FROM feature_metadata
            WHERE feature_name = %s
        """
        try:
            with self.psycopg_conn.cursor() as cur:
                cur.execute(sql, (feature_name,))
                row = cur.fetchone()
            return (
                row["active_version"]
                if row and row.get("active_version")
                else fallback
            )
        except Exception:
            return fallback

    def _resolve_version(self, feature_name: str, version: Optional[str]) -> str:
        return version or self.get_active_feature_version(feature_name, fallback="v1")

    def get_user_topk_posts(
        self, user_id: str, k: int, version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        version = self._resolve_version("cf", version)
        sql = """
            SELECT item_id, interest_score, rank
            FROM user_interested_items
            WHERE user_id = %s AND version = %s
            ORDER BY rank ASC
            LIMIT %s;
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (user_id, version, k))
            rows = cur.fetchall()
        return rows

    def get_user_topk_neighbors(
        self, user_id: str, k: int, version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Return the user's top-K similar users with scores.
        Output: [{similar_user_id, similarity_score, rank}]
        """
        version = self._resolve_version("cf", version)
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
        self, item_id: str, k: int, version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Return an item's top-K similar items with scores.
        Output: [{similar_item_id, similarity_score, rank}]
        """
        version = self._resolve_version("cf", version)
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
        self, seed_item_ids: List[str], per_seed_k: int, version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Batch: for many seeds, fetch each seed's top-K similar items.
        Output rows: [{seed_item_id, similar_item_id, similarity_score, rank}]
        """
        if not seed_item_ids:
            return []
        version = self._resolve_version("cf", version)

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
        self, user_id: str, version: Optional[str] = None
    ) -> List[str]:
        """
        Return items the user already interacted with for filtering.
        Uses user_item_interest to reflect CF-versioned interactions.
        """
        version = self._resolve_version("cf", version)
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
                p.post_id,
                p.title, 
                p.content, 
                p.image,
                p.extra,
                p.created_at,
                p.updated_at,
                p.user_id,
                u.user_id AS author_id,
                u.username AS author_name,
                u.avatar_url AS author_avatar
            FROM "Post" p
            JOIN "User" u ON p.user_id = u.user_id
            WHERE p.post_id = ANY(%s)
            ORDER BY array_position(%s, p.post_id::text)
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (post_ids, post_ids))
            posts = cur.fetchall()
        return posts

    def get_user_interaction_count(self, user_id: str) -> int:
        sql = """
            SELECT COUNT(*) as cnt
            FROM etl_behavior_events
            WHERE user_id = %s
        """
        try:
            with self.psycopg_conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                row = cur.fetchone()
                return row["cnt"] if row else 0
        except Exception:
            return 0

    def get_user_goal_tags(self, user_id: str) -> List[str]:
        sql = """
            SELECT "goalTags"
            FROM "User"
            WHERE user_id = %s
        """
        try:
            with self.psycopg_conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                row = cur.fetchone()
            if row and row.get("goalTags"):
                return [tag for tag in row["goalTags"] if tag]
        except Exception:
            return []
        return []

    def get_posts_matching_goal_tags(
        self, goal_tags: List[str], k: int = 50
    ) -> List[Dict[str, Any]]:
        if not goal_tags:
            return []

        sql = """
            SELECT
                p.post_id AS item_id,
                (
                    SELECT COUNT(*)
                    FROM unnest(COALESCE(p."topicTags", ARRAY[]::text[])) AS tag
                    WHERE tag = ANY(%s::text[])
                )::float AS score
            FROM "Post" p
            WHERE COALESCE(p."topicTags", ARRAY[]::text[]) && %s::text[]
            ORDER BY score DESC, p.created_at DESC
            LIMIT %s
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (goal_tags, goal_tags, k))
            return cur.fetchall()

    def get_seen_items_last_days(self, user_id: str, days: int = 30) -> set[str]:
        sql = """
            SELECT DISTINCT post_id AS item_id
            FROM etl_behavior_events
            WHERE user_id = %s
              AND event_type = 'POST_VIEWED'
              AND processed_at > NOW() - (%s * INTERVAL '1 day')
              AND post_id IS NOT NULL
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (user_id, days))
            rows = cur.fetchall()
        return {row["item_id"] for row in rows if row.get("item_id")}

    def get_post_topic_tags(self, post_ids: List[str]) -> Dict[str, List[str]]:
        if not post_ids:
            return {}

        sql = """
            SELECT post_id, "topicTags"
            FROM "Post"
            WHERE post_id = ANY(%s)
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (post_ids,))
            rows = cur.fetchall()
        return {
            row["post_id"]: [tag for tag in row.get("topicTags", []) if tag]
            for row in rows
        }

    def get_following_recent_posts(self, user_id: str, k: int = 50) -> List[Dict[str, Any]]:
        sql = """
            SELECT p.post_id AS item_id, p.created_at
            FROM "Post" p
            JOIN "Follow" f ON f.followee_id = p.user_id
            WHERE f.follower_id = %s
              AND p.created_at > NOW() - INTERVAL '7 days'
            ORDER BY p.created_at DESC
            LIMIT %s
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (user_id, k))
            return cur.fetchall()

    def get_trending_posts(
        self, k: int = 50, version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        version = self._resolve_version("trending", version)
        sql = """
            SELECT item_id, popularity
            FROM trending_items
            WHERE version = %s
            ORDER BY rank ASC
            LIMIT %s
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (version, k))
            rows = cur.fetchall()

        if rows:
            return rows

        fallback_sql = """
            SELECT
                p.post_id AS item_id,
                (
                    COALESCE(l.like_count, 0) * 2
                    + COALESCE(s.save_count, 0) * 3
                    + COALESCE(c.comment_count, 0)
                )::float AS popularity
            FROM "Post" p
            LEFT JOIN (
                SELECT post_id, COUNT(*) AS like_count
                FROM "Like"
                GROUP BY post_id
            ) l ON l.post_id = p.post_id
            LEFT JOIN (
                SELECT post_id, COUNT(*) AS save_count
                FROM "Save"
                GROUP BY post_id
            ) s ON s.post_id = p.post_id
            LEFT JOIN (
                SELECT post_id, COUNT(*) AS comment_count
                FROM "Comment"
                GROUP BY post_id
            ) c ON c.post_id = p.post_id
            ORDER BY popularity DESC, p.created_at DESC
            LIMIT %s
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(fallback_sql, (k,))
            return cur.fetchall()

    def get_followed_user_ids(self, user_id: str) -> List[str]:
        sql = """
            SELECT followee_id
            FROM "Follow"
            WHERE follower_id = %s
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            rows = cur.fetchall()
        return [row["followee_id"] for row in rows if row.get("followee_id")]

    def get_users_by_ids(self, user_ids: List[str]) -> List[Dict[str, Any]]:
        if not user_ids:
            return []

        sql = """
            SELECT user_id, username, display_name, avatar_url, bio, "goalTags"
            FROM "User"
            WHERE user_id = ANY(%s)
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (user_ids,))
            return cur.fetchall()

    def get_popular_users(self, limit: int = 5) -> List[Dict[str, Any]]:
        sql = """
            SELECT
                u.user_id,
                u.username,
                u.display_name,
                u.avatar_url,
                u.bio,
                COUNT(f.follow_id)::int AS follower_count
            FROM "User" u
            LEFT JOIN "Follow" f ON f.followee_id = u.user_id
            GROUP BY u.user_id, u.username, u.display_name, u.avatar_url, u.bio
            ORDER BY follower_count DESC, u.created_at DESC
            LIMIT %s
        """
        with self.psycopg_conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return cur.fetchall()

    def close(self):
        try:
            self.psycopg_conn.close()
        except Exception:
            pass
