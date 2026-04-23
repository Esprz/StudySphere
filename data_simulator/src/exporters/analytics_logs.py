"""Analytics/event log exporters for simulator output bundles."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config.models import WorldState
from exporters.simulator_json import _to_jsonable


def export_analytics_logs(world_state: WorldState, output_dir: str | Path) -> dict[str, Path]:
    """Export event-level analytics logs and propensity logs as JSONL."""
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    event_log_path = target_dir / "event_log.jsonl"
    propensity_log_path = target_dir / "propensity_logs.jsonl"

    _write_jsonl(_build_event_log_records(world_state), event_log_path)
    _write_jsonl([asdict(record) for record in world_state.propensity_logs], propensity_log_path)

    return {
        "event_log": event_log_path,
        "propensity_logs": propensity_log_path,
    }


def _build_event_log_records(world_state: WorldState) -> list[dict[str, Any]]:
    """Build a unified analytics event stream across exposure/interaction/focus entities."""
    records: list[dict[str, Any]] = []

    for exposure in world_state.exposures:
        records.append(
            {
                "event_kind": "exposure",
                "event_id": exposure.exposure_id,
                "event_type": "exposure",
                "timestamp": exposure.timestamp,
                "user_id": exposure.user_id,
                "session_id": exposure.session_id,
                "post_id": exposure.post_id,
                "payload": asdict(exposure),
            }
        )
    for interaction in world_state.interactions:
        records.append(
            {
                "event_kind": "interaction",
                "event_id": interaction.interaction_id,
                "event_type": interaction.event_type,
                "timestamp": interaction.timestamp,
                "user_id": interaction.user_id,
                "session_id": interaction.session_id,
                "post_id": interaction.post_id,
                "payload": asdict(interaction),
            }
        )
    for focus in world_state.focus_sessions:
        records.append(
            {
                "event_kind": "focus_session",
                "event_id": focus.focus_id,
                "event_type": "focus_session",
                "timestamp": focus.started_at,
                "user_id": focus.user_id,
                "session_id": focus.session_id,
                "post_id": focus.trigger_post_id,
                "payload": asdict(focus),
            }
        )

    records.sort(key=lambda item: (item["timestamp"], item["event_kind"], item["event_id"]))
    return records


def _write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    """Write dict records to JSONL using UTF-8 encoding."""
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_to_jsonable(record), sort_keys=True))
            handle.write("\n")
