from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ..core.database import get_db
from ..models.shared.tenant import Tenant
from ..services.base_service import BaseService

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant Management"])

@router.get("/", response_model=dict)
async async def get_tenants(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated tenants/schools with complete information"""
    service = BaseService(Tenant, db)
    result = service.get_paginated(page=page, size=size)
    
    formatted_tenants = [
        {
            "id": str(tenant.id),
            "school_code": tenant.school_code,
            "school_name": tenant.school_name,
            "address": tenant.address,
            "phone": tenant.phone,
            "email": tenant.email,
            "principal_name": tenant.principal_name,
            "is_active": tenant.is_active,
            
            # Financial Information
            "annual_tuition": float(tenant.annual_tuition) if tenant.annual_tuition else None,
            "registration_fee": float(tenant.registration_fee) if tenant.registration_fee else None,
            
            # Statistics
            "total_students": tenant.total_students,
            "total_teachers": tenant.total_teachers,
            "total_staff": tenant.total_staff,
            "maximum_capacity": tenant.maximum_capacity,
            "current_enrollment": tenant.current_enrollment,
            
            # Academic Information
            "school_type": tenant.school_type,
            "grade_levels": tenant.grade_levels,
            "academic_year_start": tenant.academic_year_start.isoformat() if tenant.academic_year_start else None,
            "academic_year_end": tenant.academic_year_end.isoformat() if tenant.academic_year_end else None,
            "established_year": tenant.established_year,
            "accreditation": tenant.accreditation,
            "language_of_instruction": tenant.language_of_instruction,
            
            # System fields
            "created_at": tenant.created_at.isoformat(),
            "updated_at": tenant.updated_at.isoformat()
        }
        for tenant in result["items"]
    ]
    
    return {
        "items": formatted_tenants,
        "total": result["total"],
        "page": result["page"],
        "size": result["size"],
        "has_next": result["has_next"],
        "has_previous": result["has_previous"],
        "total_pages": result["total_pages"]
    }

@router.post("/", response_model=dict)
async async def create_tenant(
    tenant_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create new tenant/school"""
    service = BaseService(Tenant, db)
    
    try:
        # Auto-generate school_code if not provided
        if 'school_code' not in tenant_data or not tenant_data['school_code']:
            # Generate school code like SCH2025003, SCH2025004, etc.
            current_year = datetime.now().year
            existing_count = db.query(Tenant).filter(
                Tenant.school_code.like(f"SCH{current_year}%")
            ).count()
            tenant_data['school_code'] = f"SCH{current_year}{existing_count + 1:03d}"
        
        tenant = service.create(tenant_data)
        return {
            "id": str(tenant.id),
            "message": "School created successfully",
            "school_code": tenant.school_code
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{tenant_id}", response_model=dict)
async async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific tenant details"""
    service = BaseService(Tenant, db)
    tenant = service.get(tenant_id)
    
    if not tenant:
        raise HTTPException(status_code=404, detail="School not found")
    
    return {
        "id": str(tenant.id),
        "school_code": tenant.school_code,
        "school_name": tenant.school_name,
        "address": tenant.address,
        "phone": tenant.phone,
        "email": tenant.email,
        "principal_name": tenant.principal_name,
        "is_active": tenant.is_active,
        
        # Financial Information
        "annual_tuition": float(tenant.annual_tuition) if tenant.annual_tuition else None,
        "registration_fee": float(tenant.registration_fee) if tenant.registration_fee else None,
        
        # Statistics
        "total_students": tenant.total_students,
        "total_teachers": tenant.total_teachers,
        "total_staff": tenant.total_staff,
        "maximum_capacity": tenant.maximum_capacity,
        "current_enrollment": tenant.current_enrollment,
        
        # Academic Information
        "school_type": tenant.school_type,
        "grade_levels": tenant.grade_levels,
        "academic_year_start": tenant.academic_year_start.isoformat() if tenant.academic_year_start else None,
        "academic_year_end": tenant.academic_year_end.isoformat() if tenant.academic_year_end else None,
        "established_year": tenant.established_year,
        "accreditation": tenant.accreditation,
        "language_of_instruction": tenant.language_of_instruction,
        
        # System fields
        "created_at": tenant.created_at.isoformat(),
        "updated_at": tenant.updated_at.isoformat()
    }

@router.put("/{tenant_id}", response_model=dict)
async async def update_tenant(
    tenant_id: UUID,
    tenant_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update tenant information"""
    service = BaseService(Tenant, db)
    tenant = service.update(tenant_id, tenant_data)
    
    if not tenant:
        raise HTTPException(status_code=404, detail="School not found")
    
    return {
        "id": str(tenant.id),
        "message": "School updated successfully"
    }

@router.delete("/{tenant_id}")
async async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete tenant"""
    service = BaseService(Tenant, db)
    success = service.soft_delete(tenant_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="School not found")
    
    return {"message": "School deactivated successfully"}

@router.get("/{tenant_id}/stats")
async async def get_tenant_stats(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get school statistics"""
    service = BaseService(Tenant, db)
    tenant = service.get(tenant_id)
    
    if not tenant:
        raise HTTPException(status_code=404, detail="School not found")
    
    return {
        "school_name": tenant.school_name,
        "total_students": tenant.total_students,
        "total_teachers": tenant.total_teachers,
        "total_staff": tenant.total_staff,
        "current_enrollment": tenant.current_enrollment,
        "maximum_capacity": tenant.maximum_capacity,
        "capacity_utilization": round((tenant.current_enrollment / tenant.maximum_capacity * 100), 2) if tenant.maximum_capacity > 0 else 0,
        "student_teacher_ratio": round(tenant.total_students / tenant.total_teachers, 2) if tenant.total_teachers > 0 else 0
    }

# Optional: Add a summary endpoint for quick overview
@router.get("/summary/all")
async async def get_tenants_summary(
    db: AsyncSession = Depends(get_db)
):
    """Get summary of all tenants for quick overview"""
    service = BaseService(Tenant, db)
    tenants = service.get_multi(skip=0, limit=1000)
    
    return [
        {
            "id": str(tenant.id),
            "school_code": tenant.school_code,
            "school_name": tenant.school_name,
            "total_students": tenant.total_students,
            "total_teachers": tenant.total_teachers,
            "is_active": tenant.is_active
        }
        for tenant in tenants
    ]
