# app/services/base_service.py
"""Base service with common CRUD operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Type, Any, Dict, Optional


class BaseService:
    def __init__(self, model: Type[Any], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: Any):
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100):
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_paginated(self, page: int = 1, size: int = 20):
        # Count query
        count_stmt = select(func.count()).select_from(self.model)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()
        
        # Data query
        stmt = select(self.model).offset((page - 1) * size).limit(size)
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
