import redis
import json
import logging
from typing import Any, Optional
from .production_config import production_settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = redis.from_url(production_settings.REDIS_URL)
    
    async def get(self, key: str) -> Optional[Any]:
        try:
            value = self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        try:
            ttl = ttl or production_settings.CACHE_TTL
            self.redis_client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

cache_service = CacheService()