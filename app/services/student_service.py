# app/services/student_service.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .base_service import BaseService
from ..models.tenant_specific.student import Student

class StudentService(BaseService[Student]):
    def __init__(self, db: AsyncSession):
        super().__init__(Student, db)
    
    async def get_by_tenant(self, tenant_id: UUID) -> List[Student]:
        """Get all students for a specific tenant/school"""
        stmt = select(self.model).where(
            self.model.tenant_id == tenant_id,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_student_id(self, student_id: str, tenant_id: Optional[UUID] = None) -> Optional[Student]:
        """Get student by their student_id"""
        stmt = select(self.model).where(
            self.model.student_id == student_id,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[Student]:
        """Get student by email"""
        stmt = select(self.model).where(
            self.model.email == email,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_admission_number(self, admission_number: str, tenant_id: Optional[UUID] = None) -> Optional[Student]:
        """Get student by admission number"""
        stmt = select(self.model).where(
            self.model.admission_number == admission_number,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_students(self, tenant_id: Optional[UUID] = None) -> List[Student]:
        """Get all active students, optionally filtered by tenant"""
        stmt = select(self.model).where(
            self.model.status == "active",
            self.model.is_deleted == False
        )
        
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_students_by_grade(self, grade_level: int, tenant_id: Optional[UUID] = None) -> List[Student]:
        """Get students by grade level"""
        stmt = select(self.model).where(
            self.model.grade_level == grade_level,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_students_by_section(self, section: str, tenant_id: Optional[UUID] = None) -> List[Student]:
        """Get students by section"""
        stmt = select(self.model).where(
            self.model.section == section,
            self.model.is_deleted == False
        )
        
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def create(self, obj_in: dict) -> Student:
        """Create new student with validation"""
        try:
            # Check if student_id already exists for the tenant
            if obj_in.get("student_id") and obj_in.get("tenant_id"):
                existing = await self.get_by_student_id(obj_in.get("student_id"), obj_in.get("tenant_id"))
                if existing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Student with ID {obj_in.get('student_id')} already exists for this school"
                    )
            
            # Check email uniqueness if provided
            if obj_in.get("email"):
                existing_email = await self.get_by_email(obj_in.get("email"))
                if existing_email:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Student with email {obj_in.get('email')} already exists"
                    )
            
            # Check admission number uniqueness if provided
            if obj_in.get("admission_number") and obj_in.get("tenant_id"):
                existing_admission = await self.get_by_admission_number(obj_in.get("admission_number"), obj_in.get("tenant_id"))
                if existing_admission:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Student with admission number {obj_in.get('admission_number')} already exists for this school"
                    )
            
            return await super().create(obj_in)
            
        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Student already exists")
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    
    async def get_students_paginated(
        self,
        page: int = 1,
        size: int = 20,
        tenant_id: Optional[UUID] = None,
        grade_level: Optional[int] = None,
        section: Optional[str] = None
    ) -> dict:
        """Get paginated students with filters"""
        filters = {}
        if tenant_id:
            filters["tenant_id"] = tenant_id
        if grade_level:
            filters["grade_level"] = grade_level
        if section:
            filters["section"] = section
            
        return await self.get_paginated(page=page, size=size, **filters)
    
    async def update_login_time(self, student_id: UUID) -> Optional[Student]:
        """Update last login time for student"""
        from datetime import datetime
        
        student = await self.get(student_id)
        if student:
            student.last_login = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(student)
        return student
