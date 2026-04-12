"""Redis helpers for offline jobs."""

from __future__ import annotations

import json
from typing import Any

import redis


class CacheRedis:
    def __init__(self, host: str, port: int, db: int, password: str | None = None):
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

