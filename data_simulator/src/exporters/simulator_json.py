"""Simulator-native JSON/JSONL export helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.models import WorldState


def export_simulator_jsonl(world_state: WorldState, output_dir: str | Path) -> dict[str, Path]:
    """Export simulator entity tables into per-entity JSONL files."""
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    entities: dict[str, list[Any]] = {
        "users": list(world_state.users),
        "goals": _flatten_goals(world_state),
        "posts": list(world_state.posts),
        "sessions": list(world_state.sessions),
        "exposures": list(world_state.exposures),
        "interactions": list(world_state.interactions),
        "focus_sessions": list(world_state.focus_sessions),
    }

    written: dict[str, Path] = {}
    for name, records in entities.items():
        path = target_dir / f"{name}.jsonl"
        _write_jsonl(records, path)
        written[name] = path
    return written


def _flatten_goals(world_state: WorldState) -> list[Any]:
    """Flatten per-user goals into a stable ordered list."""
    records: list[Any] = []
    for user in world_state.users:
        records.extend(world_state.goals_by_user.get(user.user_id, []))
    return records


def _write_jsonl(records: list[Any], path: Path) -> None:
    """Write one list of records as JSONL with deterministic UTF-8 encoding."""
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            payload = _to_jsonable(record)
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")


def _to_jsonable(value: Any) -> Any:
    """Convert dataclass-rich records into JSON-safe values."""
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, set):
        converted = [_to_jsonable(item) for item in value]
        try:
            return sorted(converted)
        except TypeError:
            return sorted(converted, key=lambda item: json.dumps(item, sort_keys=True))
    return value
