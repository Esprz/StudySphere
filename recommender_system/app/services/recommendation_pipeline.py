import logging
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

from .recall.base import RecallBase
from .filters.base import FilterBase
from .diversity.base import DiversityBase
from ..config import redis_config

logger = logging.getLogger(__name__)


class RecommendationPipeline:

    def __init__(
        self,
        recall_services: List[RecallBase],
        filter_services: List[FilterBase],
        diversity_service: DiversityBase,
    ):
        self.recall_services = recall_services
        self.filter_services = filter_services
        self.diversity_service = diversity_service
        self.redis = redis_config

    async def recommend(
        self,
        user_id: str,
        context: Dict[str, Any],
        limit: int = 20,
        detailed: bool = False,
        use_cache: bool = True,
    ) -> Dict[str, Any]:

        # Generate cache key
        cache_key = self._generate_cache_key(user_id, context, limit)
        
        # Try to get from cache first
        if use_cache:
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
        filtered_candidates = self._apply_filters(user_id, candidates, context)
        metrics["filter_time"] = time.time() - filter_start_time
        metrics["filtered_candidates"] = len(filtered_candidates)

        diversity_start_time = time.time()
        diversified_results = self._apply_diversity(
            user_id, filtered_candidates, context, limit
        )
        metrics["diversity_time"] = time.time() - diversity_start_time

        metrics["total_time"] = time.time() - start_time

        response = {"recommendations": diversified_results, "user_id": user_id, "cached": False}

        if detailed:
            response["metrics"] = metrics

        # Cache the result
        if use_cache:
            try:
                await self.redis.set(
                    cache_key, 
                    response, 
                    ttl=self.redis.CACHE_TTL["recommendations"]
                )
                logger.info(f"Cached recommendations for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")

        return response

    async def _get_candidates_from_all_sources(
        self, user_id: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        all_candidates = []
        source_metrics = {}

        if await self._is_cold_start_user(user_id):
            self.recall_services = self.recall_services.filter(
                lambda svc: svc.name == "cold_start" or svc.name == "trending_posts"
            )
            logger.info(f"User {user_id} identified as cold start user.")

        for recall_service in self.recall_services:
            source_name = recall_service.name
            logger.info(f"Getting candidates from {source_name}")

            try:
                start_time = time.time()
                candidates = recall_service.get_candidates(user_id, context)
                elapsed_time = time.time() - start_time

                source_metrics[source_name] = {
                    "count": len(candidates),
                    "time": elapsed_time,
                }

                for candidate in candidates:
                    if "source" not in candidate:
                        candidate["source"] = source_name

                all_candidates.extend(candidates)
                logger.info(f"Got {len(candidates)} candidates from {source_name}")

            except Exception as e:
                logger.error(
                    f"Failed to get candidates from {source_name}: {e}", exc_info=True
                )

        unique_candidates = self._deduplicate_candidates(all_candidates)

        logger.info(f"Total unique candidates: {len(unique_candidates)}")
        return unique_candidates

    def _deduplicate_candidates(
        self, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        item_map = {}

        for candidate in candidates:
            item_id = candidate.get("item_id")
            if not item_id:
                continue

            score = candidate.get("score", 0.0)

            if item_id not in item_map or score > item_map[item_id].get("score", 0.0):
                item_map[item_id] = candidate

        unique_candidates = list(item_map.values())

        return unique_candidates

    def _apply_filters(
        self, user_id: str, candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        filtered = candidates

        for filter_service in self.filter_services:
            try:
                filter_name = filter_service.__class__.__name__
                logger.info(f"Applying filter: {filter_name}")

                before_count = len(filtered)
                filtered = filter_service.filter_candidates(user_id, filtered, context)
                after_count = len(filtered)

                logger.info(
                    f"{filter_name} filtered out {before_count - after_count} candidates, {after_count} remaining"
                )

            except Exception as e:
                logger.error(f"Failed to apply filter: {e}", exc_info=True)

        return filtered

    def _apply_diversity(
        self,
        user_id: str,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        try:
            diversified = self.diversity_service.diversify(
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

    def _generate_cache_key(self, user_id: str, context: Dict[str, Any], limit: int) -> str:
        """Generate a unique cache key for recommendations"""
        # Create a hash of the context to ensure cache key uniqueness
        context_str = json.dumps(context, sort_keys=True)
        context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
        return f"rec:user:{user_id}:{context_hash}:{limit}"

    async def _is_cold_start_user(self, user_id: str) -> bool:
        """Check if user is cold start using Redis cache first"""
        cache_key = f"cold_start:{user_id}"
        
        try:
            # Try to get from cache first
            cached_status = await self.redis.get(cache_key)
            if cached_status is not None:
                return cached_status
            
            # If not in cache, check database
            interaction_count = self.postgres_store.get_user_interaction_count(user_id)
            is_cold_start = interaction_count < 5
            
            # Cache the result
            await self.redis.set(
                cache_key, 
                is_cold_start, 
                ttl=self.redis.CACHE_TTL["cold_start"]
            )
            
            return is_cold_start
            
        except Exception as e:
            logger.warning(f"Cold start check failed, falling back to DB: {e}")
            # Fallback to database check
            interaction_count = self.postgres_store.get_user_interaction_count(user_id)
            return interaction_count < 5

    async def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cached recommendations for a user"""
        try:
            pattern = f"rec:user:{user_id}:*"
            deleted_count = await self.redis.invalidate_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} cache entries for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache for user {user_id}: {e}")

    async def warm_up_cache(self, user_ids: List[str], context: Dict[str, Any] = None) -> None:
        """Pre-warm cache for multiple users"""
        if context is None:
            context = {}
            
        logger.info(f"Warming up cache for {len(user_ids)} users")
        
        for user_id in user_ids:
            try:
                # Generate recommendations and cache them
                await self.recommend(user_id, context, limit=20, use_cache=True)
            except Exception as e:
                logger.error(f"Failed to warm up cache for user {user_id}: {e}")
