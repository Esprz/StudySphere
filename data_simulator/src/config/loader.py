"""Source loading for simulator simulator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import SourceBundle


SOURCE_FILES: dict[str, str] = {
    "activity_intent_taxonomy": "activity_intent_taxonomy.source.json",
    "content_lifecycle_rules": "content_lifecycle_rules.source.json",
    "content_taxonomy": "content_taxonomy.source.json",
    "decision_formulas": "decision_formulas.source.json",
    "goal_activity_bridge": "goal_activity_bridge.source.json",
    "goal_interest_bridge": "goal_interest_bridge.source.json",
    "goal_taxonomy": "goal_taxonomy.source.json",
    "interaction_taxonomy": "interaction_taxonomy.source.json",
    "interest_taxonomy": "interest_taxonomy.source.json",
    "jitter_noise_rules": "jitter_noise_rules.source.json",
    "negative_interaction_taxonomy": "negative_interaction_taxonomy.source.json",
    "persona_axes": "persona_axes.source.json",
    "session_dynamics": "session_dynamics.source.json",
    "signal_catalog": "signal_catalog.source.json",
    "state_update_rules": "state_update_rules.source.json",
    "topic_activity_bridge": "topic_activity_bridge.source.json",
    "world_clock": "world_clock.source.json",
}


def load_sources(base_path: str | Path) -> SourceBundle:
    source_dir = _resolve_source_dir(base_path)
    sources: dict[str, dict[str, Any]] = {}
    for name, filename in SOURCE_FILES.items():
        path = source_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing required source file: {path}")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Source file {path} must contain a JSON object")
        sources[name] = payload
    bundle = SourceBundle(base_path=source_dir, sources=sources)
    validate_source_bundle(bundle)
    return bundle


def validate_source_bundle(bundle: SourceBundle) -> None:
    missing = [name for name in SOURCE_FILES if name not in bundle.sources]
    if missing:
        raise ValueError(f"Missing required source entries: {', '.join(sorted(missing))}")

    for name, payload in bundle.sources.items():
        if "version" not in payload:
            raise ValueError(f"Source '{name}' missing required field 'version'")

    signal_catalog = bundle.require("signal_catalog")
    if not isinstance(signal_catalog.get("signals"), list):
        raise ValueError("signal_catalog.source.json must contain a list at 'signals'")

    world_clock = bundle.require("world_clock")
    contexts = world_clock.get("contexts")
    if not isinstance(contexts, dict):
        raise ValueError("world_clock.source.json must contain an object at 'contexts'")
    for key in ("hour_segments", "day_types", "academic_seasons"):
        if key not in contexts:
            raise ValueError(f"world_clock.contexts missing '{key}'")


def _resolve_source_dir(base_path: str | Path) -> Path:
    path = Path(base_path).expanduser().resolve()
    if (path / "sources").is_dir():
        return path / "sources"
    if path.is_dir() and path.name == "sources":
        return path
    raise FileNotFoundError(f"Could not find sources directory from base path: {path}")

