# app/routers/tenant.py
"""Tenant (School) management endpoints."""
from datetime import datetime
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ..core.database import get_db
from ..core.cache import cache_manager
from ..models.shared.tenant import Tenant
from ..services.base_service import BaseService
from ..schemas.tenant_schemas import Tenant as TenantSchema, TenantCreate, TenantUpdate
from ..utils.pagination import PaginationParams, create_paginated_response

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant Management"])

@router.get("/", response_model=dict)
async def get_tenants(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    # Check cache first
    cache_key = cache_manager.make_key("tenants_list", pagination.page, pagination.size)
    cached_result = await cache_manager.get(cache_key)
    if cached_result:
        return cached_result
    
    service = BaseService(Tenant, db)
    result = await service.get_paginated(page=pagination.page, size=pagination.size)
    formatted_tenants = [
        TenantSchema.model_validate(tenant).model_dump()
        for tenant in result["items"]
    ]
    
    response = create_paginated_response(
        items=formatted_tenants,
        total=result["total"],
        page=pagination.page,
        size=pagination.size
    )
    
    # Cache the result
    await cache_manager.set(cache_key, response, ttl=180)  # 3 minutes
    return response

@router.post("/", response_model=TenantSchema)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Tenant, db)
    tenant_dict = tenant_data.model_dump()  # Changed from dict() to model_dump()
    
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
        # Invalidate list cache
        await cache_manager.delete_pattern("tenants_list:*")
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
    # Check cache first
    cache_key = cache_manager.make_key("tenant", str(tenant_id))
    cached_tenant = await cache_manager.get(cache_key)
    if cached_tenant:
        return TenantSchema.model_validate(cached_tenant)
    
    service = BaseService(Tenant, db)
    tenant = await service.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Cache the tenant
    tenant_dict = TenantSchema.model_validate(tenant).model_dump()
    await cache_manager.set(cache_key, tenant_dict, ttl=600)  # 10 minutes
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
        
        # Invalidate caches
        await cache_manager.delete(cache_manager.make_key("tenant", str(tenant_id)))
        await cache_manager.delete(cache_manager.make_key("tenant_stats", str(tenant_id)))
        await cache_manager.delete_pattern("tenants_list:*")
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
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Tenant, db)
    success = await service.soft_delete(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Invalidate caches
    await cache_manager.delete(cache_manager.make_key("tenant", str(tenant_id)))
    await cache_manager.delete(cache_manager.make_key("tenant_stats", str(tenant_id)))
    await cache_manager.delete_pattern("tenants_list:*")
    return {"message": "School deactivated successfully"}

@router.get("/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    # Check cache first
    cache_key = cache_manager.make_key("tenant_stats", str(tenant_id))
    cached_stats = await cache_manager.get(cache_key)
    if cached_stats:
        return cached_stats
    
    service = BaseService(Tenant, db)
    tenant = await service.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="School not found")
    
    stats = {
        "school_name": tenant.school_name,
        "total_students": tenant.total_students,
        "total_teachers": tenant.total_teachers,
        "total_staff": tenant.total_staff,
        "current_enrollment": tenant.current_enrollment,
        "maximum_capacity": tenant.maximum_capacity,
        "capacity_utilization": round((tenant.current_enrollment / tenant.maximum_capacity * 100), 2) if tenant.maximum_capacity > 0 else 0,
        "student_teacher_ratio": round(tenant.total_students / tenant.total_teachers, 2) if tenant.total_teachers > 0 else 0
    }
    
    # Cache stats for 5 minutes
    await cache_manager.set(cache_key, stats, ttl=300)
    return stats

@router.get("/summary/all")
async def get_tenants_summary(
    db: AsyncSession = Depends(get_db)
):
    service = BaseService(Tenant, db)
    tenants = await service.get_multi(skip=0, limit=1000)
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
                "address": existing_tenant.address
            }
        }
    else:
        return {
            "is_duplicate": False,
            "message": "No duplicate found, safe to create"
        }
