# app/core/cache.py
"""Cache management using Redis."""
import asyncio
import logging
from redis.asyncio import Redis
from .config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.client = None

    async def initialize(self):
        self.client = Redis.from_url(settings.redis_url)
        logger.info("Redis cache connected")

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("Redis cache disconnected")

cache_manager = CacheManager()
