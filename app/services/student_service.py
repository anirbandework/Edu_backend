from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .base_service import BaseService
from ..models.tenant_specific.student import Student

class StudentService(BaseService[Student]):
    async def __init__(self, db: Session):
        super().__init__(Student, db)
    
    async def get_by_tenant(self, tenant_id: UUID) -> List[Student]:
        """Get all students for a specific tenant/school"""
        return self.await db.execute(select(self.model).filter(
            self.model.tenant_id == tenant_id,
            self.model.is_deleted == False
        ).all()
    
    async def get_by_student_id(self, student_id: str, tenant_id: Optional[UUID] = None) -> Optional[Student]:
        """Get student by their student_id"""
        query = self.await db.execute(select(self.model).filter(
            self.model.student_id == student_id,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.first()
    
    async def get_by_email(self, email: str) -> Optional[Student]:
        """Get student by email"""
        return self.await db.execute(select(self.model).filter(
            self.model.email == email,
            self.model.is_deleted == False
        ).first()
    
    async def get_by_admission_number(self, admission_number: str, tenant_id: Optional[UUID] = None) -> Optional[Student]:
        """Get student by admission number"""
        query = self.await db.execute(select(self.model).filter(
            self.model.admission_number == admission_number,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.first()
    
    async def get_active_students(self, tenant_id: Optional[UUID] = None) -> List[Student]:
        """Get all active students, optionally filtered by tenant"""
        query = self.await db.execute(select(self.model).filter(
            self.model.status == "active",
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def get_students_by_grade(self, grade_level: int, tenant_id: Optional[UUID] = None) -> List[Student]:
        """Get students by grade level"""
        query = self.await db.execute(select(self.model).filter(
            self.model.grade_level == grade_level,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def get_students_by_section(self, section: str, tenant_id: Optional[UUID] = None) -> List[Student]:
        """Get students by section"""
        query = self.await db.execute(select(self.model).filter(
            self.model.section == section,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def create(self, obj_in: dict) -> Student:
        """Create new student with validation"""
        # Check if student_id already exists for the tenant
        if obj_in.get("student_id") and obj_in.get("tenant_id"):
            existing = self.get_by_student_id(obj_in.get("student_id"), obj_in.get("tenant_id"))
            if existing:
                raise ValueError(f"Student with ID {obj_in.get('student_id')} already exists for this school")
        
        # Check email uniqueness if provided
        if obj_in.get("email"):
            existing_email = self.get_by_email(obj_in.get("email"))
            if existing_email:
                raise ValueError(f"Student with email {obj_in.get('email')} already exists")
        
        # Check admission number uniqueness if provided
        if obj_in.get("admission_number") and obj_in.get("tenant_id"):
            existing_admission = self.get_by_admission_number(obj_in.get("admission_number"), obj_in.get("tenant_id"))
            if existing_admission:
                raise ValueError(f"Student with admission number {obj_in.get('admission_number')} already exists for this school")
        
        student = super().create(obj_in)
        
        # Invalidate cache
        self._invalidate_student_cache(obj_in.get("tenant_id"))
        
        return student
    
    async def get_students_paginated(
        self,
        page: int = 1,
        size: int = 20,
        tenant_id: Optional[UUID] = None,
        grade_level: Optional[int] = None,
        section: Optional[str] = None
    ) -> dict:
        """Get paginated students with filters and caching"""
        from ..core.database import cache
        from ..core.config import settings
        
        # Create cache key
        cache_key = f"students:page:{page}:size:{size}"
        if tenant_id:
            cache_key += f":tenant:{tenant_id}"
        if grade_level:
            cache_key += f":grade:{grade_level}"
        if section:
            cache_key += f":section:{section}"
        
        # Try to get from cache
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
        
        # Cache the result
        cache.set(cache_key, result, settings.cache_ttl_students)
        
        return result
    
    async def _invalidate_student_cache(self, tenant_id: Optional[UUID] = None):
        """Invalidate student list cache"""
        from ..core.database import cache
        import redis
        
        try:
            # Get all keys matching student cache pattern
            pattern = "students:*"
            if tenant_id:
                pattern = f"students:*tenant:{tenant_id}*"
            
            # Delete matching cache keys
            from ..core.database import redis_client
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        except Exception:
            pass
    
    async def update_login_time(self, student_id: UUID) -> Optional[Student]:
        """Update last login time for student"""
        from datetime import datetime
        
        student = self.get(student_id)
        if student:
            student.last_login = datetime.utcnow()
            self.db.commit()
            self.db.refresh(student)
        return student
