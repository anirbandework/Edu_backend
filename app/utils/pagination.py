# app/utils/pagination.py
"""Pagination utilities for consistent API responses."""
from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel, Field
from fastapi import Query
from math import ceil

T = TypeVar('T')

class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (starts from 1)")
    size: int = Field(20, ge=1, le=100, description="Items per page")

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int
    size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    meta: PaginationMeta

class Paginator:
    """Pagination utility class."""
    
    @staticmethod
    def get_pagination_params(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(20, ge=1, le=100, description="Items per page")
    ) -> PaginationParams:
        """FastAPI dependency for pagination parameters."""
        return PaginationParams(page=page, size=size)
    
    @staticmethod
    def calculate_offset(page: int, size: int) -> int:
        """Calculate offset for database queries."""
        return (page - 1) * size
    
    @staticmethod
    def create_meta(page: int, size: int, total: int) -> PaginationMeta:
        """Create pagination metadata."""
        total_pages = ceil(total / size) if size > 0 else 0
        return PaginationMeta(
            page=page,
            size=size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    
    @staticmethod
    def create_response(
        items: List[Any], 
        page: int, 
        size: int, 
        total: int,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create standardized paginated response."""
        meta = Paginator.create_meta(page, size, total)
        response = {
            "items": items,
            "meta": meta.model_dump()
        }
        
        # Add backward compatibility fields
        response.update({
            "total": total,
            "page": page,
            "size": size,
            "has_next": meta.has_next,
            "has_previous": meta.has_previous,
            "total_pages": meta.total_pages
        })
        
        if additional_info:
            response.update(additional_info)
            
        return response