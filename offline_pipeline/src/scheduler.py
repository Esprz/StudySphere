"""APScheduler service entrypoint for Spec 4 offline jobs."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Callable

from .config import OfflinePipelineConfig
from .service import (
    build_scheduler_job_specs,
    run_cache_warmup,
    run_cf_refresh,
    run_partition_maintenance,
    run_popularity,
    run_version_cleanup,
)


JOB_FUNCTIONS: dict[str, Callable[[OfflinePipelineConfig], dict[str, Any]]] = {
    "run_cf_refresh": run_cf_refresh,
    "run_popularity": run_popularity,
    "run_cache_warmup": run_cache_warmup,
    "run_partition_maintenance": run_partition_maintenance,
}


def register_jobs(scheduler: Any, config: OfflinePipelineConfig) -> None:
    """Register the default cron jobs and deferred version cleanup hooks."""
    for spec in build_scheduler_job_specs():
        func = JOB_FUNCTIONS[spec["func_name"]]
        scheduler.add_job(
            _wrap_job(scheduler, config, func),
            "cron",
            id=spec["job_id"],
            replace_existing=True,
            **spec["trigger"],
        )


def _wrap_job(
    scheduler: Any,
    config: OfflinePipelineConfig,
    func: Callable[[OfflinePipelineConfig], dict[str, Any]],
) -> Callable[[], dict[str, Any]]:
    """Log job output and schedule deferred cleanup after cutover when needed."""
    def runner() -> dict[str, Any]:
        result = func(config)
        print(json.dumps({"scheduled_job": func.__name__, "result": result}, indent=2))
        previous_version = result.get("previous_version")
        feature_name = result.get("feature_name")
        keep_version = result.get("cleanup_keep_version")
        if previous_version and feature_name and keep_version:
            scheduler.add_job(
                lambda: run_version_cleanup(
                    config,
                    feature_name=str(feature_name),
                    keep_version=str(keep_version),
                ),
                "date",
                run_date=datetime.now() + timedelta(seconds=config.cleanup_grace_period_seconds),
                id=f"cleanup-{feature_name}-{keep_version}",
                replace_existing=True,
            )
        return result

    return runner


def main() -> None:
    """Start the blocking APScheduler service."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError as exc:  # pragma: no cover - depends on runtime image
        raise RuntimeError(
            "apscheduler is required to run the offline scheduler service."
        ) from exc

    config = OfflinePipelineConfig.from_env()
    scheduler = BlockingScheduler(timezone="UTC")
    register_jobs(scheduler, config)
    scheduler.start()


if __name__ == "__main__":
    main()
