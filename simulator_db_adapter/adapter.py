"""Map simulator output bundles into Prisma-compatible JSONL row bundles."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PASSWORD_HASH = "simulator::locked_account"
OUTPUT_TABLES = [
    "users",
    "posts",
    "comments",
    "likes",
    "saves",
    "follows",
    "goals",
    "focus_times",
]


@dataclass(frozen=True)
class ExportResult:
    """Filesystem pointers for one emitted DB bundle."""

    output_dir: Path
    files: dict[str, Path]
    record_counts: dict[str, int]


def export_db_bundle(
    *,
    input_dir: str | Path,
    output_dir: str | Path | None = None,
) -> ExportResult:
    """Read one simulator run directory and emit Prisma-compatible JSONL tables."""
    source_dir = Path(input_dir).expanduser().resolve()
    target_dir = (
        Path(output_dir).expanduser().resolve()
        if output_dir is not None
        else source_dir / "db_bundle"
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    users = _read_jsonl(source_dir / "users.jsonl")
    posts = _read_jsonl(source_dir / "posts.jsonl")
    goals = _read_jsonl(source_dir / "goals.jsonl")
    interactions = _read_jsonl(source_dir / "interactions.jsonl")
    focus_sessions = _read_jsonl(source_dir / "focus_sessions.jsonl")
    propensity_logs = _read_jsonl(source_dir / "propensity_logs.jsonl")

    rendered_posts = _load_rendered_posts(source_dir)
    rendered_comments = _load_rendered_comments(source_dir)

    db_users = [_map_user(row) for row in users]
    db_posts = [_map_post(row, rendered_posts.get(str(row["post_id"]))) for row in posts]
    db_goals = [_map_goal(row) for row in goals]
    db_comments = _map_comments(interactions, rendered_comments)
    db_likes = _map_reaction_rows(interactions, event_type="like", row_kind="like")
    db_saves = _map_reaction_rows(interactions, event_type="save", row_kind="save")
    db_follows = _map_follows(propensity_logs)
    db_focus_times = [_map_focus_time(row) for row in focus_sessions]

    payloads = {
        "users": db_users,
        "posts": db_posts,
        "comments": db_comments,
        "likes": db_likes,
        "saves": db_saves,
        "follows": db_follows,
        "goals": db_goals,
        "focus_times": db_focus_times,
    }

    files: dict[str, Path] = {}
    record_counts: dict[str, int] = {}
    for table_name, rows in payloads.items():
        path = target_dir / f"{table_name}.jsonl"
        _write_jsonl(rows, path)
        files[table_name] = path
        record_counts[table_name] = len(rows)

    manifest_path = target_dir / "db_bundle_manifest.json"
    manifest = {
        "source_dir": str(source_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_counts": record_counts,
        "files": {table_name: str(path) for table_name, path in files.items()},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    files["manifest"] = manifest_path
    return ExportResult(output_dir=target_dir, files=files, record_counts=record_counts)


def _map_user(row: dict[str, Any]) -> dict[str, Any]:
    user_id = str(row["user_id"])
    primary_interest = _slug(str(row.get("primary_interest", "learner")))
    short_id = user_id.split("_")[-1][:8]
    username = f"{primary_interest}_{short_id}"
    goal_tags = _unique_strs(
        [row.get("primary_interest")] + list(row.get("secondary_interests", []))
    )
    return {
        "user_id": user_id,
        "username": username,
        "display_name": f"{str(row.get('primary_interest', 'Learner')).title()} Learner {short_id[:4]}",
        "email": f"{username}@sim.studysphere.local",
        "password_hash": DEFAULT_PASSWORD_HASH,
        "bio": _build_user_bio(row),
        "avatar_url": None,
        "goalTags": goal_tags,
        "habitLevel": _bounded_float(row.get("diligence_level", 0.5)),
        "timezone": "UTC",
        "created_at": row.get("created_at"),
        "updated_at": row.get("created_at"),
    }


def _map_post(row: dict[str, Any], rendered: dict[str, Any] | None) -> dict[str, Any]:
    title = rendered.get("title") if rendered else None
    content = rendered.get("content") if rendered else None
    topic = str(row.get("topic", "study"))
    subtopic = str(row.get("subtopic", "general"))
    post_style = str(row.get("post_style", "knowledge_share"))
    study_context = str(row.get("study_context", "general_study"))
    return {
        "post_id": str(row["post_id"]),
        "title": title or f"{topic.replace('_', ' ').title()}: {subtopic.replace('_', ' ').title()}",
        "content": content or _fallback_post_content(topic, subtopic, post_style, study_context),
        "user_id": str(row["author_id"]),
        "image": None,
        "extra": {
            "simulator_format": row.get("format"),
            "post_style": post_style,
            "creator_type": row.get("creator_type"),
            "utility_style": row.get("utility_style"),
            "social_affordance": row.get("social_affordance"),
            "goal_relation_type": row.get("goal_relation_type"),
            "true_latent_quality": row.get("true_latent_quality"),
            "observed_quality": row.get("observed_quality"),
        },
        "topicTags": _unique_strs([topic, subtopic]),
        "difficulty": int(row.get("difficulty", 1)),
        "created_at": row.get("created_at"),
        "updated_at": row.get("created_at"),
    }


def _map_comments(
    interactions: list[dict[str, Any]],
    rendered_comments: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    comment_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for row in sorted(
        interactions,
        key=lambda item: (
            item.get("timestamp", ""),
            int(item.get("thread_depth") or 0),
            str(item.get("interaction_id")),
        ),
    ):
        if row.get("event_type") != "comment":
            continue
        comment_id = str(row["interaction_id"])
        if comment_id in seen_ids:
            continue
        rendered = rendered_comments.get(comment_id)
        content = None
        if rendered:
            content = rendered.get("comment_text")
        if not content:
            content = row.get("comment_text") or _fallback_comment_content(row)
        comment_rows.append(
            {
                "comment_id": comment_id,
                "content": content,
                "user_id": str(row["user_id"]),
                "post_id": str(row["post_id"]),
                "parent_id": row.get("reply_to_interaction_id"),
                "created_at": row.get("timestamp"),
            }
        )
        seen_ids.add(comment_id)
    return comment_rows


def _map_reaction_rows(
    interactions: list[dict[str, Any]],
    *,
    event_type: str,
    row_kind: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for row in sorted(interactions, key=lambda item: (item.get("timestamp", ""), str(item.get("interaction_id")))):
        if row.get("event_type") != event_type:
            continue
        user_id = str(row["user_id"])
        post_id = str(row["post_id"])
        pair = (user_id, post_id)
        if pair in seen_pairs:
            continue
        record_id = _stable_id(row_kind, user_id, post_id)
        rows.append(
            {
                f"{row_kind}_id": record_id,
                "post_id": post_id,
                "user_id": user_id,
                "created_at": row.get("timestamp"),
            }
        )
        seen_pairs.add(pair)
    return rows


def _map_follows(propensity_logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for row in sorted(propensity_logs, key=lambda item: (item.get("timestamp", ""), str(item.get("log_id")))):
        if row.get("decision_stage") != "follow_decision":
            continue
        if not row.get("sampled_outcome"):
            continue
        metadata = row.get("metadata") or {}
        followee_id = metadata.get("target_author_id")
        follower_id = row.get("user_id")
        if not followee_id or not follower_id or followee_id == follower_id:
            continue
        pair = (str(follower_id), str(followee_id))
        if pair in seen_pairs:
            continue
        rows.append(
            {
                "follow_id": _stable_id("follow", pair[0], pair[1]),
                "follower_id": pair[0],
                "followee_id": pair[1],
                "created_at": row.get("timestamp"),
            }
        )
        seen_pairs.add(pair)
    return rows


def _map_goal(row: dict[str, Any]) -> dict[str, Any]:
    related_topics = [str(topic) for topic in row.get("related_topics", [])]
    content = (
        f"{str(row.get('goal_category', 'study')).replace('_', ' ').title()} - "
        f"{str(row.get('goal_type', 'goal')).replace('_', ' ')}"
    )
    if related_topics:
        content += f" ({', '.join(related_topics)})"
    return {
        "goal_id": str(row["goal_id"]),
        "content": content,
        "user_id": str(row["user_id"]),
        "status": _map_goal_status(str(row.get("progress_state", "active"))),
        "created_at": row.get("start_at"),
    }


def _map_focus_time(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ft_id": str(row["focus_id"]),
        "start": row.get("started_at"),
        "end": row.get("ended_at"),
        "user_id": str(row["user_id"]),
        "goal_id": row.get("related_goal_id"),
        "tags": _unique_strs([row.get("topic")]),
        "sourceTrigger": f"post:{row['trigger_post_id']}",
        "created_at": row.get("started_at"),
    }


def _load_rendered_posts(source_dir: Path) -> dict[str, dict[str, Any]]:
    rendered: dict[str, dict[str, Any]] = {}
    for path in sorted(source_dir.glob("*_rendered_posts.jsonl")):
        for row in _read_jsonl(path):
            rendered[str(row["post_id"])] = row
    return rendered


def _load_rendered_comments(source_dir: Path) -> dict[str, dict[str, Any]]:
    rendered: dict[str, dict[str, Any]] = {}
    for path in sorted(source_dir.glob("*_rendered_comments.jsonl")):
        for row in _read_jsonl(path):
            rendered[str(row["interaction_id"])] = row
    return rendered


def _build_user_bio(row: dict[str, Any]) -> str:
    interests = _unique_strs(
        [row.get("primary_interest")] + list(row.get("secondary_interests", []))
    )
    learning_intensity = str(row.get("learning_intensity", "steady")).replace("_", " ")
    return f"{learning_intensity.title()} learner focused on {', '.join(interests[:3])}."


def _fallback_post_content(topic: str, subtopic: str, post_style: str, study_context: str) -> str:
    return (
        f"{post_style.replace('_', ' ').capitalize()} about {topic.replace('_', ' ')} and "
        f"{subtopic.replace('_', ' ')}. Context: {study_context.replace('_', ' ')}."
    )


def _fallback_comment_content(row: dict[str, Any]) -> str:
    thread_depth = int(row.get("thread_depth") or 0)
    if thread_depth > 0:
        return "I agree with that point and would add a small follow-up detail."
    return "This is useful. I want to try this approach in my own study routine."


def _map_goal_status(progress_state: str) -> str:
    mapping = {
        "active": "ONGOING",
        "completed": "ARCHIVED",
        "dropped": "ARCHIVED",
    }
    return mapping.get(progress_state, "ONGOING")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(json.loads(stripped))
    return rows


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _slug(value: str) -> str:
    lowered = value.lower().replace(" ", "_")
    return "".join(char for char in lowered if char.isalnum() or char == "_").strip("_") or "learner"


def _unique_strs(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _bounded_float(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.5
    return round(max(0.0, min(1.0, numeric)), 6)
