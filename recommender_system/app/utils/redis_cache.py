"""
Redis caching utilities for the recommender system
"""

import json
import hashlib
from typing import Any, Dict, List, Optional, Callable
from loguru import logger
from ..config import redis_config


class RedisCache:
    """High-level Redis caching utilities for recommender system"""

    def __init__(self):
        self.redis = redis_config

    async def get_or_set(
        self, key: str, fetch_func: Callable, ttl: Optional[int] = None, *args, **kwargs
    ) -> Any:
        """Get value from cache or fetch and cache it"""
        return await self.redis.cache_or_fetch(key, fetch_func, ttl, *args, **kwargs)

    async def cache_user_recommendations(
        self,
        user_id: str,
        recommendations: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
        limit: int = 20,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache user recommendations with context"""
        cache_key = self._generate_recommendation_key(user_id, context, limit)
        return await self.redis.set(
            cache_key, recommendations, ttl or self.redis.CACHE_TTL["recommendations"]
        )

    async def get_user_recommendations(
        self, user_id: str, context: Dict[str, Any] = None, limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached user recommendations"""
        cache_key = self._generate_recommendation_key(user_id, context, limit)
        return await self.redis.get(cache_key)

    async def cache_user_similarities(
        self, user_id: str, similarities: Dict[str, float], ttl: Optional[int] = None
    ) -> bool:
        """Cache user similarity scores"""
        cache_key = f"sim:user:{user_id}"
        return await self.redis.set(
            cache_key, similarities, ttl or self.redis.CACHE_TTL["user_similarities"]
        )

    async def get_user_similarities(self, user_id: str) -> Optional[Dict[str, float]]:
        """Get cached user similarities"""
        cache_key = f"sim:user:{user_id}"
        return await self.redis.get(cache_key)

    async def cache_item_similarities(
        self, item_id: str, similarities: Dict[str, float], ttl: Optional[int] = None
    ) -> bool:
        """Cache item similarity scores"""
        cache_key = f"sim:item:{item_id}"
        return await self.redis.set(
            cache_key, similarities, ttl or self.redis.CACHE_TTL["item_similarities"]
        )

    async def get_item_similarities(self, item_id: str) -> Optional[Dict[str, float]]:
        """Get cached item similarities"""
        cache_key = f"sim:item:{item_id}"
        return await self.redis.get(cache_key)

    async def cache_trending_posts(
        self,
        posts: List[Dict[str, Any]],
        category: str = "general",
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache trending posts"""
        cache_key = f"trending:{category}"
        return await self.redis.set(
            cache_key, posts, ttl or self.redis.CACHE_TTL["trending_posts"]
        )

    async def get_trending_posts(
        self, category: str = "general"
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached trending posts"""
        cache_key = f"trending:{category}"
        return await self.redis.get(cache_key)

    async def cache_user_embeddings(
        self, user_id: str, embeddings: List[float], ttl: Optional[int] = None
    ) -> bool:
        """Cache user embeddings"""
        cache_key = f"emb:user:{user_id}"
        return await self.redis.set(
            cache_key, embeddings, ttl or self.redis.CACHE_TTL["user_embeddings"]
        )

    async def get_user_embeddings(self, user_id: str) -> Optional[List[float]]:
        """Get cached user embeddings"""
        cache_key = f"emb:user:{user_id}"
        return await self.redis.get(cache_key)

    async def cache_content_embeddings(
        self, content_id: str, embeddings: List[float], ttl: Optional[int] = None
    ) -> bool:
        """Cache content embeddings"""
        cache_key = f"emb:content:{content_id}"
        return await self.redis.set(
            cache_key, embeddings, ttl or self.redis.CACHE_TTL["content_embeddings"]
        )

    async def get_content_embeddings(self, content_id: str) -> Optional[List[float]]:
        """Get cached content embeddings"""
        cache_key = f"emb:content:{content_id}"
        return await self.redis.get(cache_key)

    async def cache_user_interactions(
        self,
        user_id: str,
        interactions: List[Dict[str, Any]],
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache user interaction history"""
        cache_key = f"int:user:{user_id}"
        return await self.redis.set(
            cache_key, interactions, ttl or self.redis.CACHE_TTL["user_interactions"]
        )

    async def get_user_interactions(
        self, user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached user interactions"""
        cache_key = f"int:user:{user_id}"
        return await self.redis.get(cache_key)

    async def invalidate_user_data(self, user_id: str) -> int:
        """Invalidate all cached data for a user"""
        patterns = [
            f"rec:user:{user_id}:*",
            f"sim:user:{user_id}",
            f"emb:user:{user_id}",
            f"int:user:{user_id}",
            f"cold_start:{user_id}",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.redis.invalidate_pattern(pattern)
            total_deleted += deleted

        logger.info(f"Invalidated {total_deleted} cache entries for user {user_id}")
        return total_deleted

    async def invalidate_content_data(self, content_id: str) -> int:
        """Invalidate all cached data for content"""
        patterns = [f"sim:item:{content_id}", f"emb:content:{content_id}"]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.redis.invalidate_pattern(pattern)
            total_deleted += deleted

        logger.info(
            f"Invalidated {total_deleted} cache entries for content {content_id}"
        )
        return total_deleted

    async def warm_up_recommendations(
        self, user_ids: List[str], context: Dict[str, Any] = None, limit: int = 20
    ) -> Dict[str, bool]:
        """Pre-warm recommendation cache for multiple users"""
        results = {}

        for user_id in user_ids:
            try:
                # Check if already cached
                cached = await self.get_user_recommendations(user_id, context, limit)
                if cached:
                    results[user_id] = True
                    continue

                # This would typically call the recommendation pipeline
                # For now, we'll just mark as attempted
                results[user_id] = False

            except Exception as e:
                logger.error(f"Failed to warm up cache for user {user_id}: {e}")
                results[user_id] = False

        return results

    def _generate_recommendation_key(
        self, user_id: str, context: Dict[str, Any] = None, limit: int = 20
    ) -> str:
        """Generate cache key for recommendations"""
        if context is None:
            context = {}

        # Create a hash of the context for uniqueness
        context_str = json.dumps(context, sort_keys=True)
        context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]

        return f"rec:user:{user_id}:{context_hash}:{limit}"

    async def get_cache_health(self) -> Dict[str, Any]:
        """Get cache health and statistics"""
        try:
            is_healthy = await self.redis.ping()
            stats = await self.redis.get_cache_stats()

            return {
                "healthy": is_healthy,
                "stats": stats,
                "status": "connected" if is_healthy else "disconnected",
            }
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {"healthy": False, "error": str(e), "status": "error"}


# Global cache instance
cache = RedisCache()
