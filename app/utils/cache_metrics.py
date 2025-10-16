# app/utils/cache_metrics.py
"""Cache performance monitoring."""
import time
from typing import Dict, Any
from ..core.cache import cache

class CacheMetrics:
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.total_requests = 0
        self.total_time_saved = 0.0
    
    def record_hit(self, time_saved: float = 0.0):
        self.hits += 1
        self.total_requests += 1
        self.total_time_saved += time_saved
    
    def record_miss(self):
        self.misses += 1
        self.total_requests += 1
    
    def get_stats(self) -> Dict[str, Any]:
        hit_rate = (self.hits / self.total_requests * 100) if self.total_requests > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "total_time_saved_seconds": round(self.total_time_saved, 3)
        }

# Global metrics instance
metrics = CacheMetrics()

async def get_cache_info():
    """Get Redis cache information."""
    if not cache.redis:
        await cache.connect()
    
    try:
        info = await cache.redis.info()
        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "total_commands_processed": info.get("total_commands_processed", 0)
        }
    except Exception as e:
        return {"error": str(e)}