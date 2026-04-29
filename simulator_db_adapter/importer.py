"""Import Prisma-compatible DB bundles into PostgreSQL."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


IMPORT_ORDER = [
    "users",
    "goals",
    "posts",
    "follows",
    "comments",
    "likes",
    "saves",
    "focus_times",
]


@dataclass(frozen=True)
class ImportResult:
    """Structured summary for one bundle import."""

    bundle_dir: Path
    database_url: str
    imported_counts: dict[str, int]
    available_counts: dict[str, int]
    dry_run: bool


def import_db_bundle(
    *,
    bundle_dir: str | Path,
    database_url: str | None = None,
    dry_run: bool = False,
) -> ImportResult:
    """Import one emitted DB bundle into PostgreSQL in dependency-safe order."""
    resolved_bundle_dir = resolve_bundle_dir(bundle_dir)
    manifest = _load_json(resolved_bundle_dir / "db_bundle_manifest.json")
    source_dir = Path(str(manifest.get("source_dir", ""))).expanduser()
    available_counts = {
        str(key): int(value)
        for key, value in (manifest.get("record_counts") or {}).items()
    }
    available_counts["etl_behavior_events"] = _count_jsonl(
        source_dir / "event_log.jsonl"
    ) if source_dir.is_dir() else 0
    resolved_database_url = database_url or os.environ.get("DATABASE_URL", "").strip()
    if not resolved_database_url:
        raise ValueError("Missing database url: pass --database-url or set DATABASE_URL")

    if dry_run:
        return ImportResult(
            bundle_dir=resolved_bundle_dir,
            database_url=resolved_database_url,
            imported_counts=dict(available_counts),
            available_counts=available_counts,
            dry_run=True,
        )

    imported_counts: dict[str, int] = {}
    with psycopg.connect(resolved_database_url) as connection:
        connection.autocommit = False
        _ensure_etl_behavior_events_table(connection)
        for table_name in IMPORT_ORDER:
            rows = _read_jsonl(resolved_bundle_dir / f"{table_name}.jsonl")
            imported_counts[table_name] = _import_table(connection, table_name, rows)
        imported_counts["etl_behavior_events"] = _import_behavior_events(
            connection,
            source_dir / "event_log.jsonl",
        )
        connection.commit()

    return ImportResult(
        bundle_dir=resolved_bundle_dir,
        database_url=resolved_database_url,
        imported_counts=imported_counts,
        available_counts=available_counts,
        dry_run=False,
    )


def resolve_bundle_dir(path: str | Path) -> Path:
    """Resolve either a bundle directory or a simulator run dir containing `db_bundle/`."""
    candidate = Path(path).expanduser().resolve()
    if (candidate / "db_bundle_manifest.json").is_file():
        return candidate
    nested = candidate / "db_bundle"
    if (nested / "db_bundle_manifest.json").is_file():
        return nested
    raise FileNotFoundError(f"Could not find db bundle manifest under {candidate}")


def _import_table(connection: psycopg.Connection, table_name: str, rows: list[dict[str, Any]]) -> int:
    """Route one bundle table to the matching SQL writer."""
    if not rows:
        return 0
    if table_name == "users":
        return _import_users(connection, rows)
    if table_name == "goals":
        return _import_goals(connection, rows)
    if table_name == "posts":
        return _import_posts(connection, rows)
    if table_name == "follows":
        return _import_follows(connection, rows)
    if table_name == "comments":
        return _import_comments(connection, rows)
    if table_name == "likes":
        return _import_likes(connection, rows)
    if table_name == "saves":
        return _import_saves(connection, rows)
    if table_name == "focus_times":
        return _import_focus_times(connection, rows)
    raise ValueError(f"Unsupported bundle table: {table_name}")


def _ensure_etl_behavior_events_table(connection: psycopg.Connection) -> None:
    """Create partitioned ETL event storage and dedupe registry if absent."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS etl_behavior_event_keys (
                event_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP NOT NULL
            )
            """
        )
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'etl_behavior_events'
            ) AS exists
            """
        )
        exists = bool(cursor.fetchone()["exists"])
        if not exists:
            cursor.execute(
                """
                CREATE TABLE etl_behavior_events (
                    id TEXT NOT NULL,
                    event_id TEXT,
                    user_id TEXT NOT NULL,
                    post_id TEXT,
                    event_type TEXT NOT NULL,
                    search_term TEXT,
                    session_id TEXT,
                    position INTEGER,
                    dwell_ms INTEGER,
                    source TEXT,
                    processed_at TIMESTAMP NOT NULL,
                    extra_data JSONB,
                    PRIMARY KEY (processed_at, id)
                )
                PARTITION BY RANGE (processed_at)
                """
            )
            for statement in [
                "CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_user_id ON etl_behavior_events (user_id)",
                "CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_post_id ON etl_behavior_events (post_id)",
                "CREATE INDEX IF NOT EXISTS ix_etl_behavior_events_processed_at ON etl_behavior_events (processed_at)",
            ]:
                cursor.execute(statement)


