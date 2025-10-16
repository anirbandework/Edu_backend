# app/core/cache_decorators.py
"""Cache decorators for FastAPI endpoints."""
import functools
import json
from typing import Any, Callable, Optional
from fastapi import Request
from .cache import cache_manager

def cache_response(
    key_prefix: str,
    ttl: int = 300,
    include_params: bool = True,
    include_user: bool = False
):
    """Cache decorator for FastAPI endpoints."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            key_parts = [key_prefix]
            
            if include_params:
                # Add query parameters to key
                for key, value in kwargs.items():
                    if key not in ['request', 'db', 'session']:
                        key_parts.append(f"{key}:{value}")
            
            cache_key = cache_manager.make_key(*key_parts)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache_manager.set(cache_key, result, ttl=ttl)
            return result
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """Decorator to invalidate cache patterns after function execution."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await cache_manager.delete_pattern(pattern)
            return result
        return wrapper
    return decorator