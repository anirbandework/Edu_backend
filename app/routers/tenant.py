# app/routers/tenant.py
"""Tenant (School) management endpoints."""
from datetime import datetime
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ..core.database import get_db
from ..models.shared.tenant import Tenant
from ..services.base_service import BaseService
from ..schemas.tenant_schemas import Tenant as TenantSchema, TenantCreate, TenantUpdate

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant Management"])

@router.get("/", response_model=dict)
async def get_tenants(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    include_inactive: bool = Query(False, description="Include deactivated schools"),
    db: AsyncSession = Depends(get_db)
):
    """Get all tenants with pagination - active tenants by default"""
    service = BaseService(Tenant, db)
    
    # Use the include_inactive parameter in the service call
    result = await service.get_paginated(
        page=page, 
        size=size, 
        include_inactive=include_inactive
    )
    
    formatted_tenants = [
        TenantSchema.model_validate(tenant)
        for tenant in result["items"]
    ]
    
    return {
        "items": formatted_tenants,
        "total": result["total"],
        "page": result["page"],
        "size": result["size"],
        "has_next": result["has_next"],
        "has_previous": result["has_previous"],
        "total_pages": result["total_pages"],
        "showing": "all schools" if include_inactive else "active schools only"
    }

@router.post("/", response_model=TenantSchema)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Tenant, db)
    tenant_dict = tenant_data.model_dump()
    
    # Generate school_code if not provided
    if not tenant_dict.get("school_code"):
        current_year = datetime.now().year
        from sqlalchemy import select, func
        count_stmt = select(func.count()).select_from(Tenant).where(
            Tenant.school_code.like(f"SCH{current_year}%")
        )
        count_result = await db.execute(count_stmt)
        existing_count = count_result.scalar()
        tenant_dict['school_code'] = f"SCH{current_year}{existing_count + 1:03d}"
    
    try:
        tenant = await service.create(tenant_dict)
        return tenant
    except IntegrityError as e:
        await db.rollback()
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        # Handle different types of duplicate errors
        if 'uq_tenant_email' in error_message or 'email' in error_message.lower():
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "Duplicate Email",
                    "message": "A school with this email address already exists",
                    "field": "email",
                    "value": tenant_dict.get("email")
                }
            )
        elif 'uq_tenant_phone' in error_message or 'phone' in error_message.lower():
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "Duplicate Phone",
                    "message": "A school with this phone number already exists",
                    "field": "phone",
                    "value": tenant_dict.get("phone")
                }
            )
        elif 'uq_tenant_school_name_address' in error_message:
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "Duplicate School",
                    "message": "A school with this name and address already exists",
                    "fields": ["school_name", "address"],
                    "values": {
                        "school_name": tenant_dict.get("school_name"),
                        "address": tenant_dict.get("address")
                    }
                }
            )
        elif 'school_code' in error_message.lower() or 'unique' in error_message.lower():
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "Duplicate School Code",
                    "message": "A school with this school code already exists",
                    "field": "school_code",
                    "value": tenant_dict.get("school_code")
                }
            )
        else:
            # Generic integrity error
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "Duplicate Data",
                    "message": "A school with similar information already exists",
                    "suggestion": "Please check email, phone, school name, and address for duplicates"
                }
            )

@router.get("/{tenant_id}", response_model=TenantSchema)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Tenant, db)
    tenant = await service.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="School not found")
    return tenant

@router.put("/{tenant_id}", response_model=TenantSchema)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Tenant, db)
    
    try:
        tenant = await service.update(tenant_id, tenant_data.model_dump(exclude_unset=True))
        if not tenant:
            raise HTTPException(status_code=404, detail="School not found")
        return tenant
    except IntegrityError as e:
        await db.rollback()
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        # Handle duplicate errors during update
        if 'uq_tenant_email' in error_message or 'email' in error_message.lower():
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "Duplicate Email",
                    "message": "Another school with this email address already exists",
                    "field": "email"
                }
            )
        elif 'uq_tenant_phone' in error_message or 'phone' in error_message.lower():
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "Duplicate Phone", 
                    "message": "Another school with this phone number already exists",
                    "field": "phone"
                }
            )
        else:
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "Duplicate Data",
                    "message": "Another school with similar information already exists"
                }
            )

