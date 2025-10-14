# app/services/school_authority_service.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .base_service import BaseService
from ..models.tenant_specific.school_authority import SchoolAuthority

class SchoolAuthorityService(BaseService[SchoolAuthority]):
    def __init__(self, db: AsyncSession):
        super().__init__(SchoolAuthority, db)
    
    async def get_by_tenant(self, tenant_id: UUID) -> List[SchoolAuthority]:
        """Get all authorities for a specific tenant/school"""
        stmt = select(self.model).where(
            self.model.tenant_id == tenant_id,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_email(self, email: str) -> Optional[SchoolAuthority]:
        """Get authority by email address"""
        stmt = select(self.model).where(
            self.model.email == email,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_authority_id(self, authority_id: str) -> Optional[SchoolAuthority]:
        """Get authority by their authority_id"""
        stmt = select(self.model).where(
            self.model.authority_id == authority_id,
            self.model.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_authorities(self, tenant_id: Optional[UUID] = None) -> List[SchoolAuthority]:
        """Get all active authorities, optionally filtered by tenant"""
        stmt = select(self.model).where(
            self.model.status == "active",
            self.model.is_deleted == False
        )
        
        if tenant_id:
            stmt = stmt.where(self.model.tenant_id == tenant_id)
            
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def create(self, obj_in: dict) -> SchoolAuthority:
        """Create new authority with validation"""
        try:
            # Check if email already exists
            existing = await self.get_by_email(obj_in.get("email"))
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Authority with email {obj_in.get('email')} already exists"
                )
            
            # Check if authority_id already exists
            if obj_in.get("authority_id"):
                existing_auth_id = await self.get_by_authority_id(obj_in.get("authority_id"))
                if existing_auth_id:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Authority with ID {obj_in.get('authority_id')} already exists"
                    )
            
            return await super().create(obj_in)
            
        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(status_code=409, detail="Authority already exists")
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
    
    async def update_login_time(self, authority_id: UUID) -> Optional[SchoolAuthority]:
        """Update last login time for authority"""
        from datetime import datetime
        
        authority = await self.get(authority_id)
        if authority:
            authority.last_login = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(authority)
        return authority
