"""Redis helpers for offline jobs."""

from __future__ import annotations

import json
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover - exercised only in lean test environments
    redis = None


class CacheRedis:
    def __init__(self, host: str, port: int, db: int, password: str | None = None):
        if redis is None:
            raise RuntimeError(
                "redis package is required to use CacheRedis. Install offline_pipeline requirements."
            )
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )

    def ping(self) -> bool:
        return bool(self.client.ping())

    def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        payload = json.dumps(value, default=str)
        if ttl_seconds:
            self.client.setex(key, ttl_seconds, payload)
        else:
            self.client.set(key, payload)

    def get_json(self, key: str) -> Any | None:
        payload = self.client.get(key)
        if payload is None:
            return None
        return json.loads(payload)

    def set_text(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if ttl_seconds:
            self.client.setex(key, ttl_seconds, value)
        else:
            self.client.set(key, value)

    def get_text(self, key: str) -> str | None:
        return self.client.get(key)
