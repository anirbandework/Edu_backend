# app/services/base_service.py
"""Base service with common CRUD operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Type, Any, Dict, Optional, List, TypeVar, Generic

# Define generic type
T = TypeVar('T')

class BaseService(Generic[T]):
    def __init__(self, model: Type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: Any):
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100, include_deleted: bool = False):
        stmt = select(self.model).offset(skip).limit(limit)
        
        # Add soft delete filter if model has is_deleted field
        if hasattr(self.model, 'is_deleted') and not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_paginated(
        self, 
        page: int = 1, 
        size: int = 20, 
        include_deleted: bool = False,
        **filters
    ):
        """Get paginated results with optional soft delete filtering"""
        offset = (page - 1) * size
        
        # Build base query
        stmt = select(self.model)
        
        # Add soft delete filter if model has is_deleted field
        if hasattr(self.model, 'is_deleted') and not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)
        
        # Add additional filters
        for key, value in filters.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        
        # Get total count
        count_stmt = select(func.count()).select_from(self.model)
        if hasattr(self.model, 'is_deleted') and not include_deleted:
            count_stmt = count_stmt.where(self.model.is_deleted == False)
        
        # Add filters to count query too
        for key, value in filters.items():
            if hasattr(self.model, key):
                count_stmt = count_stmt.where(getattr(self.model, key) == value)
        
        # Execute count query
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()
        
        # Execute main query with pagination
        stmt = stmt.offset(offset).limit(size)
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": (total + size - 1) // size,
            "has_next": page * size < total,
            "has_previous": page > 1,
        }

    async def create(self, obj_in: Dict) -> T:
        obj = self.model(**obj_in)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, id: Any, obj_in: Dict) -> Optional[T]:
        obj = await self.get(id)
        if not obj:
            return None
        for key, value in obj_in.items():
            setattr(obj, key, value)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def soft_delete(self, id: Any) -> bool:
        obj = await self.get(id)
        if not obj:
            return False
        if hasattr(obj, "is_deleted"):
            obj.is_deleted = True
            await self.db.commit()
            return True
        return False

    async def hard_delete(self, id: Any) -> bool:
        """Permanently delete record from database"""
        obj = await self.get(id)
        if not obj:
            return False
        await self.db.delete(obj)
        await self.db.commit()
        return True

    async def get_active_count(self) -> int:
        """Get count of non-deleted records"""
        stmt = select(func.count()).select_from(self.model)
        if hasattr(self.model, 'is_deleted'):
            stmt = stmt.where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        return result.scalar()

    async def get_total_count(self) -> int:
        """Get total count including soft-deleted records"""
        stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(stmt)
        return result.scalar()
