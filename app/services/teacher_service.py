from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .base_service import BaseService
from ..models.tenant_specific.teacher import Teacher

class TeacherService(BaseService[Teacher]):
    async def __init__(self, db: Session):
        super().__init__(Teacher, db)
    
    async def get_by_tenant(self, tenant_id: UUID) -> List[Teacher]:
        """Get all teachers for a specific tenant/school"""
        return self.await db.execute(select(self.model).filter(
            self.model.tenant_id == tenant_id,
            self.model.is_deleted == False
        ).all()
    
    async def get_by_teacher_id(self, teacher_id: str, tenant_id: Optional[UUID] = None) -> Optional[Teacher]:
        """Get teacher by their teacher_id"""
        query = self.await db.execute(select(self.model).filter(
            self.model.teacher_id == teacher_id,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.first()
    
    async def get_by_email(self, email: str) -> Optional[Teacher]:
        """Get teacher by email from personal_info JSON"""
        teachers = self.await db.execute(select(self.model).filter(
            self.model.is_deleted == False
        ).all()
        
        for teacher in teachers:
            if teacher.personal_info and teacher.personal_info.get('contact_info', {}).get('primary_email') == email:
                return teacher
        return None
    
    async def get_active_teachers(self, tenant_id: Optional[UUID] = None) -> List[Teacher]:
        """Get all active teachers, optionally filtered by tenant"""
        query = self.await db.execute(select(self.model).filter(
            self.model.status == "active",
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def get_teachers_by_subject(self, subject: str, tenant_id: Optional[UUID] = None) -> List[Teacher]:
        """Get teachers who teach a specific subject"""
        query = self.await db.execute(select(self.model).filter(
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
        
        teachers = query.all()
        subject_teachers = []
        
        for teacher in teachers:
            assignments = teacher.academic_responsibilities.get('teaching_assignments', []) if teacher.academic_responsibilities else []
            for assignment in assignments:
                if assignment.get('subject', '').lower() == subject.lower():
                    subject_teachers.append(teacher)
                    break
        
        return subject_teachers
    
    async def create(self, obj_in: dict) -> Teacher:
        """Create new teacher with validation"""
        # Check if teacher_id already exists for the tenant
        if obj_in.get("teacher_id") and obj_in.get("tenant_id"):
            existing = self.get_by_teacher_id(obj_in.get("teacher_id"), obj_in.get("tenant_id"))
            if existing:
                raise ValueError(f"Teacher with ID {obj_in.get('teacher_id')} already exists for this school")
        
        # Check email uniqueness if provided
        email = None
        if obj_in.get("personal_info", {}).get("contact_info", {}).get("primary_email"):
            email = obj_in["personal_info"]["contact_info"]["primary_email"]
            existing_email = self.get_by_email(email)
            if existing_email:
                raise ValueError(f"Teacher with email {email} already exists")
        
        teacher = super().create(obj_in)
        
        # Invalidate cache
        self._invalidate_teacher_cache(obj_in.get("tenant_id"))
        
        return teacher
    
    async def get_teachers_paginated(
        self,
        page: int = 1,
        size: int = 20,
        tenant_id: Optional[UUID] = None
    ) -> dict:
        """Get paginated teachers with caching"""
        from ..core.database import cache
        from ..core.config import settings
        
        # Create cache key
        cache_key = f"teachers:page:{page}:size:{size}"
        if tenant_id:
            cache_key += f":tenant:{tenant_id}"
        
        # Try to get from cache
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Query database
        query = self.await db.execute(select(self.model).filter(self.model.is_deleted == False)
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
        
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
        cache.set(cache_key, result, settings.cache_ttl_teachers)
        
        return result
    
    async def get_teachers_by_tenant_cached(self, tenant_id: UUID) -> List[Teacher]:
        """Get teachers by tenant with caching"""
        from ..core.database import cache
        from ..core.config import settings
        
        cache_key = f"teachers:tenant:{tenant_id}:all"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Query database
        teachers = self.get_by_tenant(tenant_id)
        
        # Cache result
        cache.set(cache_key, teachers, settings.cache_ttl_teachers)
        
        return teachers
    
    async def get_teachers_by_subject_cached(self, subject: str, tenant_id: Optional[UUID] = None) -> List[Teacher]:
        """Get teachers by subject with caching"""
        from ..core.database import cache
        from ..core.config import settings
        
        cache_key = f"teachers:subject:{subject}"
        if tenant_id:
            cache_key += f":tenant:{tenant_id}"
        
        # Try cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Query database
        teachers = self.get_teachers_by_subject(subject, tenant_id)
        
        # Cache result
        cache.set(cache_key, teachers, settings.cache_ttl_teachers)
        
        return teachers
    
    async def _invalidate_teacher_cache(self, tenant_id: Optional[UUID] = None):
        """Invalidate teacher cache"""
        from ..core.database import redis_client
        
        try:
            pattern = "teachers:*"
            if tenant_id:
                pattern = f"teachers:*tenant:{tenant_id}*"
            
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        except Exception:
            pass
    
    async def update_login_time(self, teacher_id: UUID) -> Optional[Teacher]:
        """Update last login time for teacher"""
        from datetime import datetime
        
        teacher = self.get(teacher_id)
        if teacher:
            teacher.last_login = datetime.utcnow()
            self.db.commit()
            self.db.refresh(teacher)
        return teacher
