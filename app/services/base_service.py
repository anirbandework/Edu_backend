# app/services/base_service.py
"""Base service with common CRUD operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Type, Any, Dict, Optional, List

class BaseService:
    def __init__(self, model: Type[Any], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: Any):
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100, include_inactive: bool = False):
        stmt = select(self.model).offset(skip).limit(limit)
        
        # Add active filter if model has is_active field and include_inactive is False
        if hasattr(self.model, 'is_active') and not include_inactive:
            stmt = stmt.where(self.model.is_active == True)
            
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_paginated(
        self, 
        page: int = 1, 
        size: int = 20, 
        include_inactive: bool = False,
        additional_filters: List = None
    ):
        """Get paginated results with optional active/inactive filtering"""
        offset = (page - 1) * size
        
        # Build base queries
        count_stmt = select(func.count()).select_from(self.model)
        data_stmt = select(self.model).offset(offset).limit(size)
        
        # Collect all filter conditions
        filter_conditions = []
        
        # Add active filter if model has is_active field and include_inactive is False
        if hasattr(self.model, 'is_active') and not include_inactive:
            filter_conditions.append(self.model.is_active == True)
        
        # Add any additional filters
        if additional_filters:
            filter_conditions.extend(additional_filters)
        
        # Apply filters to both queries
        if filter_conditions:
            if len(filter_conditions) == 1:
                filter_condition = filter_conditions[0]
            else:
                filter_condition = and_(*filter_conditions)
                
            count_stmt = count_stmt.where(filter_condition)
            data_stmt = data_stmt.where(filter_condition)
        
        # Execute queries
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()
        
        data_result = await self.db.execute(data_stmt)
        items = data_result.scalars().all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": (total + size - 1) // size,
            "has_next": page * size < total,
            "has_previous": page > 1,
        }

    async def create(self, obj_in: Dict):
        obj = self.model(**obj_in)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, id: Any, obj_in: Dict):
        obj = await self.get(id)
        if not obj:
            return None
        for key, value in obj_in.items():
            setattr(obj, key, value)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def soft_delete(self, id: Any):
        obj = await self.get(id)
        if not obj:
            return None
        if hasattr(obj, "is_active"):
            obj.is_active = False
            await self.db.commit()
            return True
        return False

    async def hard_delete(self, id: Any):
        """Permanently delete record from database"""
        obj = await self.get(id)
        if not obj:
            return None
        await self.db.delete(obj)
        await self.db.commit()
        return True

    async def get_active_count(self):
        """Get count of active records only"""
        if not hasattr(self.model, 'is_active'):
            return await self.get_total_count()
        
        count_stmt = select(func.count()).select_from(self.model).where(self.model.is_active == True)
        result = await self.db.execute(count_stmt)
        return result.scalar()

    async def get_total_count(self):
        """Get total count including inactive records"""
        count_stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(count_stmt)
        return result.scalar()