@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID,
    hard_delete: bool = Query(False, description="Permanently delete instead of deactivating"),
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Tenant, db)
    
    if hard_delete:
        success = await service.hard_delete(tenant_id)
        if not success:
            raise HTTPException(status_code=404, detail="School not found")
        return {"message": "School deleted permanently"}
    else:
        success = await service.soft_delete(tenant_id)
        if not success:
            raise HTTPException(status_code=404, detail="School not found")
        return {"message": "School deactivated successfully"}

@router.patch("/{tenant_id}/reactivate")
async def reactivate_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a deactivated school"""
    service = BaseService(Tenant, db)
    tenant = await service.update(tenant_id, {"is_active": True})
    if not tenant:
        raise HTTPException(status_code=404, detail="School not found")
    return {"message": "School reactivated successfully"}

@router.get("/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Tenant, db)
    tenant = await service.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="School not found")
    return {
        "school_name": tenant.school_name,
        "is_active": tenant.is_active,
        "total_students": tenant.total_students,
        "total_teachers": tenant.total_teachers,
        "total_staff": tenant.total_staff,
        "current_enrollment": tenant.current_enrollment,
        "maximum_capacity": tenant.maximum_capacity,
        "capacity_utilization": round((tenant.current_enrollment / tenant.maximum_capacity * 100), 2) if tenant.maximum_capacity > 0 else 0,
        "student_teacher_ratio": round(tenant.total_students / tenant.total_teachers, 2) if tenant.total_teachers > 0 else 0
    }

@router.get("/summary/all")
async def get_tenants_summary(
    include_inactive: bool = Query(False, description="Include deactivated schools"),
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Tenant, db)
    tenants = await service.get_multi(skip=0, limit=1000, include_inactive=include_inactive)
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

@router.get("/stats/overview")
async def get_tenants_overview(db: AsyncSession = Depends(get_db)):
    """Get overview statistics of all tenants"""
    service = BaseService(Tenant, db)
    
    active_count = await service.get_active_count()
    total_count = await service.get_total_count()
    inactive_count = total_count - active_count
    
    return {
        "total_schools": total_count,
        "active_schools": active_count,
        "inactive_schools": inactive_count,
        "activation_rate": round((active_count / total_count * 100), 2) if total_count > 0 else 0
    }

# Additional endpoint to check for duplicates before creating
@router.post("/check-duplicate", response_model=dict)
async def check_duplicate_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db)
):
    """Check if a tenant with similar data already exists"""
    from sqlalchemy import select, or_
    
    tenant_dict = tenant_data.model_dump()
    
    # Check for existing records with same email, phone, or name+address
    stmt = select(Tenant).where(
        or_(
            Tenant.email == tenant_dict.get('email'),
            Tenant.phone == tenant_dict.get('phone'),
            (Tenant.school_name == tenant_dict.get('school_name')) & 
            (Tenant.address == tenant_dict.get('address'))
        )
    )
    
    result = await db.execute(stmt)
    existing_tenant = result.scalar_one_or_none()
    
    if existing_tenant:
        return {
            "is_duplicate": True,
            "message": "Similar school already exists",
            "existing_school": {
                "id": str(existing_tenant.id),
                "school_name": existing_tenant.school_name,
                "email": existing_tenant.email,
                "phone": existing_tenant.phone,
                "address": existing_tenant.address,
                "is_active": existing_tenant.is_active
            }
        }
    else:
        return {
            "is_duplicate": False,
            "message": "No duplicate found, safe to create"
        }
