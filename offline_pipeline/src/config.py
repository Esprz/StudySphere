"""Environment configuration for offline pipeline jobs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class OfflinePipelineConfig:
    database_url: str
    redis_cache_host: str
    redis_cache_port: int
    redis_cache_db: int
    redis_session_host: str
    redis_session_port: int
    redis_session_db: int
    redis_password: str | None
    kafka_brokers: str
    trending_limit: int
    similarity_top_k: int
    warm_user_limit: int
    cleanup_grace_period_seconds: int
    work_mem: str
    statement_timeout_ms: int

    @classmethod
    def from_env(cls) -> "OfflinePipelineConfig":
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://sy:sypw@db:5432/studysphere?schema=public",
            ),
            redis_cache_host=os.getenv("REDIS_CACHE_HOST", "redis-cache"),
            redis_cache_port=int(os.getenv("REDIS_CACHE_PORT", "6379")),
            redis_cache_db=int(os.getenv("REDIS_CACHE_DB", "1")),
            redis_session_host=os.getenv("REDIS_SESSION_HOST", "redis-session"),
            redis_session_port=int(os.getenv("REDIS_SESSION_PORT", "6379")),
            redis_session_db=int(os.getenv("REDIS_SESSION_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            kafka_brokers=os.getenv("KAFKA_BROKERS", "kafka:9092"),
            trending_limit=int(os.getenv("OFFLINE_TRENDING_LIMIT", "50")),
            similarity_top_k=int(os.getenv("OFFLINE_SIMILARITY_TOP_K", "10")),
            warm_user_limit=int(os.getenv("OFFLINE_WARM_USER_LIMIT", "100")),
            cleanup_grace_period_seconds=int(
                os.getenv("OFFLINE_CLEANUP_GRACE_PERIOD_SECONDS", "3600")
            ),
            work_mem=os.getenv("OFFLINE_WORK_MEM", "64MB"),
            statement_timeout_ms=int(
                os.getenv("OFFLINE_STATEMENT_TIMEOUT_MS", "1800000")
            ),
        )
