# app/core/cache.py
"""Redis caching implementation."""
import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
import redis.asyncio as redis
from ..core.config import settings

class CacheManager:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection."""
        if not self.redis:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=False
            )
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis:
            await self.connect()
        
        try:
            value = await self.redis.get(key)
            if value:
                return pickle.loads(value)
        except Exception:
            pass
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Set value in cache."""
        if not self.redis:
            await self.connect()
        
        try:
            serialized = pickle.dumps(value)
            if expire:
                if isinstance(expire, timedelta):
                    expire = int(expire.total_seconds())
                return await self.redis.setex(key, expire, serialized)
            else:
                return await self.redis.set(key, serialized)
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis:
            await self.connect()
        
        try:
            return bool(await self.redis.delete(key))
        except Exception:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.redis:
            await self.connect()
        
        try:
            return bool(await self.redis.exists(key))
        except Exception:
            return False

# Global cache instance
cache = CacheManager()

async def get_cache():
    """Dependency to get cache instance."""
    return cache
