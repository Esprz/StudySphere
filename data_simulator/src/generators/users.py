"""User generation for simulator v2 Phase 1."""

from __future__ import annotations

import random
from datetime import datetime, timezone

from config.models import RunConfig, SourceBundle, UserProfile
from core.ids import new_id


def generate_user_profiles(
    config: RunConfig,
    sources: SourceBundle,
    rng: random.Random,
    *,
    now: datetime | None = None,
) -> list[UserProfile]:
    now_utc = now or datetime.now(timezone.utc)
    themes = _all_interest_themes(sources)
    persona_axes = _persona_axes_lookup(sources)

    users: list[UserProfile] = []
    for _ in range(config.user_count):
        primary_interest = sample_primary_interest(themes, rng)
        secondary_interests = sample_secondary_interests(
            primary_interest=primary_interest,
            themes=themes,
            count_range=_secondary_interest_range(persona_axes),
            rng=rng,
        )
        users.append(
            UserProfile(
                user_id=new_id("u", rng=rng),
                primary_interest=primary_interest,
                secondary_interests=secondary_interests,
                learning_intensity=_sample_enum(persona_axes, "learning_intensity", rng),
                sleep_habit_skew=_sample_float_range(persona_axes, "sleep_habit_skew", rng),
                posting_tendency=_sample_enum(persona_axes, "posting_tendency", rng),
                interaction_tendency=_sample_enum(persona_axes, "interaction_tendency", rng),
                curiosity_level=_sample_float_range(persona_axes, "curiosity_level", rng),
                diligence_level=_sample_float_range(persona_axes, "diligence_level", rng),
                social_affinity=_sample_float_range(persona_axes, "social_affinity", rng),
                exploration_rate=_sample_float_range(persona_axes, "exploration_rate", rng),
                drift_rate=_sample_float_range(persona_axes, "drift_rate", rng),
                created_at=now_utc,
            )
        )
    return users


def sample_primary_interest(themes: list[str], rng: random.Random) -> str:
    return rng.choice(themes)


def sample_secondary_interests(
    *,
    primary_interest: str,
    themes: list[str],
    count_range: tuple[int, int],
    rng: random.Random,
) -> list[str]:
    min_count, max_count = count_range
    count = rng.randint(min_count, max_count)
    pool = [theme for theme in themes if theme != primary_interest]
    rng.shuffle(pool)
    return pool[:count]


def _all_interest_themes(sources: SourceBundle) -> list[str]:
    taxonomy = sources.require("interest_taxonomy")
    themes: list[str] = []
    for category in taxonomy.get("categories", []):
        for theme in category.get("themes", []):
            label = theme.get("label")
            if label:
                themes.append(str(label))
    if not themes:
        raise ValueError("No themes found in interest taxonomy")
    return themes


def _persona_axes_lookup(sources: SourceBundle) -> dict[str, dict]:
    persona_axes = sources.require("persona_axes")
    fields = persona_axes.get("fields", [])
    lookup: dict[str, dict] = {}
    for field in fields:
        name = field.get("name")
        if name:
            lookup[str(name)] = field
    return lookup


def _secondary_interest_range(persona_axes: dict[str, dict]) -> tuple[int, int]:
    field = persona_axes["secondary_interest_count"]
    values = field.get("allowed_values", [1, 3])
    return int(values[0]), int(values[1])


def _sample_enum(persona_axes: dict[str, dict], field_name: str, rng: random.Random) -> str:
    allowed = persona_axes[field_name].get("allowed_values", [])
    if not allowed:
        raise ValueError(f"No allowed enum values for field '{field_name}'")
    return str(rng.choice(allowed))


def _sample_float_range(persona_axes: dict[str, dict], field_name: str, rng: random.Random) -> float:
    values = persona_axes[field_name].get("allowed_values", [0.0, 1.0])
    lo, hi = float(values[0]), float(values[1])
    return round(rng.uniform(lo, hi), 4)
