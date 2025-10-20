import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
import redis.asyncio as redis
from loguru import logger


class RedisConfig:
    """Redis configuration and connection management for recommender system"""

    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.password = os.getenv("REDIS_PASSWORD")
        self.db = int(os.getenv("REDIS_DB", "1"))  # Use DB 1 for recommender
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))

        # Connection pool settings
        self.connection_pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            password=self.password,
            db=self.db,
            max_connections=self.max_connections,
            retry_on_timeout=True,
            health_check_interval=30,
        )

        self.redis = redis.Redis(connection_pool=self.connection_pool)

        # Cache TTL settings (in seconds) - Optimized for ML workloads
        self.CACHE_TTL = {
            "recommendations": 1800,  # 30 minutes - user recommendations
            "user_similarities": 3600,  # 1 hour - user-user similarities
            "item_similarities": 3600,  # 1 hour - item-item similarities
            "trending_posts": 900,  # 15 minutes - trending content
            "user_embeddings": 7200,  # 2 hours - user feature vectors
            "content_embeddings": 7200,  # 2 hours - content feature vectors
            "user_interactions": 1800,  # 30 minutes - user behavior data
            "cold_start": 3600,  # 1 hour - cold start user status
            "precomputed": 14400,  # 4 hours - precomputed results
        }

    async def ping(self) -> bool:
        """Check Redis connection health"""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a key-value pair with optional TTL"""
        try:
            serialized_value = json.dumps(value, default=str)
            if ttl:
                return await self.redis.setex(key, ttl, serialized_value)
            else:
                return await self.redis.set(key, serialized_value)
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key"""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None

    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """Get multiple values by keys"""
        try:
            values = await self.redis.mget(keys)
            return [json.loads(v) if v else None for v in values]
        except Exception as e:
            logger.error(f"Failed to mget keys: {e}")
            return [None] * len(keys)

    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple key-value pairs"""
        try:
            serialized_mapping = {
                k: json.dumps(v, default=str) for k, v in mapping.items()
            }

            if await self.redis.mset(serialized_mapping):
                if ttl:
                    # Set TTL for all keys
                    pipeline = self.redis.pipeline()
                    for key in mapping.keys():
                        pipeline.expire(key, ttl)
                    await pipeline.execute()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to mset: {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys"""
        try:
            return await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check key existence: {e}")
            return False

    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        try:
            return await self.redis.keys(pattern)
        except Exception as e:
            logger.error(f"Failed to get keys with pattern {pattern}: {e}")
            return []

    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys = await self.keys(pattern)
            if keys:
                return await self.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate pattern {pattern}: {e}")
            return 0

    async def cache_or_fetch(
        self, key: str, fetch_func, ttl: Optional[int] = None, *args, **kwargs
    ) -> Any:
        """Cache or fetch pattern - get from cache or execute fetch function"""
        try:
            # Try to get from cache first
            cached_value = await self.get(key)
            if cached_value is not None:
                logger.debug(f"Cache HIT for key: {key}")
                return cached_value

            logger.debug(f"Cache MISS for key: {key}")

            # Fetch from source
            if asyncio.iscoroutinefunction(fetch_func):
                value = await fetch_func(*args, **kwargs)
            else:
                value = fetch_func(*args, **kwargs)

            # Cache the result
            cache_ttl = ttl or self.CACHE_TTL.get("recommendations", 1800)
            await self.set(key, value, cache_ttl)

            return value

        except Exception as e:
            logger.error(f"Cache or fetch failed for key {key}: {e}")
            # Fallback to direct fetch
            if asyncio.iscoroutinefunction(fetch_func):
                return await fetch_func(*args, **kwargs)
            else:
                return fetch_func(*args, **kwargs)

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        try:
            # Get Redis info
            info = await self.redis.info()

            # Count keys by pattern
            patterns = {
                "recommendations": "rec:user:*",
                "user_similarities": "sim:user:*",
                "item_similarities": "sim:item:*",
                "embeddings": "emb:*",
                "interactions": "int:user:*",
                "trending": "trending:*",
                "cold_start": "cold_start:*",
                "precomputed": "precomp:*",
            }

            stats = {}
            for name, pattern in patterns.items():
                keys = await self.keys(pattern)
                stats[name] = len(keys)

            # Calculate hit rate
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            hit_rate = (hits / max(hits + misses, 1)) * 100

            stats.update(
                {
                    "redis_memory": info.get("used_memory_human", "Unknown"),
                    "redis_connections": info.get("connected_clients", 0),
                    "redis_hit_rate": round(hit_rate, 2),
                    "total_keys": sum(stats.values()),
                    "redis_version": info.get("redis_version", "Unknown"),
                }
            )

            return stats

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close Redis connection"""
        try:
            await self.redis.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Failed to close Redis connection: {e}")


# Global Redis instance
redis_config = RedisConfig()
