from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession  # Changed from Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
from ..core.database import get_db
from ..models.tenant_specific.school_authority import SchoolAuthority
from ..services.school_authority_service import SchoolAuthorityService

# Pydantic Models
class AuthorityCreate(BaseModel):
    tenant_id: UUID
    authority_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    date_of_birth: datetime
    address: str
    position: str
    qualification: Optional[str] = None
    experience_years: Optional[int] = 0
    joining_date: datetime
    authority_details: Optional[dict] = None
    permissions: Optional[dict] = None
    school_overview: Optional[dict] = None
    contact_info: Optional[dict] = None

class AuthorityUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    position: Optional[str] = None
    qualification: Optional[str] = None
    experience_years: Optional[int] = None
    status: Optional[str] = None
    authority_details: Optional[dict] = None
    permissions: Optional[dict] = None
    school_overview: Optional[dict] = None
    contact_info: Optional[dict] = None

class AuthorityResponse(BaseModel):
    id: str
    tenant_id: str
    authority_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    position: str
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

router = APIRouter(prefix="/api/v1/authorities", tags=["School Authority"])

@router.get("/", response_model=dict)
async def get_authorities(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)  # Changed to AsyncSession
):
    """Get paginated school authorities"""
    service = SchoolAuthorityService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    
    try:
        result = await service.get_paginated(page=page, size=size, **filters)  # Added await
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=dict)
async def create_authority(
    authority_data: AuthorityCreate,
    db: AsyncSession = Depends(get_db)  # Changed to AsyncSession
):
    """Create new school authority"""
    service = SchoolAuthorityService(db)
    
    authority_dict = authority_data.model_dump()
    authority = await service.create(authority_dict)  # Added await
    
    return {
        "id": str(authority.id),
        "message": "School authority created successfully",
        "authority_id": authority.authority_id
    }

@router.get("/{authority_id}", response_model=dict)
async def get_authority(
    authority_id: UUID,
    db: AsyncSession = Depends(get_db)  # Changed to AsyncSession
):
    """Get specific authority details"""
    service = SchoolAuthorityService(db)
    authority = await service.get(authority_id)  # Added await
    
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
async def update_authority(
    authority_id: UUID,
    authority_data: AuthorityUpdate,
    db: AsyncSession = Depends(get_db)  # Changed to AsyncSession
):
    """Update authority information"""
    service = SchoolAuthorityService(db)
    
    update_dict = authority_data.model_dump(exclude_unset=True)
    authority = await service.update(authority_id, update_dict)  # Added await
    
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")
    
    return {
        "id": str(authority.id),
        "message": "Authority updated successfully"
    }

@router.delete("/{authority_id}")
async def delete_authority(
    authority_id: UUID,
    db: AsyncSession = Depends(get_db)  # Changed to AsyncSession
):
    """Soft delete authority"""
    service = SchoolAuthorityService(db)
    success = await service.soft_delete(authority_id)  # Added await
    
    if not success:
        raise HTTPException(status_code=404, detail="Authority not found")
    
    return {"message": "Authority deactivated successfully"}

@router.get("/tenant/{tenant_id}")
async def get_authorities_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)  # Changed to AsyncSession
):
    """Get all authorities for a specific school/tenant"""
    service = SchoolAuthorityService(db)
    authorities = await service.get_by_tenant(tenant_id)  # Added await
    
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
