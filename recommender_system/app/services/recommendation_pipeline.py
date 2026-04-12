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
    ):
        self.recall_services = recall_services
        self.filter_services = filter_services
        self.diversity_service = diversity_service
        self.postgres_store = postgres_store
        self.redis = redis

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

        recall_start_time = time.time()
        candidates = await self._get_candidates_from_all_sources(user_id, context)
        metrics["recall_time"] = time.time() - recall_start_time
        metrics["total_candidates"] = len(candidates)

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
    ) -> List[Dict[str, Any]]:
        all_candidates = []
        source_metrics = {}

        is_cold_start = await self._is_cold_start_user(user_id)

        if is_cold_start:
            active_services = [
                svc
                for svc in self.recall_services
                if svc.name in ("cold_start", "trending_posts", "content_based")
            ]
            logger.info(
                f"User {user_id} is cold-start, using {len(active_services)} sources"
            )
        else:
            active_services = self.recall_services

        RECALL_TIMEOUT = 2.0

        results = await asyncio.gather(
            *[
                asyncio.wait_for(
                    svc.get_candidates(user_id, context), timeout=RECALL_TIMEOUT
                )
                for svc in active_services
            ],
            return_exceptions=True,
        )

        for svc, result in zip(active_services, results):
            if isinstance(result, Exception):
                logger.error(f"Recall source {svc.name} failed: {result}")
                continue
            source_metrics[svc.name] = {"count": len(result)}
            all_candidates.extend(result)
            logger.info(f"Got {len(result)} candidates from {svc.name}")

        unique_candidates = self._deduplicate_candidates(all_candidates)

        logger.info(f"Total unique candidates: {len(unique_candidates)}")
        return unique_candidates

    def _deduplicate_candidates(
        self, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        item_map: Dict[str, Dict[str, Any]] = {}

        for candidate in candidates:
            item_id = candidate.get("item_id")
            if not item_id:
                continue

            score = candidate.get("score", 0.0)

            if item_id not in item_map or score > item_map[item_id].get("score", 0.0):
                item_map[item_id] = candidate

        return list(item_map.values())

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
        cache_key = f"cold_start:{user_id}"

        try:
            if self.redis:
                cached_status = await self.redis.get(cache_key)
                if cached_status is not None:
                    return cached_status

            if self.postgres_store is None:
                return True

            interaction_count = self.postgres_store.get_user_interaction_count(user_id)
            is_cold_start = interaction_count < 5

            if self.redis:
                await self.redis.set(
                    cache_key, is_cold_start, ttl=self.redis.CACHE_TTL["cold_start"]
                )

            return is_cold_start

        except Exception as e:
            logger.warning(f"Cold start check failed, defaulting to True: {e}")
            return True

    async def invalidate_user_cache(self, user_id: str) -> None:
        if not self.redis:
            return
        try:
            pattern = f"rec:user:{user_id}:*"
            deleted_count = await self.redis.invalidate_pattern(pattern)
            deleted_count += await self.redis.delete(f"rec:feed:{user_id}")
            logger.info(f"Invalidated {deleted_count} cache entries for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache for user {user_id}: {e}")
