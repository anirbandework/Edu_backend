# app/routers/tenant.py
"""Tenant (School) management endpoints with bulk operations."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from ..core.database import get_db
from ..models.shared.tenant import Tenant
from ..services.tenant_service import TenantService
from ..schemas.tenant_schemas import Tenant as TenantSchema, TenantCreate, TenantUpdate

# NEW BULK OPERATION MODELS
class BulkTenantImport(BaseModel):
    tenants: List[dict]

class BulkStatusUpdate(BaseModel):
    tenant_ids: List[UUID]
    is_active: bool

class BulkCapacityUpdate(BaseModel):
    capacity_updates: List[dict]  # [{"tenant_id": UUID, "new_capacity": int}]

class BulkFinancialUpdate(BaseModel):
    financial_updates: List[dict]  # [{"tenant_id": UUID, "annual_tuition": float, "registration_fee": float}]

class BulkStatisticsUpdate(BaseModel):
    stats_updates: List[dict]  # [{"tenant_id": UUID, "total_students": int, "total_teachers": int}]

class BulkDeleteRequest(BaseModel):
    tenant_ids: List[UUID]

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant Management"])

# EXISTING ENDPOINTS (with TenantService)
@router.get("/", response_model=dict)
async def get_tenants(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    include_inactive: bool = Query(False, description="Include deactivated schools"),
    db: AsyncSession = Depends(get_db)
):
    """Get all tenants with pagination - active tenants by default"""
    service = TenantService(db)
    
    # Build filters
    filters = {}
    if not include_inactive:
        filters["is_active"] = True
    
    result = await service.get_paginated(
        page=page, 
        size=size, 
        **filters
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
    service = TenantService(db)
    tenant_dict = tenant_data.model_dump()
    
    # Generate school_code if not provided
    if not tenant_dict.get("school_code"):
        tenant_dict['school_code'] = await service.generate_school_code(tenant_dict["school_name"])
    
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
        else:
            raise HTTPException(
                status_code=409, 
                detail={
                    "error": "Duplicate School Code",
                    "message": "A school with this school code already exists",
                    "field": "school_code",
                    "value": tenant_dict.get("school_code")
                }
            )

@router.get("/{tenant_id}", response_model=TenantSchema)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = TenantService(db)
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
    service = TenantService(db)
    
    try:
        tenant = await service.update(tenant_id, tenant_data.model_dump(exclude_unset=True))
        if not tenant:
            raise HTTPException(status_code=404, detail="School not found")
        return tenant
    except IntegrityError as e:
        await db.rollback()
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        
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
    service = TenantService(db)
    
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

# EXISTING UTILITY ENDPOINTS
@router.patch("/{tenant_id}/reactivate")
async def reactivate_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a deactivated school"""
    service = TenantService(db)
    tenant = await service.update(tenant_id, {"is_active": True})
    if not tenant:
        raise HTTPException(status_code=404, detail="School not found")
    return {"message": "School reactivated successfully"}

@router.get("/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    service = TenantService(db)
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

# NEW BULK OPERATION ENDPOINTS

@router.post("/bulk/import", response_model=dict)
async def bulk_import_tenants(
    import_data: BulkTenantImport,
    db: AsyncSession = Depends(get_db)
):
    """Bulk import tenants from CSV/JSON data"""
    service = TenantService(db)
    
    result = await service.bulk_import_tenants(
        tenants_data=import_data.tenants
    )
    
    return {
        "message": f"Bulk import completed. {result['successful_imports']} schools imported successfully",
        **result
    }

@router.post("/bulk/update-status", response_model=dict)
async def bulk_update_status(
    status_data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update tenant active status"""
    service = TenantService(db)
    
    result = await service.bulk_update_status(
        tenant_ids=status_data.tenant_ids,
        is_active=status_data.is_active
    )
    
    return {
        "message": f"Status update completed. {result['updated_tenants']} schools updated to '{result['new_status']}'",
        **result
    }

@router.post("/bulk/update-capacity", response_model=dict)
async def bulk_update_capacity(
    capacity_data: BulkCapacityUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update tenant maximum capacity"""
    service = TenantService(db)
    
    result = await service.bulk_update_capacity(
        capacity_updates=capacity_data.capacity_updates
    )
    
    return {
        "message": f"Capacity update completed. {result['updated_tenants']} schools updated",
        **result
    }

@router.post("/bulk/update-financial", response_model=dict)
async def bulk_update_financial(
    financial_data: BulkFinancialUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update tenant financial information"""
    service = TenantService(db)
    
    result = await service.bulk_update_financial_info(
        financial_updates=financial_data.financial_updates
    )
    
    return {
        "message": f"Financial update completed. {result['updated_tenants']} schools updated",
        **result
    }

@router.post("/bulk/update-statistics", response_model=dict)
async def bulk_update_statistics(
    stats_data: BulkStatisticsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update tenant statistics (student/teacher counts)"""
    service = TenantService(db)
    
    result = await service.bulk_update_statistics(
        stats_updates=stats_data.stats_updates
    )
    
    return {
        "message": f"Statistics update completed. {result['updated_tenants']} schools updated",
        **result
    }

@router.post("/bulk/delete", response_model=dict)
async def bulk_delete_tenants(
    delete_data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk soft delete tenants"""
    service = TenantService(db)
    
    result = await service.bulk_soft_delete(
        tenant_ids=delete_data.tenant_ids
    )
    
    return {
        "message": f"Bulk delete completed. {result['deleted_tenants']} schools deactivated",
        **result
    }

@router.get("/analytics/comprehensive", response_model=dict)
async def get_comprehensive_statistics(
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive tenant statistics and analytics"""
    service = TenantService(db)
    
    stats = await service.get_comprehensive_statistics()
    
    return {
        "message": "Comprehensive statistics retrieved successfully",
        **stats
    }

# EXISTING SUMMARY ENDPOINTS
@router.get("/summary/all")
async def get_tenants_summary(
    include_inactive: bool = Query(False, description="Include deactivated schools"),
    db: AsyncSession = Depends(get_db)
):
    service = TenantService(db)
    
    filters = {}
    if not include_inactive:
        filters["is_active"] = True
    
    result = await service.get_paginated(page=1, size=1000, **filters)
    
    return [
        {
            "id": str(tenant.id),
            "school_code": tenant.school_code,
            "school_name": tenant.school_name,
            "total_students": tenant.total_students,
            "total_teachers": tenant.total_teachers,
            "is_active": tenant.is_active
        }
        for tenant in result["items"]
    ]

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
