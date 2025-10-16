# app/utils/pagination.py
"""Pagination utilities for FastAPI endpoints."""
from typing import Any, Dict, List, Optional, Type
from fastapi import Query
from pydantic import BaseModel

class PaginationParams:
    """Dependency for pagination query parameters."""
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Items per page")
    ):
        self.page = page
        self.size = size

class PaginatedResponse(BaseModel):
    """Standard paginated response format."""
    items: List[Any]
    total: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_previous: bool

def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    size: int
) -> Dict[str, Any]:
    """Create standardized pagination response."""
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size,
        "has_next": page * size < total,
        "has_previous": page > 1,
    }