def _import_behavior_events(connection: psycopg.Connection, event_log_path: Path) -> int:
    """Project simulator event log into the shared ETL behavior event table."""
    rows = _read_jsonl(event_log_path)
    if not rows:
        return 0

    payload = []
    for row in rows:
        event_kind = str(row.get("event_kind", ""))
        event_type = str(row.get("event_type", ""))
        payload_row = _map_behavior_event_row(row, event_kind=event_kind, event_type=event_type)
        if payload_row is None:
            continue
        payload.append(payload_row)

    month_starts = {
        _first_of_month(_coerce_event_dt(item[10]))
        for item in payload
    }
    for month_start in sorted(month_starts):
        _ensure_etl_partition(connection, month_start)

    inserted = 0
    with connection.cursor() as cursor:
        for item in payload:
            event_id = item[1]
            processed_at = item[10]
            if event_id:
                cursor.execute(
                    """
                    INSERT INTO etl_behavior_event_keys (event_id, processed_at)
                    VALUES (%s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                    RETURNING event_id
                    """,
                    (event_id, processed_at),
                )
                if cursor.fetchone() is None:
                    continue
            cursor.execute(
                """
                INSERT INTO etl_behavior_events (
                    id,
                    event_id,
                    user_id,
                    post_id,
                    event_type,
                    search_term,
                    session_id,
                    position,
                    dwell_ms,
                    source,
                    processed_at,
                    extra_data
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                item,
            )
            inserted += 1
    return inserted


def _map_behavior_event_row(
    row: dict[str, Any],
    *,
    event_kind: str,
    event_type: str,
) -> tuple[Any, ...] | None:
    payload = row.get("payload") or {}
    if event_kind == "exposure":
        mapped_type = "POST_VIEWED"
        dwell_ms = payload.get("feed_dwell_ms")
        position = payload.get("rank_position")
    elif event_kind == "interaction":
        mapped_type = _map_event_type_to_etl(event_type)
        if mapped_type is None:
            return None
        dwell_ms = payload.get("dwell_ms") or payload.get("feed_dwell_ms")
        position = None
    elif event_kind == "focus_session":
        return None
    else:
        return None

    event_id = str(row.get("event_id"))
    return (
        event_id,
        event_id,
        row.get("user_id"),
        row.get("post_id"),
        mapped_type,
        payload.get("search_term"),
        row.get("session_id"),
        position,
        dwell_ms,
        "simulator_db_adapter",
        row.get("timestamp"),
        Jsonb(payload),
    )


def _map_event_type_to_etl(event_type: str) -> str | None:
    mapping = {
        "view": "POST_VIEWED",
        "like": "POST_LIKED",
        "save": "POST_SAVED",
        "comment": "COMMENT_CREATED",
    }
    return mapping.get(event_type)


def _import_users(connection: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    payload = [
        (
            row["user_id"],
            row["username"],
            row["display_name"],
            row["email"],
            row["password_hash"],
            row.get("bio"),
            row.get("avatar_url"),
            row.get("goalTags", []),
            row.get("habitLevel", 0.5),
            row.get("timezone"),
            row.get("created_at"),
            row.get("updated_at"),
        )
        for row in rows
    ]
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO "User" (
                user_id,
                username,
                display_name,
                email,
                password_hash,
                bio,
                avatar_url,
                "goalTags",
                "habitLevel",
                timezone,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET
                username = EXCLUDED.username,
                display_name = EXCLUDED.display_name,
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash,
                bio = EXCLUDED.bio,
                avatar_url = EXCLUDED.avatar_url,
                "goalTags" = EXCLUDED."goalTags",
                "habitLevel" = EXCLUDED."habitLevel",
                timezone = EXCLUDED.timezone,
                updated_at = EXCLUDED.updated_at
            """,
            payload,
        )
        return _normalized_rowcount(cursor.rowcount, len(rows))


