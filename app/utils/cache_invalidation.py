# app/utils/cache_invalidation.py
"""Cache invalidation utilities."""
from typing import List
from ..core.cache import cache

async def invalidate_tenant_cache(tenant_id: str = None):
    """Invalidate tenant-related cache entries."""
    patterns = ["tenants:*"]
    if tenant_id:
        patterns.append(f"tenant:{tenant_id}:*")
    
    for pattern in patterns:
        await cache.delete(pattern)

async def invalidate_student_cache(tenant_id: str = None, class_id: str = None):
    """Invalidate student-related cache entries."""
    patterns = ["students:*"]
    if tenant_id:
        patterns.append(f"students:tenant:{tenant_id}:*")
    if class_id:
        patterns.append(f"students:class:{class_id}:*")
    
    for pattern in patterns:
        await cache.delete(pattern)

async def invalidate_teacher_cache(tenant_id: str = None):
    """Invalidate teacher-related cache entries."""
    patterns = ["teachers:*"]
    if tenant_id:
        patterns.append(f"teachers:tenant:{tenant_id}:*")
    
    for pattern in patterns:
        await cache.delete(pattern)

async def invalidate_all_cache():
    """Clear all cache entries (use with caution)."""
    if cache.redis:
        await cache.redis.flushdb()