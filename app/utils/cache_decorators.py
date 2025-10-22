# app/utils/cache_decorators.py
"""Cache decorators for API endpoints."""
import hashlib
import json
import time
from functools import wraps
from typing import Any, Callable, Optional, Union
from datetime import timedelta
from fastapi import Request
from ..core.cache import cache
from .cache_metrics import metrics

def cache_key_generator(prefix: str, *args, **kwargs) -> str:
    """Generate cache key from function arguments."""
    key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(key_data.encode()).hexdigest()

def cached(
    prefix: str,
    expire: Optional[Union[int, timedelta]] = timedelta(minutes=15),
    key_func: Optional[Callable] = None
):
    """Cache decorator for functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_key_generator(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                metrics.record_hit(time.time() - start_time)
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, expire)
            metrics.record_miss()
            return result
        
        return wrapper
    return decorator

def cache_paginated_response(
    prefix: str,
    expire: Optional[Union[int, timedelta]] = timedelta(minutes=10)
):
    """Cache decorator specifically for paginated responses."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Extract pagination and filter params for cache key
            pagination = kwargs.get('pagination')
            filters = {k: v for k, v in kwargs.items() 
                      if k not in ['db', 'pagination'] and v is not None}
            
            cache_key = f"{prefix}:page_{pagination.page}:size_{pagination.size}:{hash(str(sorted(filters.items())))}"
            
            # Try cache first
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                metrics.record_hit(time.time() - start_time)
                return cached_result
            
            # Execute and cache
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, expire)
            metrics.record_miss()
            return result
        
        return wrapper
    return decorator