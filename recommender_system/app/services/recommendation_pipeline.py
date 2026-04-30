import asyncio
import logging
from typing import List, Dict, Any
import time
import hashlib
import json

from .recall.base import RecallBase
from .filters.base import FilterBase
from .diversity.base import DiversityBase

logger = logging.getLogger(__name__)


class RecommendationPipeline:
    def __init__(
        self,
        recall_services: List[RecallBase],
        filter_services: List[FilterBase],
        diversity_service: DiversityBase,
        postgres_store=None,
        redis=None,
        session_redis=None,
    ):
        self.recall_services = recall_services
        self.filter_services = filter_services
        self.diversity_service = diversity_service
        self.postgres_store = postgres_store
        self.redis = redis
        self.session_redis = session_redis

    async def recommend(
        self,
        user_id: str,
        context: Dict[str, Any] = None,
        limit: int = 20,
        detailed: bool = False,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        if context is None:
            context = {}

        cache_key = self._generate_cache_key(user_id, context, limit)

        if use_cache and self.redis:
            try:
                cached_result = await self.redis.get(cache_key)
                if cached_result:
                    logger.info(f"Cache HIT for user {user_id}")
                    cached_result["cached"] = True
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")

        start_time = time.time()
        metrics = {}

        context = await self._prepare_context(user_id, context)

        recall_start_time = time.time()
        candidates, source_metrics = await self._get_candidates_from_all_sources(
            user_id, context
        )
        metrics["recall_time"] = time.time() - recall_start_time
        metrics["total_candidates"] = len(candidates)
        metrics["source_metrics"] = source_metrics

        filter_start_time = time.time()
        filtered_candidates = await self._apply_filters(user_id, candidates, context)
        metrics["filter_time"] = time.time() - filter_start_time
        metrics["filtered_candidates"] = len(filtered_candidates)

        diversity_start_time = time.time()
        diversified_results = await self._apply_diversity(
            user_id, filtered_candidates, context, limit
        )
        metrics["diversity_time"] = time.time() - diversity_start_time

        metrics["total_time"] = time.time() - start_time

        response = {
            "recommendations": diversified_results,
            "user_id": user_id,
            "cached": False,
        }

        if detailed:
            response["metrics"] = metrics

        if self.redis:
            try:
                await self.redis.set(
                    cache_key, response, ttl=self.redis.CACHE_TTL["recommendations"]
                )

                feed_key = f"rec:feed:{user_id}"
                feed_entries = [
                    {
                        "post_id": recommendation["item_id"],
                        "score": float(recommendation.get("score", 0.0)),
                        "source": recommendation.get("source", "unknown"),
                    }
                    for recommendation in diversified_results
                    if recommendation.get("item_id")
                ]
                await self.redis.set(
                    feed_key,
                    feed_entries,
                    ttl=self.redis.CACHE_TTL["recommendations"],
                )

                logger.info(f"Cached recs + feed for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")

        return response

    async def _get_candidates_from_all_sources(
        self, user_id: str, context: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        all_candidates = []
        source_metrics = {}

        interaction_count = int(context.get("interaction_count", 0))
        active_services = self._select_recall_services(interaction_count)
        logger.info(
            f"User {user_id} interaction_count={interaction_count}, "
            f"using sources={[svc.name for svc in active_services]}"
        )

        recall_timeout = 0.5

        results = await asyncio.gather(
            *[
                self._run_recall_service(
                    svc=svc,
                    user_id=user_id,
                    context=context,
                    timeout=recall_timeout,
                )
                for svc in active_services
            ],
            return_exceptions=True,
        )

        for svc, result in zip(active_services, results):
            if isinstance(result, Exception):
                logger.error(f"Recall source {svc.name} failed: {result}")
                source_metrics[svc.name] = {
                    "count": 0,
                    "latency_ms": None,
                    "status": "failed",
                }
                continue
            candidates = result.get("candidates", [])
            source_metrics[svc.name] = {
                "count": len(candidates),
                "latency_ms": result.get("latency_ms"),
                "status": result.get("status", "ok"),
            }
            all_candidates.extend(candidates)
            logger.info(
                f"Got {len(candidates)} candidates from {svc.name} "
                f"in {result.get('latency_ms')}ms"
            )

        logger.info(f"Total raw candidates: {len(all_candidates)}")
        return all_candidates, source_metrics

    async def _apply_filters(
        self, user_id: str, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        filtered = candidates

        for filter_service in self.filter_services:
            try:
                filter_name = filter_service.name
                logger.info(f"Applying filter: {filter_name}")

                before_count = len(filtered)
                filtered = await filter_service.filter_candidates(
                    user_id, filtered, context
                )
                after_count = len(filtered)

                logger.info(
                    f"{filter_name}: {before_count} -> {after_count} candidates"
                )

            except Exception as e:
                logger.error(f"Failed to apply filter: {e}", exc_info=True)

        return filtered

    async def _apply_diversity(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        try:
            diversified = await self.diversity_service.diversify(
                user_id, candidates, context, limit
            )
            logger.info(f"Diversity applied, {len(diversified)} results")
            return diversified

        except Exception as e:
            logger.error(f"Failed to apply diversity: {e}", exc_info=True)
            sorted_candidates = sorted(
                candidates, key=lambda x: x.get("score", 0.0), reverse=True
            )
            return sorted_candidates[:limit]

    def _generate_cache_key(
        self, user_id: str, context: Dict[str, Any], limit: int
    ) -> str:
        context_str = json.dumps(context, sort_keys=True)
        context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
        return f"rec:user:{user_id}:{context_hash}:{limit}"

    async def _is_cold_start_user(self, user_id: str) -> bool:
        return await self._get_interaction_count(user_id) < 5

    async def _get_interaction_count(self, user_id: str) -> int:
        cache_key = f"rec:cold:{user_id}"

        try:
            if self.redis:
                cached_status = await self.redis.get(cache_key)
                if cached_status is not None:
                    return int(cached_status)

            if self.postgres_store is None:
                return 0

            interaction_count = self.postgres_store.get_user_interaction_count(user_id)

            if self.redis:
                await self.redis.set(
                    cache_key,
                    interaction_count,
                    ttl=self.redis.CACHE_TTL["cold_start"],
                )

            return interaction_count

        except Exception as e:
            logger.warning(f"Cold start check failed, defaulting to 0: {e}")
            return 0

    async def _prepare_context(
        self, user_id: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        prepared = dict(context)
        prepared["interaction_count"] = await self._get_interaction_count(user_id)
        prepared["cf_version"] = await self._get_feature_version(
            feature_name="cf", redis_key="offline:cf:active_version"
        )
        prepared["trending_version"] = await self._get_feature_version(
            feature_name="trending", redis_key="offline:trending:active_version"
        )
        return prepared

    async def _get_feature_version(self, feature_name: str, redis_key: str) -> str | None:
        try:
            if self.session_redis:
                cached = await self.session_redis.get(redis_key)
                if isinstance(cached, str) and cached:
                    return cached
        except Exception as e:
            logger.warning(f"Failed to read {redis_key} from session redis: {e}")

        if self.postgres_store:
            return self.postgres_store.get_active_feature_version(feature_name, fallback=None)
        return None

    def _select_recall_services(self, interaction_count: int) -> List[RecallBase]:
        if interaction_count <= 0:
            allowed = {"cold_start_interest", "trending"}
        elif interaction_count <= 5:
            allowed = {"cold_start_interest", "content_based", "trending"}
        else:
            allowed = None

        if allowed is None:
            return self.recall_services
        return [svc for svc in self.recall_services if svc.name in allowed]

    async def _run_recall_service(
        self,
        svc: RecallBase,
        user_id: str,
        context: Dict[str, Any],
        timeout: float,
    ) -> Dict[str, Any]:
        start = time.time()
        try:
            candidates = await asyncio.wait_for(
                svc.get_candidates(user_id, context), timeout=timeout
            )
            return {
                "candidates": candidates,
                "latency_ms": round((time.time() - start) * 1000, 2),
                "status": "ok",
            }
        except asyncio.TimeoutError:
            logger.warning(f"Recall source {svc.name} timed out after {timeout}s")
            return {
                "candidates": [],
                "latency_ms": round((time.time() - start) * 1000, 2),
                "status": "timeout",
            }

    async def invalidate_user_cache(self, user_id: str) -> None:
        if not self.redis:
            return
        try:
            pattern = f"rec:user:{user_id}:*"
            deleted_count = await self.redis.invalidate_pattern(pattern)
            deleted_count += await self.redis.delete(f"rec:feed:{user_id}")
            deleted_count += await self.redis.delete(f"rec:cold:{user_id}")
            deleted_count += await self.redis.delete(f"rec:seen:{user_id}")
            logger.info(f"Invalidated {deleted_count} cache entries for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache for user {user_id}: {e}")
