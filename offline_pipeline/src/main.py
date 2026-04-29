"""CLI entrypoint for offline batch jobs and one-shot Spec 4 orchestration."""

from __future__ import annotations

import argparse
import json
from typing import Iterable

from .config import OfflinePipelineConfig
from .service import (
    open_runtime,
    run_cache_warmup,
    run_cf_refresh,
    run_partition_maintenance,
    run_popularity,
    run_version_cleanup,
)


def run_job_names(job_names: Iterable[str]) -> int:
    config = OfflinePipelineConfig.from_env()
    jobs = {
        "cf-refresh": lambda: run_cf_refresh(config),
        "popularity": lambda: run_popularity(config),
        "cache-warmup": lambda: run_cache_warmup(config),
        "partition-maintenance": lambda: run_partition_maintenance(config),
        # Compatibility aliases for the previous lighter CLI.
        "trending": lambda: run_popularity(config),
        "user-similarity": lambda: run_cf_refresh(config),
        "item-similarity": lambda: run_cf_refresh(config),
    }
    results = []
    for job_name in job_names:
        result = jobs[job_name]()
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
        choices=[
            "cf-refresh",
            "popularity",
            "cache-warmup",
            "partition-maintenance",
            "trending",
            "user-similarity",
            "item-similarity",
        ],
    )
    subparsers.add_parser("run-all", help="Run all offline jobs")
    cleanup_parser = subparsers.add_parser("cleanup-versions", help="Delete non-active historical versions")
    cleanup_parser.add_argument("feature_name", choices=["cf", "trending"])
    cleanup_parser.add_argument("keep_version")

    args = parser.parse_args()
    config = OfflinePipelineConfig.from_env()

    if args.command == "healthcheck":
        with open_runtime(config) as (connection, cache, session_cache, _):
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        print(
            json.dumps(
                {
                    "database": "ok",
                    "redis_cache": "ok" if cache.ping() else "error",
                    "redis_session": "ok" if session_cache.ping() else "error",
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
            ["cf-refresh", "popularity", "cache-warmup", "partition-maintenance"]
        )
    if args.command == "cleanup-versions":
        print(
            json.dumps(
                run_version_cleanup(
                    config,
                    feature_name=args.feature_name,
                    keep_version=args.keep_version,
                ),
                indent=2,
            )
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
