from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .base_service import BaseService
from ..models.tenant_specific.class_model import ClassModel

class ClassService(BaseService[ClassModel]):
    async def __init__(self, db: Session):
        super().__init__(ClassModel, db)
    
    async def get_by_tenant(self, tenant_id: UUID) -> List[ClassModel]:
        """Get all classes for a specific tenant/school"""
        return self.await db.execute(select(self.model).filter(
            self.model.tenant_id == tenant_id,
            self.model.is_deleted == False
        ).all()
    
    async def get_by_grade_level(self, grade_level: int, tenant_id: Optional[UUID] = None) -> List[ClassModel]:
        """Get classes by grade level"""
        query = self.await db.execute(select(self.model).filter(
            self.model.grade_level == grade_level,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def get_by_section(self, section: str, tenant_id: Optional[UUID] = None) -> List[ClassModel]:
        """Get classes by section"""
        query = self.await db.execute(select(self.model).filter(
            self.model.section == section,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def get_by_academic_year(self, academic_year: str, tenant_id: Optional[UUID] = None) -> List[ClassModel]:
        """Get classes by academic year"""
        query = self.await db.execute(select(self.model).filter(
            self.model.academic_year == academic_year,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def get_active_classes(self, tenant_id: Optional[UUID] = None) -> List[ClassModel]:
        """Get all active classes"""
        query = self.await db.execute(select(self.model).filter(
            self.model.is_active == True,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def get_by_class_name(self, class_name: str, tenant_id: Optional[UUID] = None) -> Optional[ClassModel]:
        """Get class by name"""
        query = self.await db.execute(select(self.model).filter(
            self.model.class_name == class_name,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.first()
    
    async def create(self, obj_in: dict) -> ClassModel:
        """Create new class with validation"""
        # Check if class name already exists for the tenant and academic year
        if obj_in.get("class_name") and obj_in.get("tenant_id") and obj_in.get("academic_year"):
            existing = self.await db.execute(select(self.model).filter(
                self.model.class_name == obj_in.get("class_name"),
                self.model.tenant_id == obj_in.get("tenant_id"),
                self.model.academic_year == obj_in.get("academic_year"),
                self.model.is_deleted == False
            ).first()
            
            if existing:
                raise ValueError(f"Class {obj_in.get('class_name')} already exists for academic year {obj_in.get('academic_year')}")
        
        class_obj = super().create(obj_in)
        
        # Invalidate cache
        self._invalidate_class_cache(obj_in.get("tenant_id"))
        
        return class_obj
    
    async def get_class_statistics(self, class_id: UUID) -> dict:
        """Get statistics for a specific class"""
        class_obj = self.get(class_id)
        if not class_obj:
            return {}
        
        return {
            "class_name": class_obj.class_name,
            "grade_level": class_obj.grade_level,
            "section": class_obj.section,
            "maximum_students": class_obj.maximum_students,
            "current_students": class_obj.current_students,
            "available_spots": class_obj.maximum_students - class_obj.current_students,
            "occupancy_rate": round((class_obj.current_students / class_obj.maximum_students * 100), 2) if class_obj.maximum_students > 0 else 0,
            "classroom": class_obj.classroom,
            "is_active": class_obj.is_active,
            "academic_year": class_obj.academic_year
        }
    
    async def update_student_count(self, class_id: UUID, new_count: int) -> Optional[ClassModel]:
        """Update the current student count for a class"""
        class_obj = self.get(class_id)
        if class_obj:
            if new_count > class_obj.maximum_students:
                raise ValueError(f"Cannot exceed maximum capacity of {class_obj.maximum_students}")
            
            class_obj.current_students = new_count
            self.db.commit()
            self.db.refresh(class_obj)
        return class_obj
    
    async def get_classes_with_availability(self, tenant_id: Optional[UUID] = None) -> List[ClassModel]:
        """Get classes that have available spots"""
        query = self.await db.execute(select(self.model).filter(
            self.model.current_students < self.model.maximum_students,
            self.model.is_active == True,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def get_classes_paginated(
        self,
        page: int = 1,
        size: int = 20,
        tenant_id: Optional[UUID] = None,
        grade_level: Optional[int] = None,
        section: Optional[str] = None,
        academic_year: Optional[str] = None,
        active_only: bool = False
    ) -> dict:
        """Get paginated classes with caching"""
        from ..core.database import cache
        from ..core.config import settings
        
        # Create cache key
        cache_key = f"classes:page:{page}:size:{size}"
        if tenant_id:
            cache_key += f":tenant:{tenant_id}"
        if grade_level:
            cache_key += f":grade:{grade_level}"
        if section:
            cache_key += f":section:{section}"
        if academic_year:
            cache_key += f":year:{academic_year}"
        if active_only:
            cache_key += ":active"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Query database
        query = self.await db.execute(select(self.model).filter(self.model.is_deleted == False)
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
        if grade_level:
            query = query.filter(self.model.grade_level == grade_level)
        if section:
            query = query.filter(self.model.section == section)
        if academic_year:
            query = query.filter(self.model.academic_year == academic_year)
        if active_only:
            query = query.filter(self.model.is_active == True)
        
        total = query.count()
        items = query.offset((page - 1) * size).limit(size).all()
        
        total_pages = (total + size - 1) // size
        
        result = {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "total_pages": total_pages
        }
        
        # Cache result
        cache.set(cache_key, result, settings.cache_ttl_classes)
        
        return result
    
    async def get_classes_by_tenant_cached(self, tenant_id: UUID) -> List[ClassModel]:
        """Get classes by tenant with caching"""
        from ..core.database import cache
        from ..core.config import settings
        
        cache_key = f"classes:tenant:{tenant_id}:all"
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        classes = self.get_by_tenant(tenant_id)
        cache.set(cache_key, classes, settings.cache_ttl_classes)
        
        return classes
    
    async def get_classes_by_grade_cached(self, grade_level: int, tenant_id: Optional[UUID] = None) -> List[ClassModel]:
        """Get classes by grade with caching"""
        from ..core.database import cache
        from ..core.config import settings
        
        cache_key = f"classes:grade:{grade_level}"
        if tenant_id:
            cache_key += f":tenant:{tenant_id}"
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        classes = self.get_by_grade_level(grade_level, tenant_id)
        cache.set(cache_key, classes, settings.cache_ttl_classes)
        
        return classes
    
    async def get_classes_with_availability_cached(self, tenant_id: Optional[UUID] = None) -> List[ClassModel]:
        """Get available classes with caching"""
        from ..core.database import cache
        from ..core.config import settings
        
        cache_key = f"classes:available"
        if tenant_id:
            cache_key += f":tenant:{tenant_id}"
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        classes = self.get_classes_with_availability(tenant_id)
        cache.set(cache_key, classes, settings.cache_ttl_classes)
        
        return classes
    
    async def _invalidate_class_cache(self, tenant_id: Optional[UUID] = None):
        """Invalidate class cache"""
        from ..core.database import redis_client
        
        try:
            pattern = "classes:*"
            if tenant_id:
                pattern = f"classes:*tenant:{tenant_id}*"
            
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        except Exception:
            pass
