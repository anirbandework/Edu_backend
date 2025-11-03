# app/services/teacher_service.py
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .base_service import BaseService
from ..models.tenant_specific.teacher import Teacher

class TeacherService(BaseService[Teacher]):
    def __init__(self, db: AsyncSession):
        super().__init__(Teacher, db)
    
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
        """Get teacher by email from individual field or personal_info JSON"""
        # First check individual email field
        stmt = select(self.model).where(
            self.model.email == email,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        teacher = result.scalar_one_or_none()
        if teacher:
            return teacher
        
        # Then check JSON field for backward compatibility
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
            
            # Check email uniqueness if provided (check both individual field and JSON)
            email = obj_in.get("email")
            if not email:
                personal_info = obj_in.get("personal_info", {})
                if personal_info and personal_info.get("contact_info", {}).get("primary_email"):
                    email = personal_info["contact_info"]["primary_email"]
            
            if email:
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
        teacher = await self.get(teacher_id)
        if teacher:
            teacher.last_login = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(teacher)
        return teacher
    
    # BULK OPERATIONS USING RAW SQL FOR HIGH PERFORMANCE
    
    async def bulk_import_teachers(self, teachers_data: List[dict], tenant_id: UUID) -> dict:
        """Bulk import teachers using raw SQL for maximum performance"""
        try:
            if not teachers_data:
                raise HTTPException(status_code=400, detail="No teacher data provided")
            
            # Validate and prepare bulk insert data
            now = datetime.utcnow()
            insert_data = []
            validation_errors = []
            
            for idx, teacher_data in enumerate(teachers_data):
                try:
                    # Validate required fields
                    required_fields = ["teacher_id"]
                    for field in required_fields:
                        if not teacher_data.get(field):
                            validation_errors.append(f"Row {idx + 1}: Missing required field '{field}'")
                            continue
                    
                    if validation_errors:
                        continue
                    
                    # Prepare teacher record
                    teacher_record = {
                        "id": str(uuid.uuid4()),
                        "tenant_id": str(tenant_id),
                        "teacher_id": teacher_data["teacher_id"],
                        "personal_info": teacher_data.get("personal_info"),
                        "contact_info": teacher_data.get("contact_info"),
                        "family_info": teacher_data.get("family_info"),
                        "qualifications": teacher_data.get("qualifications"),
                        "employment": teacher_data.get("employment"),
                        "academic_responsibilities": teacher_data.get("academic_responsibilities"),
                        "timetable": teacher_data.get("timetable"),
                        "performance_evaluation": teacher_data.get("performance_evaluation"),
                        "status": teacher_data.get("status", "active"),
                        "created_at": now,
                        "updated_at": now,
                        "is_deleted": False
                    }
                    insert_data.append(teacher_record)
                    
                except Exception as e:
                    validation_errors.append(f"Row {idx + 1}: {str(e)}")
            
            if validation_errors:
                raise HTTPException(
                    status_code=400, 
                    detail={"message": "Validation errors found", "errors": validation_errors}
                )
            
            # Bulk insert using raw SQL
            bulk_insert_sql = text("""
                INSERT INTO teachers (
                    id, tenant_id, teacher_id, personal_info, contact_info, family_info,
                    qualifications, employment, academic_responsibilities, timetable,
                    performance_evaluation, status, last_login, created_at, updated_at, is_deleted
                ) VALUES (
                    :id, :tenant_id, :teacher_id, :personal_info, :contact_info, :family_info,
                    :qualifications, :employment, :academic_responsibilities, :timetable,
                    :performance_evaluation, :status, :last_login, :created_at, :updated_at, :is_deleted
                ) ON CONFLICT (tenant_id, teacher_id) DO NOTHING
            """)
            
            result = await self.db.execute(bulk_insert_sql, insert_data)
            await self.db.commit()
            
            return {
                "total_records_processed": len(teachers_data),
                "successful_imports": len(insert_data),
                "failed_imports": len(validation_errors),
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk import failed: {str(e)}")
    
    async def bulk_update_status(self, teacher_ids: List[str], new_status: str, tenant_id: UUID) -> dict:
        """Bulk update teacher status using raw SQL"""
        try:
            if not teacher_ids:
                raise HTTPException(status_code=400, detail="No teacher IDs provided")
            
            valid_statuses = ["active", "inactive", "resigned", "terminated", "on_leave"]
            if new_status not in valid_statuses:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid status. Must be one of: {valid_statuses}"
                )
            
            update_sql = text("""
                UPDATE teachers
                SET status = :new_status,
                    updated_at = :updated_at
                WHERE tenant_id = :tenant_id
                AND teacher_id = ANY(:teacher_ids)
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                update_sql,
                {
                    "new_status": new_status,
                    "updated_at": datetime.utcnow(),
                    "tenant_id": tenant_id,
                    "teacher_ids": teacher_ids
                }
            )
            
            await self.db.commit()
            
            return {
                "updated_teachers": result.rowcount,
                "new_status": new_status,
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk status update failed: {str(e)}")
    
    async def bulk_assign_subjects(self, subject_assignments: List[dict], tenant_id: UUID) -> dict:
        """Bulk assign subjects to teachers using raw SQL"""
        try:
            if not subject_assignments:
                raise HTTPException(status_code=400, detail="No subject assignment data provided")
            
            # Get current teachers with their academic responsibilities
            teachers_sql = text("""
                SELECT id, teacher_id, academic_responsibilities
                FROM teachers
                WHERE tenant_id = :tenant_id
                AND teacher_id = ANY(:teacher_ids)
                AND is_deleted = false
            """)
            
            teacher_ids = [assignment["teacher_id"] for assignment in subject_assignments]
            result = await self.db.execute(
                teachers_sql, 
                {"tenant_id": tenant_id, "teacher_ids": teacher_ids}
            )
            
            teachers_data = {row[1]: {"id": row[0], "academic_responsibilities": row[2] or {}} 
                           for row in result.fetchall()}
            
            # Update academic responsibilities for each teacher
            updated_count = 0
            for assignment in subject_assignments:
                teacher_id = assignment["teacher_id"]
                if teacher_id not in teachers_data:
                    continue
                
                current_responsibilities = teachers_data[teacher_id]["academic_responsibilities"]
                teaching_assignments = current_responsibilities.get("teaching_assignments", [])
                
                # Add new subject assignments
                new_assignments = assignment.get("subjects", [])
                for subject_data in new_assignments:
                    # Check if subject already exists
                    existing = next((a for a in teaching_assignments 
                                   if a.get("subject") == subject_data.get("subject")), None)
                    if not existing:
                        teaching_assignments.append(subject_data)
                
                current_responsibilities["teaching_assignments"] = teaching_assignments
                
                # Update teacher record
                update_teacher_sql = text("""
                    UPDATE teachers
                    SET academic_responsibilities = :academic_responsibilities,
                        updated_at = :updated_at
                    WHERE id = :teacher_id
                """)
                
                await self.db.execute(
                    update_teacher_sql,
                    {
                        "academic_responsibilities": current_responsibilities,
                        "updated_at": datetime.utcnow(),
                        "teacher_id": teachers_data[teacher_id]["id"]
                    }
                )
                updated_count += 1
            
            await self.db.commit()
            
            return {
                "updated_teachers": updated_count,
                "total_assignments": len(subject_assignments),
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk subject assignment failed: {str(e)}")
    
    async def bulk_salary_update(self, salary_updates: List[dict], tenant_id: UUID) -> dict:
        """Bulk update teacher salaries using raw SQL"""
        try:
            if not salary_updates:
                raise HTTPException(status_code=400, detail="No salary update data provided")
            
            # Get current teachers with their employment info
            teachers_sql = text("""
                SELECT id, teacher_id, employment
                FROM teachers
                WHERE tenant_id = :tenant_id
                AND teacher_id = ANY(:teacher_ids)
                AND is_deleted = false
            """)
            
            teacher_ids = [update["teacher_id"] for update in salary_updates]
            result = await self.db.execute(
                teachers_sql, 
                {"tenant_id": tenant_id, "teacher_ids": teacher_ids}
            )
            
            teachers_data = {row[1]: {"id": row[0], "employment": row[2] or {}} 
                           for row in result.fetchall()}
            
            # Update employment info for each teacher
            updated_count = 0
            for salary_update in salary_updates:
                teacher_id = salary_update["teacher_id"]
                if teacher_id not in teachers_data:
                    continue
                
                current_employment = teachers_data[teacher_id]["employment"]
                salary_details = current_employment.get("salary_details", {})
                
                # Update salary information
                salary_details.update({
                    "annual_salary": salary_update.get("new_salary"),
                    "effective_date": salary_update.get("effective_date", datetime.utcnow().isoformat()),
                    "increment_reason": salary_update.get("reason", "Bulk salary update")
                })
                
                current_employment["salary_details"] = salary_details
                
                # Update teacher record
                update_teacher_sql = text("""
                    UPDATE teachers
                    SET employment = :employment,
                        updated_at = :updated_at
                    WHERE id = :teacher_id
                """)
                
                await self.db.execute(
                    update_teacher_sql,
                    {
                        "employment": current_employment,
                        "updated_at": datetime.utcnow(),
                        "teacher_id": teachers_data[teacher_id]["id"]
                    }
                )
                updated_count += 1
            
            await self.db.commit()
            
            return {
                "updated_teachers": updated_count,
                "total_updates": len(salary_updates),
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk salary update failed: {str(e)}")
    
    async def bulk_soft_delete(self, teacher_ids: List[str], tenant_id: UUID) -> dict:
        """Bulk soft delete teachers using raw SQL"""
        try:
            if not teacher_ids:
                raise HTTPException(status_code=400, detail="No teacher IDs provided")
            
            delete_sql = text("""
                UPDATE teachers
                SET is_deleted = true,
                    status = 'inactive',
                    updated_at = :updated_at
                WHERE tenant_id = :tenant_id
                AND teacher_id = ANY(:teacher_ids)
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                delete_sql,
                {
                    "updated_at": datetime.utcnow(),
                    "tenant_id": tenant_id,
                    "teacher_ids": teacher_ids
                }
            )
            
            await self.db.commit()
            
            return {
                "deleted_teachers": result.rowcount,
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")
    
    async def get_teacher_statistics(self, tenant_id: UUID) -> dict:
        """Get comprehensive teacher statistics using raw SQL for performance"""
        try:
            stats_sql = text("""
                SELECT 
                    COUNT(*) as total_teachers,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_teachers,
                    COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive_teachers,
                    COUNT(CASE WHEN status = 'on_leave' THEN 1 END) as on_leave_teachers,
                    COUNT(CASE WHEN status = 'resigned' THEN 1 END) as resigned_teachers
                FROM teachers
                WHERE tenant_id = :tenant_id
                AND is_deleted = false
            """)
            
            result = await self.db.execute(stats_sql, {"tenant_id": tenant_id})
            stats = result.fetchone()
            
            # Get department-wise distribution
            dept_distribution_sql = text("""
                SELECT 
                    employment->'job_information'->>'department' as department,
                    COUNT(*) as teacher_count
                FROM teachers
                WHERE tenant_id = :tenant_id
                AND is_deleted = false
                AND status = 'active'
                AND employment->'job_information'->>'department' IS NOT NULL
                GROUP BY employment->'job_information'->>'department'
                ORDER BY teacher_count DESC
            """)
            
            dept_result = await self.db.execute(dept_distribution_sql, {"tenant_id": tenant_id})
            dept_distribution = {row[0]: row[1] for row in dept_result.fetchall()}
            
            return {
                "total_teachers": stats[0] or 0,
                "active_teachers": stats[1] or 0,
                "inactive_teachers": stats[2] or 0,
                "on_leave_teachers": stats[3] or 0,
                "resigned_teachers": stats[4] or 0,
                "department_distribution": dept_distribution,
                "tenant_id": str(tenant_id)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
