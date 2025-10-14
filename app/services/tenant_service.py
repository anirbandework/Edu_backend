# app/services/tenant_service.py
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .base_service import BaseService
from ..models.shared.tenant import Tenant

class TenantService(BaseService[Tenant]):
    def __init__(self, db: AsyncSession):
        super().__init__(Tenant, db)
    
    async def get_by_school_code(self, school_code: str) -> Optional[Tenant]:
        """Get tenant by school code"""
        stmt = select(self.model).where(
            self.model.school_code == school_code,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[Tenant]:
        """Get tenant by email"""
        stmt = select(self.model).where(
            self.model.email == email,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_tenants(self) -> List[Tenant]:
        """Get all active tenants"""
        stmt = select(self.model).where(
            self.model.is_active == True,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def generate_school_code(self, school_name: str) -> str:
        """Generate unique school code"""
        current_year = datetime.now().year
        
        # Create base code from school name (first 3 letters + year + sequence)
        name_prefix = ''.join(c.upper() for c in school_name if c.isalpha())[:3]
        if len(name_prefix) < 3:
            name_prefix = name_prefix.ljust(3, 'X')
        
        # Get count of existing schools with similar pattern
        count_stmt = select(func.count()).select_from(Tenant).where(
            Tenant.school_code.like(f"{name_prefix}{current_year}%")
        )
        count_result = await self.db.execute(count_stmt)
        existing_count = count_result.scalar()
        
        return f"{name_prefix}{current_year}{existing_count + 1:03d}"
    
    # BULK OPERATIONS USING RAW SQL FOR HIGH PERFORMANCE
    
    async def bulk_import_tenants(self, tenants_data: List[dict]) -> dict:
        """Bulk import tenants using raw SQL for maximum performance"""
        try:
            if not tenants_data:
                raise HTTPException(status_code=400, detail="No tenant data provided")
            
            # Validate and prepare bulk insert data
            now = datetime.utcnow()
            insert_data = []
            validation_errors = []
            
            for idx, tenant_data in enumerate(tenants_data):
                try:
                    # Validate required fields
                    required_fields = ["school_name", "address", "phone", "email", "principal_name", "annual_tuition", "registration_fee", "maximum_capacity", "grade_levels"]
                    for field in required_fields:
                        if not tenant_data.get(field):
                            validation_errors.append(f"Row {idx + 1}: Missing required field '{field}'")
                            continue
                    
                    if validation_errors:
                        continue
                    
                    # Generate school code if not provided
                    school_code = tenant_data.get("school_code")
                    if not school_code:
                        school_code = await self.generate_school_code(tenant_data["school_name"])
                    
                    # Prepare tenant record
                    tenant_record = {
                        "id": str(uuid.uuid4()),
                        "school_code": school_code,
                        "school_name": tenant_data["school_name"],
                        "address": tenant_data["address"],
                        "phone": tenant_data["phone"],
                        "email": tenant_data["email"],
                        "principal_name": tenant_data["principal_name"],
                        "is_active": tenant_data.get("is_active", True),
                        "annual_tuition": tenant_data["annual_tuition"],
                        "registration_fee": tenant_data["registration_fee"],
                        "total_students": tenant_data.get("total_students", 0),
                        "total_teachers": tenant_data.get("total_teachers", 0),
                        "total_staff": tenant_data.get("total_staff", 0),
                        "maximum_capacity": tenant_data["maximum_capacity"],
                        "current_enrollment": tenant_data.get("current_enrollment", 0),
                        "school_type": tenant_data.get("school_type", "K-12"),
                        "grade_levels": tenant_data["grade_levels"],
                        "academic_year_start": tenant_data.get("academic_year_start"),
                        "academic_year_end": tenant_data.get("academic_year_end"),
                        "established_year": tenant_data.get("established_year"),
                        "accreditation": tenant_data.get("accreditation"),
                        "language_of_instruction": tenant_data.get("language_of_instruction", "English"),
                        "created_at": now,
                        "updated_at": now,
                        "is_deleted": False
                    }
                    insert_data.append(tenant_record)
                    
                except Exception as e:
                    validation_errors.append(f"Row {idx + 1}: {str(e)}")
            
            if validation_errors:
                raise HTTPException(
                    status_code=400, 
                    detail={"message": "Validation errors found", "errors": validation_errors}
                )
            
            # Bulk insert using raw SQL
            bulk_insert_sql = text("""
                INSERT INTO tenants (
                    id, school_code, school_name, address, phone, email, principal_name,
                    is_active, annual_tuition, registration_fee, total_students, total_teachers,
                    total_staff, maximum_capacity, current_enrollment, school_type, grade_levels,
                    academic_year_start, academic_year_end, established_year, accreditation,
                    language_of_instruction, created_at, updated_at, is_deleted
                ) VALUES (
                    :id, :school_code, :school_name, :address, :phone, :email, :principal_name,
                    :is_active, :annual_tuition, :registration_fee, :total_students, :total_teachers,
                    :total_staff, :maximum_capacity, :current_enrollment, :school_type, :grade_levels,
                    :academic_year_start, :academic_year_end, :established_year, :accreditation,
                    :language_of_instruction, :created_at, :updated_at, :is_deleted
                ) ON CONFLICT (email) DO NOTHING
            """)
            
            result = await self.db.execute(bulk_insert_sql, insert_data)
            await self.db.commit()
            
            return {
                "total_records_processed": len(tenants_data),
                "successful_imports": len(insert_data),
                "failed_imports": len(validation_errors),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk import failed: {str(e)}")
    
    async def bulk_update_status(self, tenant_ids: List[UUID], is_active: bool) -> dict:
        """Bulk update tenant active status using raw SQL"""
        try:
            if not tenant_ids:
                raise HTTPException(status_code=400, detail="No tenant IDs provided")
            
            update_sql = text("""
                UPDATE tenants
                SET is_active = :is_active,
                    updated_at = :updated_at
                WHERE id = ANY(:tenant_ids)
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                update_sql,
                {
                    "is_active": is_active,
                    "updated_at": datetime.utcnow(),
                    "tenant_ids": [str(tid) for tid in tenant_ids]
                }
            )
            
            await self.db.commit()
            
            return {
                "updated_tenants": result.rowcount,
                "new_status": "active" if is_active else "inactive",
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk status update failed: {str(e)}")
    
    async def bulk_update_capacity(self, capacity_updates: List[dict]) -> dict:
        """Bulk update tenant maximum capacity using raw SQL"""
        try:
            if not capacity_updates:
                raise HTTPException(status_code=400, detail="No capacity update data provided")
            
            # Prepare update data
            update_cases = []
            tenant_ids = []
            
            for update in capacity_updates:
                tenant_ids.append(str(update["tenant_id"]))
                capacity = update["new_capacity"]
                update_cases.append(f"WHEN '{update['tenant_id']}' THEN {capacity}")
            
            if not update_cases:
                raise HTTPException(status_code=400, detail="No valid capacity updates provided")
            
            # Build and execute bulk update SQL
            cases_sql = " ".join(update_cases)
            bulk_update_sql = text(f"""
                UPDATE tenants 
                SET maximum_capacity = CASE id {cases_sql} ELSE maximum_capacity END,
                    updated_at = :updated_at
                WHERE id IN :tenant_ids
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                bulk_update_sql,
                {
                    "updated_at": datetime.utcnow(),
                    "tenant_ids": tuple(tenant_ids)
                }
            )
            
            await self.db.commit()
            
            return {
                "updated_tenants": result.rowcount,
                "total_requests": len(capacity_updates),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk capacity update failed: {str(e)}")
    
    async def bulk_update_financial_info(self, financial_updates: List[dict]) -> dict:
        """Bulk update tenant financial information using raw SQL"""
        try:
            if not financial_updates:
                raise HTTPException(status_code=400, detail="No financial update data provided")
            
            updated_count = 0
            for financial_update in financial_updates:
                tenant_id = financial_update["tenant_id"]
                
                # Build dynamic update fields
                update_fields = []
                params = {"tenant_id": str(tenant_id), "updated_at": datetime.utcnow()}
                
                if "annual_tuition" in financial_update:
                    update_fields.append("annual_tuition = :annual_tuition")
                    params["annual_tuition"] = financial_update["annual_tuition"]
                
                if "registration_fee" in financial_update:
                    update_fields.append("registration_fee = :registration_fee")
                    params["registration_fee"] = financial_update["registration_fee"]
                
                if not update_fields:
                    continue
                
                # Execute update
                update_sql = text(f"""
                    UPDATE tenants
                    SET {', '.join(update_fields)}, updated_at = :updated_at
                    WHERE id = :tenant_id
                    AND is_deleted = false
                """)
                
                result = await self.db.execute(update_sql, params)
                if result.rowcount > 0:
                    updated_count += 1
            
            await self.db.commit()
            
            return {
                "updated_tenants": updated_count,
                "total_requests": len(financial_updates),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk financial update failed: {str(e)}")
    
    async def bulk_update_statistics(self, stats_updates: List[dict]) -> dict:
        """Bulk update tenant statistics (student/teacher counts) using raw SQL"""
        try:
            if not stats_updates:
                raise HTTPException(status_code=400, detail="No statistics update data provided")
            
            updated_count = 0
            for stats_update in stats_updates:
                tenant_id = stats_update["tenant_id"]
                
                # Build dynamic update fields
                update_fields = []
                params = {"tenant_id": str(tenant_id), "updated_at": datetime.utcnow()}
                
                if "total_students" in stats_update:
                    update_fields.append("total_students = :total_students")
                    params["total_students"] = stats_update["total_students"]
                
                if "total_teachers" in stats_update:
                    update_fields.append("total_teachers = :total_teachers")
                    params["total_teachers"] = stats_update["total_teachers"]
                
                if "total_staff" in stats_update:
                    update_fields.append("total_staff = :total_staff")
                    params["total_staff"] = stats_update["total_staff"]
                
                if "current_enrollment" in stats_update:
                    update_fields.append("current_enrollment = :current_enrollment")
                    params["current_enrollment"] = stats_update["current_enrollment"]
                
                if not update_fields:
                    continue
                
                # Execute update
                update_sql = text(f"""
                    UPDATE tenants
                    SET {', '.join(update_fields)}, updated_at = :updated_at
                    WHERE id = :tenant_id
                    AND is_deleted = false
                """)
                
                result = await self.db.execute(update_sql, params)
                if result.rowcount > 0:
                    updated_count += 1
            
            await self.db.commit()
            
            return {
                "updated_tenants": updated_count,
                "total_requests": len(stats_updates),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk statistics update failed: {str(e)}")
    
    async def bulk_soft_delete(self, tenant_ids: List[UUID]) -> dict:
        """Bulk soft delete tenants using raw SQL"""
        try:
            if not tenant_ids:
                raise HTTPException(status_code=400, detail="No tenant IDs provided")
            
            delete_sql = text("""
                UPDATE tenants
                SET is_deleted = true,
                    is_active = false,
                    updated_at = :updated_at
                WHERE id = ANY(:tenant_ids)
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                delete_sql,
                {
                    "updated_at": datetime.utcnow(),
                    "tenant_ids": [str(tid) for tid in tenant_ids]
                }
            )
            
            await self.db.commit()
            
            return {
                "deleted_tenants": result.rowcount,
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")
    
    async def get_comprehensive_statistics(self) -> dict:
        """Get comprehensive tenant statistics using raw SQL for performance"""
        try:
            # Main statistics
            stats_sql = text("""
                SELECT 
                    COUNT(*) as total_tenants,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active_tenants,
                    COUNT(CASE WHEN is_active = false THEN 1 END) as inactive_tenants,
                    SUM(total_students) as total_students_across_all,
                    SUM(total_teachers) as total_teachers_across_all,
                    SUM(current_enrollment) as total_enrollment,
                    SUM(maximum_capacity) as total_capacity,
                    AVG(annual_tuition) as average_tuition,
                    MIN(established_year) as oldest_school_year,
                    MAX(established_year) as newest_school_year
                FROM tenants
                WHERE is_deleted = false
            """)
            
            result = await self.db.execute(stats_sql)
            stats = result.fetchone()
            
            # School type distribution
            type_distribution_sql = text("""
                SELECT school_type, COUNT(*) as school_count
                FROM tenants
                WHERE is_deleted = false
                AND is_active = true
                GROUP BY school_type
                ORDER BY school_count DESC
            """)
            
            type_result = await self.db.execute(type_distribution_sql)
            type_distribution = {row[0]: row[1] for row in type_result.fetchall()}
            
            # Capacity utilization analysis
            capacity_sql = text("""
                SELECT 
                    COUNT(CASE WHEN (current_enrollment::float / maximum_capacity) < 0.5 THEN 1 END) as under_50_percent,
                    COUNT(CASE WHEN (current_enrollment::float / maximum_capacity) BETWEEN 0.5 AND 0.8 THEN 1 END) as between_50_80_percent,
                    COUNT(CASE WHEN (current_enrollment::float / maximum_capacity) > 0.8 THEN 1 END) as over_80_percent
                FROM tenants
                WHERE is_deleted = false
                AND is_active = true
                AND maximum_capacity > 0
            """)
            
            capacity_result = await self.db.execute(capacity_sql)
            capacity_stats = capacity_result.fetchone()
            
            return {
                "total_tenants": stats[0] or 0,
                "active_tenants": stats[1] or 0,
                "inactive_tenants": stats[2] or 0,
                "activation_rate": round((stats[1] / stats[0] * 100), 2) if stats[0] > 0 else 0,
                "total_students_across_all": stats[3] or 0,
                "total_teachers_across_all": stats[4] or 0,
                "total_enrollment": stats[5] or 0,
                "total_capacity": stats[6] or 0,
                "overall_capacity_utilization": round((stats[5] / stats[6] * 100), 2) if stats[6] > 0 else 0,
                "average_tuition": float(stats[7]) if stats[7] else 0.0,
                "oldest_school_year": stats[8],
                "newest_school_year": stats[9],
                "school_type_distribution": type_distribution,
                "capacity_utilization_breakdown": {
                    "under_50_percent": capacity_stats[0] or 0,
                    "between_50_80_percent": capacity_stats[1] or 0,
                    "over_80_percent": capacity_stats[2] or 0
                }
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
