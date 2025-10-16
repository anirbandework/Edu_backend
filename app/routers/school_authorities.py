# services/api-gateway/app/routers/school_authorities.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ..core.database import get_db
from ..models.tenant_specific.school_authority import SchoolAuthority
from ..services.school_authority_service import SchoolAuthorityService

router = APIRouter(prefix="/api/v1/authorities", tags=["School Authority"])

@router.get("/", response_model=dict)
async async def get_authorities(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated school authorities"""
    service = SchoolAuthorityService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    
    result = service.get_paginated(page=page, size=size, **filters)
    
    formatted_authorities = [
        {
            "id": str(auth.id),
            "tenant_id": str(auth.tenant_id), 
            "authority_id": auth.authority_id,
            "first_name": auth.first_name,
            "last_name": auth.last_name,
            "email": auth.email,
            "phone": auth.phone,
            "position": auth.position,
            "status": auth.status,
            "authority_details": auth.authority_details,
            "permissions": auth.permissions,
            "created_at": auth.created_at.isoformat(),
            "updated_at": auth.updated_at.isoformat()
        }
        for auth in result["items"]
    ]
    
    return {
        "items": formatted_authorities,
        "total": result["total"],
        "page": result["page"],
        "size": result["size"],
        "has_next": result["has_next"],
        "has_previous": result["has_previous"],
        "total_pages": result["total_pages"]
    }

@router.post("/", response_model=dict)
async async def create_authority(
    authority_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create new school authority"""
    service = SchoolAuthorityService(db)
    
    try:
        authority = service.create(authority_data)
        return {
            "id": str(authority.id),
            "message": "School authority created successfully",
            "authority_id": authority.authority_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{authority_id}", response_model=dict)
async async def get_authority(
    authority_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific authority details"""
    service = SchoolAuthorityService(db)
    authority = service.get(authority_id)
    
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")
    
    return {
        "id": str(authority.id),
        "tenant_id": str(authority.tenant_id),
        "authority_id": authority.authority_id,
        "first_name": authority.first_name,
        "last_name": authority.last_name,
        "email": authority.email,
        "phone": authority.phone,
        "date_of_birth": authority.date_of_birth.isoformat() if authority.date_of_birth else None,
        "address": authority.address,
        "role": authority.role,
        "status": authority.status,
        "position": authority.position,
        "qualification": authority.qualification,
        "experience_years": authority.experience_years,
        "joining_date": authority.joining_date.isoformat() if authority.joining_date else None,
        "authority_details": authority.authority_details,
        "permissions": authority.permissions,
        "school_overview": authority.school_overview,
        "contact_info": authority.contact_info,
        "last_login": authority.last_login.isoformat() if authority.last_login else None,
        "created_at": authority.created_at.isoformat(),
        "updated_at": authority.updated_at.isoformat()
    }

@router.put("/{authority_id}", response_model=dict)
async async def update_authority(
    authority_id: UUID,
    authority_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update authority information"""
    service = SchoolAuthorityService(db)
    authority = service.update(authority_id, authority_data)
    
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")
    
    return {
        "id": str(authority.id),
        "message": "Authority updated successfully"
    }

@router.delete("/{authority_id}")
async async def delete_authority(
    authority_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete authority"""
    service = SchoolAuthorityService(db)
    success = service.soft_delete(authority_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Authority not found")
    
    return {"message": "Authority deactivated successfully"}

@router.get("/tenant/{tenant_id}")
async async def get_authorities_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all authorities for a specific school/tenant"""
    service = SchoolAuthorityService(db)
    authorities = service.get_by_tenant(tenant_id)
    
    return [
        {
            "id": str(auth.id),
            "authority_id": auth.authority_id,
            "name": f"{auth.first_name} {auth.last_name}",
            "email": auth.email,
            "position": auth.position,
            "status": auth.status
        }
        for auth in authorities
    ]
