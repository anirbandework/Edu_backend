# app/core/cache.py
"""Cache management using Redis."""
import asyncio
import logging
import json
from typing import Any, Optional
from redis.asyncio import Redis
from .config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.client = None
        self.default_ttl = 300  # 5 minutes

    async def initialize(self):
        self.client = Redis.from_url(settings.redis_url)
        logger.info("Redis cache connected")

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("Redis cache disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.client:
            return None
        try:
            value = await self.client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache"""
        if not self.client:
            return False
        try:
            ttl = ttl or self.default_ttl
            await self.client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.client:
            return False
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> bool:
        """Delete keys matching pattern"""
        if not self.client:
            return False
        try:
            keys = await self.client.keys(pattern)
            if keys:
                await self.client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return False

    def make_key(self, prefix: str, *args) -> str:
        """Generate cache key"""
        return f"{prefix}:" + ":".join(str(arg) for arg in args)

cache_manager = CacheManager()
