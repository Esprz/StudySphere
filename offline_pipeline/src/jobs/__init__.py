"""Offline job registry."""

from .cache_warmup import CacheWarmupJob
from .item_similarity import ItemSimilarityJob
from .trending import TrendingJob
from .user_similarity import UserSimilarityJob

__all__ = [
    "CacheWarmupJob",
    "ItemSimilarityJob",
    "TrendingJob",
    "UserSimilarityJob",
]

