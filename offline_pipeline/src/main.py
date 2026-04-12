"""CLI entrypoint for offline batch jobs."""

from __future__ import annotations

import argparse
import json
from typing import Iterable

from .config import OfflinePipelineConfig
from .database import get_connection
from .jobs import CacheWarmupJob, ItemSimilarityJob, TrendingJob, UserSimilarityJob
from .redis_client import CacheRedis


def build_jobs(connection, cache, config: OfflinePipelineConfig):
    return {
        "trending": TrendingJob(connection, cache, config.trending_limit),
        "user-similarity": UserSimilarityJob(connection, cache, config.similarity_top_k),
        "item-similarity": ItemSimilarityJob(connection, cache, config.similarity_top_k),
        "cache-warmup": CacheWarmupJob(
            connection,
            cache,
            config.warm_user_limit,
            config.trending_limit,
        ),
    }


def run_job_names(job_names: Iterable[str]) -> int:
    config = OfflinePipelineConfig.from_env()
    cache = CacheRedis(
        host=config.redis_cache_host,
        port=config.redis_cache_port,
        db=config.redis_cache_db,
        password=config.redis_password,
    )

    with get_connection(config.database_url) as connection:
        jobs = build_jobs(connection, cache, config)
        results = []
        for job_name in job_names:
            result = jobs[job_name].run()
            results.append(result)

    print(json.dumps({"results": results}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="StudySphere offline pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("healthcheck", help="Validate DB and Redis connectivity")
    run_parser = subparsers.add_parser("run", help="Run a single offline job")
    run_parser.add_argument(
        "job_name",
        choices=["trending", "user-similarity", "item-similarity", "cache-warmup"],
    )
    subparsers.add_parser("run-all", help="Run all offline jobs")

    args = parser.parse_args()
    config = OfflinePipelineConfig.from_env()

    if args.command == "healthcheck":
        cache = CacheRedis(
            host=config.redis_cache_host,
            port=config.redis_cache_port,
            db=config.redis_cache_db,
            password=config.redis_password,
        )
        with get_connection(config.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        print(
            json.dumps(
                {
                    "database": "ok",
                    "redis_cache": "ok" if cache.ping() else "error",
                    "kafka": config.kafka_brokers,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "run":
        return run_job_names([args.job_name])

    if args.command == "run-all":
        return run_job_names(
            ["trending", "user-similarity", "item-similarity", "cache-warmup"]
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

