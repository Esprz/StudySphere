"""High-level orchestration for Spec 4 offline jobs."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from .config import OfflinePipelineConfig
from .database import get_connection
from .feature_store import CF_FEATURE_NAME, TRENDING_FEATURE_NAME, FeatureStore
from .redis_client import CacheRedis
from .tasks import (
    CacheWarmerTask,
    FeatureProcessorTask,
    PartitionMaintenanceTask,
    PopularityAggregatorTask,
    SimilarityBuilderTask,
)


@contextmanager
def open_runtime(config: OfflinePipelineConfig) -> Iterator[tuple[Any, Any, Any, FeatureStore]]:
    """Open DB plus both Redis clients for one offline job execution."""
    cache = CacheRedis(
        host=config.redis_cache_host,
        port=config.redis_cache_port,
        db=config.redis_cache_db,
        password=config.redis_password,
    )
    session_cache = CacheRedis(
        host=config.redis_session_host,
        port=config.redis_session_port,
        db=config.redis_session_db,
        password=config.redis_password,
    )
    with get_connection(config.database_url) as connection:
        feature_store = FeatureStore(
            connection,
            session_cache=session_cache,
            work_mem=config.work_mem,
            statement_timeout_ms=config.statement_timeout_ms,
        )
        yield connection, cache, session_cache, feature_store


def run_cf_refresh(config: OfflinePipelineConfig) -> dict[str, Any]:
    """Build and activate a fresh CF feature version."""
    with open_runtime(config) as (connection, _, _, feature_store):
        processor = FeatureProcessorTask(
            connection,
            feature_store,
            top_k=config.similarity_top_k,
        )
        processor_result = processor.run()
        similarity_result = SimilarityBuilderTask(
            connection,
            top_k=config.similarity_top_k,
        ).run(version=str(processor_result["version"]))
        cutover = feature_store.activate_version(
            feature_name=CF_FEATURE_NAME,
            version=str(processor_result["version"]),
            row_count=int(processor_result["row_count"]),
        )
        return {
            "job": "cf-refresh",
            "version": cutover.version,
            "previous_version": cutover.previous_version,
            "feature_name": CF_FEATURE_NAME,
            "cleanup_keep_version": cutover.version,
            "feature_processor": processor_result,
            "similarity_builder": similarity_result,
        }


def run_popularity(config: OfflinePipelineConfig) -> dict[str, Any]:
    """Build and activate a fresh trending feature version."""
    with open_runtime(config) as (connection, cache, _, feature_store):
        result = PopularityAggregatorTask(
            connection,
            feature_store,
            cache,
            limit=config.trending_limit,
        ).run()
        return {
            **result,
            "feature_name": TRENDING_FEATURE_NAME,
            "cleanup_keep_version": result.get("version"),
        }


def run_cache_warmup(config: OfflinePipelineConfig) -> dict[str, Any]:
    """Warm top-N users in Redis from active offline features."""
    with open_runtime(config) as (connection, cache, _, feature_store):
        return CacheWarmerTask(
            connection,
            feature_store,
            cache,
            user_limit=config.warm_user_limit,
            feed_limit=config.trending_limit,
        ).run()


def run_partition_maintenance(config: OfflinePipelineConfig) -> dict[str, Any]:
    """Create next month's partition if the ETL table is already partitioned."""
    with open_runtime(config) as (connection, _, _, _):
        return PartitionMaintenanceTask(connection).run()


def run_version_cleanup(
    config: OfflinePipelineConfig,
    *,
    feature_name: str,
    keep_version: str,
) -> dict[str, Any]:
    """Remove non-active historical versions after grace period has elapsed."""
    with open_runtime(config) as (connection, _, _, feature_store):
        deleted = feature_store.cleanup_inactive_versions(feature_name, keep_version)
        return {
            "job": "cleanup-versions",
            "feature_name": feature_name,
            "keep_version": keep_version,
            "deleted_rows_by_table": deleted,
        }


def build_scheduler_job_specs() -> list[dict[str, Any]]:
    """Return cron definitions for the default APScheduler service."""
    return [
        {
            "job_id": "cf-refresh",
            "func_name": "run_cf_refresh",
            "trigger": {"hour": 2, "minute": 0},
        },
        {
            "job_id": "popularity",
            "func_name": "run_popularity",
            "trigger": {"minute": 0},
        },
        {
            "job_id": "cache-warmup",
            "func_name": "run_cache_warmup",
            "trigger": {"hour": 5, "minute": 0},
        },
        {
            "job_id": "partition-maintenance",
            "func_name": "run_partition_maintenance",
            "trigger": {"day": 1, "hour": 1, "minute": 0},
        },
    ]
