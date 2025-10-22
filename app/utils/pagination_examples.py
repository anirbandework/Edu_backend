# app/utils/pagination_examples.py
"""Examples of how to use the pagination system."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from .pagination import Paginator, PaginationParams, PaginatedResponse
from ..core.database import get_db
from ..services.base_service import BaseService

# Example router showing pagination usage
router = APIRouter(prefix="/api/v1/examples", tags=["Pagination Examples"])

# Example response model
class ExampleItem(BaseModel):
    id: str
    name: str
    description: str

# Method 1: Using PaginationParams dependency
@router.get("/method1", response_model=dict)
async def get_items_method1(
    pagination: PaginationParams = Depends(Paginator.get_pagination_params),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Example using PaginationParams dependency."""
    # service = YourService(db)
    
    # Build filters
    filters = {}
    if category:
        filters["category"] = category
    
    # Use service pagination
    # result = await service.get_paginated(
    #     page=pagination.page,
    #     size=pagination.size,
    #     **filters
    # )
    
    # Mock result for example
    result = Paginator.create_response(
        items=[{"id": "1", "name": "Item 1", "description": "Example item"}],
        page=pagination.page,
        size=pagination.size,
        total=1
    )
    
    return result

# Method 2: Using individual parameters (backward compatibility)
@router.get("/method2", response_model=dict)
async def get_items_method2(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Example using individual pagination parameters."""
    # service = YourService(db)
    
    # Build filters
    filters = {}
    if category:
        filters["category"] = category
    
    # Use service pagination
    # result = await service.get_paginated(
    #     page=page,
    #     size=size,
    #     **filters
    # )
    
    # Mock result for example
    result = Paginator.create_response(
        items=[{"id": "1", "name": "Item 1", "description": "Example item"}],
        page=page,
        size=size,
        total=1,
        additional_info={"category_filter": category}
    )
    
    return result

# Method 3: Using generic PaginatedResponse
@router.get("/method3", response_model=PaginatedResponse[ExampleItem])
async def get_items_method3(
    pagination: PaginationParams = Depends(Paginator.get_pagination_params),
    db: AsyncSession = Depends(get_db)
):
    """Example using generic PaginatedResponse."""
    # Mock items
    items = [
        ExampleItem(id="1", name="Item 1", description="Example item 1"),
        ExampleItem(id="2", name="Item 2", description="Example item 2")
    ]
    
    meta = Paginator.create_meta(pagination.page, pagination.size, len(items))
    
    return PaginatedResponse(items=items, meta=meta)

# Method 4: Custom service with pagination
class ExampleService(BaseService):
    """Example service showing pagination usage."""
    
    async def get_items_with_custom_logic(
        self, 
        page: int = 1, 
        size: int = 20,
        **filters
    ):
        """Custom method using base service pagination."""
        # Use inherited get_paginated method
        result = await self.get_paginated(page, size, **filters)
        
        # Add custom processing
        for item in result["items"]:
            # Custom logic here
            pass
        
        return result

@router.get("/method4", response_model=dict)
async def get_items_method4(
    pagination: PaginationParams = Depends(Paginator.get_pagination_params),
    db: AsyncSession = Depends(get_db)
):
    """Example using custom service with pagination."""
    # service = ExampleService(YourModel, db)
    # result = await service.get_items_with_custom_logic(
    #     page=pagination.page,
    #     size=pagination.size
    # )
    
    # Mock result
    result = Paginator.create_response(
        items=[{"id": "1", "name": "Custom Item", "description": "Custom processed"}],
        page=pagination.page,
        size=pagination.size,
        total=1
    )
    
    return result

# Usage in existing endpoints (migration example)
@router.get("/migration-example", response_model=dict)
async def migration_example(
    # Old way (still supported for backward compatibility)
    # page: int = Query(1, ge=1),
    # size: int = Query(20, ge=1, le=100),
    
    # New way (recommended)
    pagination: PaginationParams = Depends(Paginator.get_pagination_params),
    
    # Other filters remain the same
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Example showing how to migrate existing endpoints."""
    
    # Old service call:
    # result = await service.get_paginated(page=page, size=size, status=status)
    
    # New service call (same result, cleaner code):
    # result = await service.get_paginated(
    #     page=pagination.page, 
    #     size=pagination.size, 
    #     status=status
    # )
    
    # Mock result
    result = Paginator.create_response(
        items=[{"id": "1", "status": status or "active"}],
        page=pagination.page,
        size=pagination.size,
        total=1
    )
    
    return result