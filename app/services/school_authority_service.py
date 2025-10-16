from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .base_service import BaseService
from ..models.tenant_specific.school_authority import SchoolAuthority

class SchoolAuthorityService(BaseService[SchoolAuthority]):
    async def __init__(self, db: Session):
        super().__init__(SchoolAuthority, db)
    
    async def get_by_tenant(self, tenant_id: UUID) -> List[SchoolAuthority]:
        """Get all authorities for a specific tenant/school"""
        return self.await db.execute(select(self.model).filter(
            self.model.tenant_id == tenant_id,
            self.model.is_deleted == False
        ).all()
    
    async def get_by_email(self, email: str) -> Optional[SchoolAuthority]:
        """Get authority by email address"""
        return self.await db.execute(select(self.model).filter(
            self.model.email == email,
            self.model.is_deleted == False
        ).first()
    
    async def get_by_authority_id(self, authority_id: str) -> Optional[SchoolAuthority]:
        """Get authority by their authority_id"""
        return self.await db.execute(select(self.model).filter(
            self.model.authority_id == authority_id,
            self.model.is_deleted == False
        ).first()
    
    async def get_active_authorities(self, tenant_id: Optional[UUID] = None) -> List[SchoolAuthority]:
        """Get all active authorities, optionally filtered by tenant"""
        query = self.await db.execute(select(self.model).filter(
            self.model.status == "active",
            self.model.is_deleted == False
        )
        
        if tenant_id:
            query = query.filter(self.model.tenant_id == tenant_id)
            
        return query.all()
    
    async def create(self, obj_in: dict) -> SchoolAuthority:
        """Create new authority with validation"""
        # Check if email already exists
        existing = self.get_by_email(obj_in.get("email"))
        if existing:
            raise ValueError(f"Authority with email {obj_in.get('email')} already exists")
        
        # Check if authority_id already exists
        if obj_in.get("authority_id"):
            existing_auth_id = self.get_by_authority_id(obj_in.get("authority_id"))
            if existing_auth_id:
                raise ValueError(f"Authority with ID {obj_in.get('authority_id')} already exists")
        
        return super().create(obj_in)
    
    async def update_login_time(self, authority_id: UUID) -> Optional[SchoolAuthority]:
        """Update last login time for authority"""
        from datetime import datetime
        
        authority = self.get(authority_id)
        if authority:
            authority.last_login = datetime.utcnow()
            self.db.commit()
            self.db.refresh(authority)
        return authority
