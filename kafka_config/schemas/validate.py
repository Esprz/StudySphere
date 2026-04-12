"""Shared JSON Schema validation helpers for Kafka consumers."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from jsonschema import Draft7Validator


SCHEMA_DIR = Path(__file__).resolve().parent
TOPIC_TO_SCHEMA = {
    "post-events": "post-events.json",
    "user-events": "user-events.json",
    "behavior-events": "behavior-events.json",
    "embedding-updates": "embedding-updates.json",
}


@lru_cache(maxsize=None)
def _load_validator(topic_name: str) -> Optional[Draft7Validator]:
    schema_file = TOPIC_TO_SCHEMA.get(topic_name)
    if not schema_file:
        return None

    schema_path = SCHEMA_DIR / schema_file
    if not schema_path.exists():
        return None

    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    return Draft7Validator(schema)


def validate_event_payload(
    topic_name: str, payload: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    validator = _load_validator(topic_name)
    if validator is None:
        return True, None

    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
    if not errors:
        return True, None

    first_error = errors[0]
    error_path = ".".join(str(part) for part in first_error.path) or "<root>"
    return False, f"{error_path}: {first_error.message}"


def validate_json_message(
    topic_name: str, raw_message: str
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    try:
        payload = json.loads(raw_message)
    except json.JSONDecodeError as exc:
        return False, None, f"invalid JSON: {exc}"

    is_valid, error = validate_event_payload(topic_name, payload)
    if not is_valid:
        return False, payload, error

    return True, payload, None
