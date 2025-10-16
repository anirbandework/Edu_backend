# services/api-gateway/app/services/base_service.py
from typing import Type, TypeVar, Generic, Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.ext.declarative import DeclarativeMeta
from ..models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseService(Generic[ModelType]):
    async def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    async def get(self, id: UUID) -> Optional[ModelType]:
        return self.await db.execute(select(self.model).filter(
            self.model.id == id, 
            self.model.is_deleted == False
        ).first()
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        query = self.await db.execute(select(self.model).filter(self.model.is_deleted == False)
        
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    async def get_paginated(
        self,
        page: int = 1,
        size: int = 20,
        **filters
    ) -> dict:
        query = self.await db.execute(select(self.model).filter(self.model.is_deleted == False)
        
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        
        total = query.count()
        items = query.offset((page - 1) * size).limit(size).all()
        
        total_pages = (total + size - 1) // size
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "total_pages": total_pages
        }
    
    async def create(self, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    async def update(self, id: UUID, obj_in: dict) -> Optional[ModelType]:
        db_obj = self.get(id)
        if db_obj:
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            self.db.commit()
            self.db.refresh(db_obj)
        return db_obj
    
    async def soft_delete(self, id: UUID) -> bool:
        db_obj = self.get(id)
        if db_obj:
            db_obj.is_deleted = True
            self.db.commit()
            return True
        return False