def _import_goals(connection: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    payload = [
        (
            row["goal_id"],
            row["content"],
            row["user_id"],
            row.get("status", "ONGOING"),
            row.get("created_at"),
        )
        for row in rows
    ]
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO "Goal" (
                goal_id,
                content,
                user_id,
                status,
                created_at
            )
            VALUES (%s, %s, %s, %s::"GoalStatus", %s)
            ON CONFLICT (goal_id)
            DO UPDATE SET
                content = EXCLUDED.content,
                user_id = EXCLUDED.user_id,
                status = EXCLUDED.status
            """,
            payload,
        )
        return _normalized_rowcount(cursor.rowcount, len(rows))


def _import_posts(connection: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    payload = [
        (
            row["post_id"],
            row["title"],
            row["content"],
            row["user_id"],
            Jsonb(row["image"]) if row.get("image") is not None else None,
            Jsonb(row["extra"]) if row.get("extra") is not None else None,
            row.get("topicTags", []),
            row.get("difficulty"),
            row.get("created_at"),
            row.get("updated_at"),
        )
        for row in rows
    ]
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO "Post" (
                post_id,
                title,
                content,
                user_id,
                image,
                extra,
                "topicTags",
                difficulty,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (post_id)
            DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                user_id = EXCLUDED.user_id,
                image = EXCLUDED.image,
                extra = EXCLUDED.extra,
                "topicTags" = EXCLUDED."topicTags",
                difficulty = EXCLUDED.difficulty,
                updated_at = EXCLUDED.updated_at
            """,
            payload,
        )
        return _normalized_rowcount(cursor.rowcount, len(rows))


def _import_follows(connection: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    payload = [
        (
            row["follow_id"],
            row["follower_id"],
            row["followee_id"],
            row.get("created_at"),
        )
        for row in rows
    ]
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO "Follow" (
                follow_id,
                follower_id,
                followee_id,
                created_at
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (follower_id, followee_id)
            DO NOTHING
            """,
            payload,
        )
        return _normalized_rowcount(cursor.rowcount, len(rows))


def _import_comments(connection: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    imported = 0
    payload = sorted(
        rows,
        key=lambda row: (0 if row.get("parent_id") in {None, ""} else 1, row.get("created_at") or ""),
    )
    with connection.cursor() as cursor:
        for row in payload:
            cursor.execute(
                """
                INSERT INTO "Comment" (
                    comment_id,
                    content,
                    user_id,
                    post_id,
                    parent_id,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (comment_id)
                DO UPDATE SET
                    content = EXCLUDED.content,
                    user_id = EXCLUDED.user_id,
                    post_id = EXCLUDED.post_id,
                    parent_id = EXCLUDED.parent_id
                """,
                (
                    row["comment_id"],
                    row["content"],
                    row["user_id"],
                    row["post_id"],
                    row.get("parent_id"),
                    row.get("created_at"),
                ),
            )
            imported += _normalized_rowcount(cursor.rowcount, 1)
    return imported


def _import_likes(connection: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    payload = [
        (
            row["like_id"],
            row["post_id"],
            row["user_id"],
            row.get("created_at"),
        )
        for row in rows
    ]
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO "Like" (
                like_id,
                post_id,
                user_id,
                created_at
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, post_id)
            DO NOTHING
            """,
            payload,
        )
        return _normalized_rowcount(cursor.rowcount, len(rows))


def _import_saves(connection: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    payload = [
        (
            row["save_id"],
            row["post_id"],
            row["user_id"],
            row.get("created_at"),
        )
        for row in rows
    ]
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO "Save" (
                save_id,
                post_id,
                user_id,
                created_at
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, post_id)
            DO NOTHING
            """,
            payload,
        )
        return _normalized_rowcount(cursor.rowcount, len(rows))


def _import_focus_times(connection: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    payload = [
        (
            row["ft_id"],
            row["start"],
            row.get("end"),
            row["user_id"],
            row.get("goal_id"),
            row.get("tags", []),
            row.get("sourceTrigger"),
            row.get("created_at"),
        )
        for row in rows
    ]
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO "FocusTime" (
                ft_id,
                start,
                "end",
                user_id,
                goal_id,
                tags,
                "sourceTrigger",
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ft_id)
            DO UPDATE SET
                start = EXCLUDED.start,
                "end" = EXCLUDED."end",
                user_id = EXCLUDED.user_id,
                goal_id = EXCLUDED.goal_id,
                tags = EXCLUDED.tags,
                "sourceTrigger" = EXCLUDED."sourceTrigger"
            """,
            payload,
        )
        return _normalized_rowcount(cursor.rowcount, len(rows))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _ensure_etl_partition(connection: psycopg.Connection, month_start: datetime) -> None:
    start = _first_of_month(month_start)
    end = _first_of_next_month(start)
    partition_name = f"etl_behavior_events_{start.strftime('%Y_%m')}"
    start_literal = start.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    end_literal = end.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF etl_behavior_events
            FOR VALUES FROM ('{start_literal}') TO ('{end_literal}')
            """
        )


def _first_of_month(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _first_of_next_month(value: datetime) -> datetime:
    base = _first_of_month(value)
    return (base + timedelta(days=32)).replace(day=1)


def _coerce_event_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalized_rowcount(rowcount: int, fallback: int) -> int:
    return fallback if rowcount is None or rowcount < 0 else int(rowcount)
