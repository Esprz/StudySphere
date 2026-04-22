"""Time and calendar helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config.models import GlobalTimeContext


def clip_0_1(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def derive_global_time_context(
    timestamp: datetime,
    world_clock: dict[str, Any],
    *,
    season_name: str | None = None,
) -> GlobalTimeContext:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    contexts = world_clock.get("contexts", {})
    hour_segments = contexts.get("hour_segments", [])
    academic_seasons = contexts.get("academic_seasons", [])

    hour_segment = _select_hour_segment(timestamp.hour, hour_segments)
    day_type = "weekend" if timestamp.weekday() >= 5 else "weekday"
    season = _select_academic_season(academic_seasons, season_name)

    return GlobalTimeContext(
        wall_clock_time=timestamp,
        hour_segment=hour_segment,
        day_type=day_type,
        academic_season=str(season.get("name", "regular_term")),
        urgency_bonus=float(season.get("urgency_bonus", 0.0)),
        fatigue_bonus=float(season.get("fatigue_bonus", 0.0)),
        intent_bias=dict(season.get("intent_bias", {})),
    )


def _select_hour_segment(hour: int, hour_segments: list[dict[str, Any]]) -> str:
    for segment in hour_segments:
        hours = segment.get("hours", [])
        if hour in hours:
            return str(segment.get("name", "unknown"))
    return "unknown"


def _select_academic_season(
    academic_seasons: list[dict[str, Any]],
    season_name: str | None,
) -> dict[str, Any]:
    if season_name:
        for season in academic_seasons:
            if season.get("name") == season_name:
                return season

    for season in academic_seasons:
        if season.get("name") == "regular_term":
            return season

    if academic_seasons:
        return academic_seasons[0]
    return {"name": "regular_term", "urgency_bonus": 0.0, "fatigue_bonus": 0.0, "intent_bias": {}}

