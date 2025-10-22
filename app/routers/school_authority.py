# app/routers/school_authority.py (base router, not the subdirectory)
from typing import List, Optional
from uuid import UUID
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from datetime import datetime
from ..core.database import get_db
from ..utils.pagination import Paginator, PaginationParams
from ..utils.cache_decorators import cache_paginated_response
from ..models.tenant_specific.school_authority import SchoolAuthority
from ..services.school_authority_service import SchoolAuthorityService

# Existing Pydantic Models
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

# NEW BULK OPERATION MODELS
class BulkAuthorityImport(BaseModel):
    tenant_id: UUID
    authorities: List[dict]

class BulkStatusUpdate(BaseModel):
    tenant_id: UUID
    authority_ids: List[str]
    new_status: str

class BulkPermissionUpdate(BaseModel):
    tenant_id: UUID
    permission_updates: List[dict]  # [{"authority_id": "AUTH001", "permissions": {...}}]

class BulkPositionUpdate(BaseModel):
    tenant_id: UUID
    position_updates: List[dict]  # [{"authority_id": "AUTH001", "new_position": "Vice Principal"}]

class BulkDeleteRequest(BaseModel):
    tenant_id: UUID
    authority_ids: List[str]

router = APIRouter(prefix="/api/v1/authorities", tags=["School Authority"])

# EXISTING ENDPOINTS (unchanged, but with proper async)
@router.get("/", response_model=dict)
@cache_paginated_response("authorities", expire=timedelta(minutes=10))
async def get_authorities(
    pagination: PaginationParams = Depends(Paginator.get_pagination_params),
    tenant_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated school authorities"""
    service = SchoolAuthorityService(db)
    
    filters = {}
    if tenant_id:
        filters["tenant_id"] = tenant_id
    
    try:
        result = await service.get_paginated(
            page=pagination.page, 
            size=pagination.size, 
            **filters
        )
        
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
        
        # Update response with formatted items
        result["items"] = formatted_authorities
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=dict)
async def create_authority(
    authority_data: AuthorityCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new school authority"""
    service = SchoolAuthorityService(db)
    
    authority_dict = authority_data.model_dump()
    authority = await service.create(authority_dict)
    
    return {
        "id": str(authority.id),
        "message": "School authority created successfully",
        "authority_id": authority.authority_id
    }

@router.get("/{authority_id}", response_model=dict)
async def get_authority(
    authority_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific authority details"""
    service = SchoolAuthorityService(db)
    authority = await service.get(authority_id)
    
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
    db: AsyncSession = Depends(get_db)
):
    """Update authority information"""
    service = SchoolAuthorityService(db)
    
    update_dict = authority_data.model_dump(exclude_unset=True)
    authority = await service.update(authority_id, update_dict)
    
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")
    
    return {
        "id": str(authority.id),
        "message": "Authority updated successfully"
    }

@router.delete("/{authority_id}")
async def delete_authority(
    authority_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete authority"""
    service = SchoolAuthorityService(db)
    success = await service.soft_delete(authority_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Authority not found")
    
    return {"message": "Authority deactivated successfully"}

@router.get("/tenant/{tenant_id}")
async def get_authorities_by_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get all authorities for a specific school/tenant"""
    service = SchoolAuthorityService(db)
    authorities = await service.get_by_tenant(tenant_id)
    
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

# NEW BULK OPERATION ENDPOINTS

@router.post("/bulk/import", response_model=dict)
async def bulk_import_authorities(
    import_data: BulkAuthorityImport,
    db: AsyncSession = Depends(get_db)
):
    """Bulk import school authorities from CSV/JSON data"""
    service = SchoolAuthorityService(db)
    
    result = await service.bulk_import_authorities(
        authorities_data=import_data.authorities,
        tenant_id=import_data.tenant_id
    )
    
    return {
        "message": f"Bulk import completed. {result['successful_imports']} authorities imported successfully",
        **result
    }

@router.post("/bulk/update-status", response_model=dict)
async def bulk_update_status(
    status_data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update authority status"""
    service = SchoolAuthorityService(db)
    
    result = await service.bulk_update_status(
        authority_ids=status_data.authority_ids,
        new_status=status_data.new_status,
        tenant_id=status_data.tenant_id
    )
    
    return {
        "message": f"Status update completed. {result['updated_authorities']} authorities updated to '{result['new_status']}'",
        **result
    }

@router.post("/bulk/update-permissions", response_model=dict)
async def bulk_update_permissions(
    permission_data: BulkPermissionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update authority permissions"""
    service = SchoolAuthorityService(db)
    
    result = await service.bulk_update_permissions(
        permission_updates=permission_data.permission_updates,
        tenant_id=permission_data.tenant_id
    )
    
    return {
        "message": f"Permission update completed. {result['updated_authorities']} authorities updated",
        **result
    }

@router.post("/bulk/update-positions", response_model=dict)
async def bulk_update_positions(
    position_data: BulkPositionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update authority positions"""
    service = SchoolAuthorityService(db)
    
    result = await service.bulk_update_positions(
        position_updates=position_data.position_updates,
        tenant_id=position_data.tenant_id
    )
    
    return {
        "message": f"Position update completed. {result['updated_authorities']} authorities updated",
        **result
    }

@router.post("/bulk/delete", response_model=dict)
async def bulk_delete_authorities(
    delete_data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk soft delete authorities"""
    service = SchoolAuthorityService(db)
    
    result = await service.bulk_soft_delete(
        authority_ids=delete_data.authority_ids,
        tenant_id=delete_data.tenant_id
    )
    
    return {
        "message": f"Bulk delete completed. {result['deleted_authorities']} authorities deactivated",
        **result
    }

@router.get("/statistics/{tenant_id}", response_model=dict)
async def get_authority_statistics(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive authority statistics for a school"""
    service = SchoolAuthorityService(db)
    
    stats = await service.get_authority_statistics(tenant_id)
    
    return {
        "message": "Authority statistics retrieved successfully",
        **stats
    }
