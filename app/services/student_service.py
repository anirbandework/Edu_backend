# app/services/student_service.py
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
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
        student = await self.get(student_id)
        if student:
            student.last_login = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(student)
        return student
    
    # BULK OPERATIONS USING RAW SQL FOR HIGH PERFORMANCE
    
    async def bulk_import_students(self, students_data: List[dict], tenant_id: UUID) -> dict:
        """Bulk import students using raw SQL for maximum performance"""
        try:
            if not students_data:
                raise HTTPException(status_code=400, detail="No student data provided")
            
            # Validate and prepare bulk insert data
            now = datetime.utcnow()
            insert_data = []
            validation_errors = []
            
            for idx, student_data in enumerate(students_data):
                try:
                    # Validate required fields
                    required_fields = ["student_id", "first_name", "last_name", "admission_number", "grade_level", "academic_year", "date_of_birth", "address"]
                    for field in required_fields:
                        if not student_data.get(field):
                            validation_errors.append(f"Row {idx + 1}: Missing required field '{field}'")
                            continue
                    
                    if validation_errors:
                        continue
                    
                    # Prepare student record
                    student_record = {
                        "id": str(uuid.uuid4()),
                        "tenant_id": str(tenant_id),
                        "student_id": student_data["student_id"],
                        "first_name": student_data["first_name"],
                        "last_name": student_data["last_name"],
                        "email": student_data.get("email"),
                        "phone": student_data.get("phone"),
                        "date_of_birth": student_data["date_of_birth"],
                        "address": student_data["address"],
                        "role": "student",
                        "status": student_data.get("status", "active"),
                        "admission_number": student_data["admission_number"],
                        "roll_number": student_data.get("roll_number"),
                        "grade_level": student_data["grade_level"],
                        "section": student_data.get("section"),
                        "academic_year": student_data["academic_year"],
                        "parent_info": student_data.get("parent_info"),
                        "health_medical_info": student_data.get("health_medical_info"),
                        "emergency_information": student_data.get("emergency_information"),
                        "behavioral_disciplinary": student_data.get("behavioral_disciplinary"),
                        "extended_academic_info": student_data.get("extended_academic_info"),
                        "enrollment_details": student_data.get("enrollment_details"),
                        "financial_info": student_data.get("financial_info"),
                        "extracurricular_social": student_data.get("extracurricular_social"),
                        "attendance_engagement": student_data.get("attendance_engagement"),
                        "additional_metadata": student_data.get("additional_metadata"),
                        "created_at": now,
                        "updated_at": now,
                        "is_deleted": False
                    }
                    insert_data.append(student_record)
                    
                except Exception as e:
                    validation_errors.append(f"Row {idx + 1}: {str(e)}")
            
            if validation_errors:
                raise HTTPException(
                    status_code=400, 
                    detail={"message": "Validation errors found", "errors": validation_errors}
                )
            
            # Bulk insert using raw SQL
            bulk_insert_sql = text("""
                INSERT INTO students (
                    id, tenant_id, student_id, first_name, last_name, 
                    email, phone, date_of_birth, address, role, status,
                    admission_number, roll_number, grade_level, section, academic_year,
                    parent_info, health_medical_info, emergency_information,
                    behavioral_disciplinary, extended_academic_info, enrollment_details,
                    financial_info, extracurricular_social, attendance_engagement,
                    additional_metadata, created_at, updated_at, is_deleted
                ) VALUES (
                    :id, :tenant_id, :student_id, :first_name, :last_name,
                    :email, :phone, :date_of_birth, :address, :role, :status,
                    :admission_number, :roll_number, :grade_level, :section, :academic_year,
                    :parent_info, :health_medical_info, :emergency_information,
                    :behavioral_disciplinary, :extended_academic_info, :enrollment_details,
                    :financial_info, :extracurricular_social, :attendance_engagement,
                    :additional_metadata, :created_at, :updated_at, :is_deleted
                ) ON CONFLICT (tenant_id, student_id) DO NOTHING
            """)
            
            result = await self.db.execute(bulk_insert_sql, insert_data)
            await self.db.commit()
            
            return {
                "total_records_processed": len(students_data),
                "successful_imports": len(insert_data),
                "failed_imports": len(validation_errors),
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk import failed: {str(e)}")
    
    async def bulk_update_grades(self, grade_updates: List[dict], tenant_id: UUID) -> dict:
        """Bulk update student grade levels using raw SQL"""
        try:
            if not grade_updates:
                raise HTTPException(status_code=400, detail="No grade update data provided")
            
            # Prepare update data - format: [{"student_id": "STU001", "new_grade": 11}, ...]
            update_cases = []
            student_ids = []
            
            for update in grade_updates:
                student_ids.append(update["student_id"])
                update_cases.append(f"WHEN '{update['student_id']}' THEN {update['new_grade']}")
            
            if not update_cases:
                raise HTTPException(status_code=400, detail="No valid grade updates provided")
            
            # Build and execute bulk update SQL
            cases_sql = " ".join(update_cases)
            bulk_update_sql = text(f"""
                UPDATE students 
                SET grade_level = CASE student_id {cases_sql} ELSE grade_level END,
                    updated_at = :updated_at
                WHERE tenant_id = :tenant_id
                AND student_id IN :student_ids
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                bulk_update_sql,
                {
                    "updated_at": datetime.utcnow(),
                    "tenant_id": tenant_id,
                    "student_ids": tuple(student_ids)
                }
            )
            
            await self.db.commit()
            
            return {
                "updated_students": result.rowcount,
                "total_requests": len(grade_updates),
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk grade update failed: {str(e)}")
    
    async def bulk_promote_students(self, current_grade: int, tenant_id: UUID, academic_year: str) -> dict:
        """Promote all students from current grade to next grade using raw SQL"""
        try:
            # Get count of students to be promoted
            count_sql = text("""
                SELECT COUNT(*) as student_count
                FROM students
                WHERE tenant_id = :tenant_id
                AND grade_level = :current_grade
                AND status = 'active'
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                count_sql,
                {"tenant_id": tenant_id, "current_grade": current_grade}
            )
            student_count = result.scalar()
            
            if student_count == 0:
                return {
                    "promoted_students": 0,
                    "message": f"No students found in grade {current_grade}",
                    "status": "success"
                }
            
            # Promote students
            promote_sql = text("""
                UPDATE students 
                SET grade_level = grade_level + 1,
                    academic_year = :academic_year,
                    updated_at = :updated_at
                WHERE tenant_id = :tenant_id
                AND grade_level = :current_grade
                AND status = 'active'
                AND is_deleted = false
            """)
            
            await self.db.execute(
                promote_sql,
                {
                    "academic_year": academic_year,
                    "updated_at": datetime.utcnow(),
                    "tenant_id": tenant_id,
                    "current_grade": current_grade
                }
            )
            
            await self.db.commit()
            
            return {
                "promoted_students": student_count,
                "from_grade": current_grade,
                "to_grade": current_grade + 1,
                "academic_year": academic_year,
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk promotion failed: {str(e)}")
    
    async def bulk_update_status(self, student_ids: List[str], new_status: str, tenant_id: UUID) -> dict:
        """Bulk update student status using raw SQL"""
        try:
            if not student_ids:
                raise HTTPException(status_code=400, detail="No student IDs provided")
            
            valid_statuses = ["active", "inactive", "graduated", "transferred", "suspended"]
            if new_status not in valid_statuses:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid status. Must be one of: {valid_statuses}"
                )
            
            update_sql = text("""
                UPDATE students
                SET status = :new_status,
                    updated_at = :updated_at
                WHERE tenant_id = :tenant_id
                AND student_id = ANY(:student_ids)
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                update_sql,
                {
                    "new_status": new_status,
                    "updated_at": datetime.utcnow(),
                    "tenant_id": tenant_id,
                    "student_ids": student_ids
                }
            )
            
            await self.db.commit()
            
            return {
                "updated_students": result.rowcount,
                "new_status": new_status,
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk status update failed: {str(e)}")
    
    async def bulk_update_sections(self, section_updates: List[dict], tenant_id: UUID) -> dict:
        """Bulk update student sections using raw SQL"""
        try:
            if not section_updates:
                raise HTTPException(status_code=400, detail="No section update data provided")
            
            # Prepare update data - format: [{"student_id": "STU001", "new_section": "B"}, ...]
            update_cases = []
            student_ids = []
            
            for update in section_updates:
                student_ids.append(update["student_id"])
                section = update["new_section"] or "NULL"
                if section != "NULL":
                    update_cases.append(f"WHEN '{update['student_id']}' THEN '{section}'")
                else:
                    update_cases.append(f"WHEN '{update['student_id']}' THEN NULL")
            
            if not update_cases:
                raise HTTPException(status_code=400, detail="No valid section updates provided")
            
            # Build and execute bulk update SQL
            cases_sql = " ".join(update_cases)
            bulk_update_sql = text(f"""
                UPDATE students 
                SET section = CASE student_id {cases_sql} ELSE section END,
                    updated_at = :updated_at
                WHERE tenant_id = :tenant_id
                AND student_id IN :student_ids
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                bulk_update_sql,
                {
                    "updated_at": datetime.utcnow(),
                    "tenant_id": tenant_id,
                    "student_ids": tuple(student_ids)
                }
            )
            
            await self.db.commit()
            
            return {
                "updated_students": result.rowcount,
                "total_requests": len(section_updates),
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk section update failed: {str(e)}")
    
    async def bulk_soft_delete(self, student_ids: List[str], tenant_id: UUID) -> dict:
        """Bulk soft delete students using raw SQL"""
        try:
            if not student_ids:
                raise HTTPException(status_code=400, detail="No student IDs provided")
            
            delete_sql = text("""
                UPDATE students
                SET is_deleted = true,
                    status = 'inactive',
                    updated_at = :updated_at
                WHERE tenant_id = :tenant_id
                AND student_id = ANY(:student_ids)
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                delete_sql,
                {
                    "updated_at": datetime.utcnow(),
                    "tenant_id": tenant_id,
                    "student_ids": student_ids
                }
            )
            
            await self.db.commit()
            
            return {
                "deleted_students": result.rowcount,
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")
    
    async def get_student_statistics(self, tenant_id: UUID) -> dict:
        """Get comprehensive student statistics using raw SQL for performance"""
        try:
            stats_sql = text("""
                SELECT 
                    COUNT(*) as total_students,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_students,
                    COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive_students,
                    COUNT(CASE WHEN status = 'graduated' THEN 1 END) as graduated_students,
                    COUNT(CASE WHEN status = 'transferred' THEN 1 END) as transferred_students,
                    AVG(grade_level) as average_grade,
                    MIN(grade_level) as lowest_grade,
                    MAX(grade_level) as highest_grade
                FROM students
                WHERE tenant_id = :tenant_id
                AND is_deleted = false
            """)
            
            result = await self.db.execute(stats_sql, {"tenant_id": tenant_id})
            stats = result.fetchone()
            
            # Get grade-wise distribution
            grade_distribution_sql = text("""
                SELECT grade_level, COUNT(*) as student_count
                FROM students
                WHERE tenant_id = :tenant_id
                AND is_deleted = false
                AND status = 'active'
                GROUP BY grade_level
                ORDER BY grade_level
            """)
            
            grade_result = await self.db.execute(grade_distribution_sql, {"tenant_id": tenant_id})
            grade_distribution = {row[0]: row[1] for row in grade_result.fetchall()}
            
            return {
                "total_students": stats[0] or 0,
                "active_students": stats[1] or 0,
                "inactive_students": stats[2] or 0,
                "graduated_students": stats[3] or 0,
                "transferred_students": stats[4] or 0,
                "average_grade": float(stats[5]) if stats[5] else 0.0,
                "lowest_grade": stats[6] or 0,
                "highest_grade": stats[7] or 0,
                "grade_distribution": grade_distribution,
                "tenant_id": str(tenant_id)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
