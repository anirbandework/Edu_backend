# app/services/teacher_service.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .base_service import BaseService
from ..models.tenant_specific.teacher import Teacher  # Updated import path

class TeacherService(BaseService[Teacher]):
    def __init__(self, db: AsyncSession):
        super().__init__(Teacher, db)
    
    # ... rest of the service methods remain the same as provided earlier
    async def get_by_tenant(self, tenant_id: UUID) -> List[Teacher]:
        """Get all teachers for a specific tenant/school"""
        stmt = select(self.model).where(
            self.model.tenant_id == tenant_id,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_teacher_id(self, teacher_id: str, tenant_id: Optional[UUID] = None) -> Optional[Teacher]:
        """Get teacher by their teacher_id"""
        stmt = select(self.model).where(
            self.model.teacher_id == teacher_id,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[Teacher]:
        """Get teacher by email from personal_info JSON"""
        stmt = select(self.model).where(self.model.is_deleted == False)
        result = await self.db.execute(stmt)
        teachers = result.scalars().all()
        
        for teacher in teachers:
            if (teacher.personal_info and 
                teacher.personal_info.get('contact_info', {}).get('primary_email') == email):
                return teacher
        return None
    
    async def get_active_teachers(self, tenant_id: Optional[UUID] = None) -> List[Teacher]:
        """Get all active teachers, optionally filtered by tenant"""
        stmt = select(self.model).where(
            self.model.status == "active",
            self.model.is_deleted == False
        )
        
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_teachers_by_subject(self, subject: str, tenant_id: Optional[UUID] = None) -> List[Teacher]:
        """Get teachers who teach a specific subject"""
        stmt = select(self.model).where(self.model.is_deleted == False)
        
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        
        result = await self.db.execute(stmt)
        teachers = result.scalars().all()
        subject_teachers = []
        
        for teacher in teachers:
            assignments = (teacher.academic_responsibilities.get('teaching_assignments', []) 
                         if teacher.academic_responsibilities else [])
            for assignment in assignments:
                if assignment.get('subject', '').lower() == subject.lower():
                    subject_teachers.append(teacher)
                    break
        
        return subject_teachers
    
    async def create(self, obj_in: dict) -> Teacher:
        """Create new teacher with validation"""
        try:
            # Check if teacher_id already exists for the tenant
            if obj_in.get("teacher_id") and obj_in.get("tenant_id"):
                existing = await self.get_by_teacher_id(obj_in.get("teacher_id"), obj_in.get("tenant_id"))
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Teacher with ID {obj_in.get('teacher_id')} already exists for this school"
                    )
            
            # Check email uniqueness if provided
            email = None
            personal_info = obj_in.get("personal_info", {})
            if personal_info.get("contact_info", {}).get("primary_email"):
                email = personal_info["contact_info"]["primary_email"]
                existing_email = await self.get_by_email(email)
                if existing_email:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Teacher with email {email} already exists"
                    )
            
            return await super().create(obj_in)
            
        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Teacher already exists")
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    
    async def get_teachers_paginated(
        self,
        page: int = 1,
        size: int = 20,
        tenant_id: Optional[UUID] = None
    ) -> dict:
        """Get paginated teachers"""
        filters = {}
        if tenant_id:
            filters["tenant_id"] = tenant_id
            
        return await self.get_paginated(page=page, size=size, **filters)
    
    async def update_login_time(self, teacher_id: UUID) -> Optional[Teacher]:
        """Update last login time for teacher"""
        from datetime import datetime
        
        teacher = await self.get(teacher_id)
        if teacher:
            teacher.last_login = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(teacher)
        return teacher
