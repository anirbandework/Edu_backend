# app/routers/cache_test.py
"""Cache testing endpoints."""
from fastapi import APIRouter
from app.core.cache import cache_manager
import time

router = APIRouter(prefix="/cache", tags=["Cache"])

@router.get("/test")
async def test_cache():
    """Test cache set/get operations."""
    key = "test:cache:demo"
    test_data = {"timestamp": time.time(), "message": "Cache test successful"}
    
    # Set cache
    set_success = await cache_manager.set(key, test_data, ttl=60)
    
    # Get cache
    cached_data = await cache_manager.get(key)
    
    return {
        "set_success": set_success,
        "cached_data": cached_data,
        "cache_working": cached_data == test_data
    }

@router.delete("/clear/{key}")
async def clear_cache(key: str):
    """Clear specific cache key."""
    success = await cache_manager.delete(key)
    return {"key": key, "deleted": success}