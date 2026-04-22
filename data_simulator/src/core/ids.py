"""Identifier helper utilities."""

from __future__ import annotations

import random
import uuid


def new_id(prefix: str, rng: random.Random | None = None) -> str:
    if rng is None:
        token = uuid.uuid4().hex[:12]
    else:
        token = format(rng.getrandbits(48), "012x")
    return f"{prefix}_{token}"

