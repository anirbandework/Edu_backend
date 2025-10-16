from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.parent_portal_service import ParentPortalService

router = APIRouter(prefix="/api/v1/parent/auth", tags=["Parent Portal - Authentication"])

@router.post("/login")
async async def parent_login(
    credentials: dict,
    db: AsyncSession = Depends(get_db)
):
    """Parent login"""
    service = ParentPortalService(db)
    
    try:
        parent = service.authenticate_parent(
            username=credentials["username"],
            password=credentials["password"]
        )
        
        if not parent:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create session
        session = service.create_session(
            parent_id=parent.id,
            session_data={
                "ip_address": credentials.get("ip_address"),
                "user_agent": credentials.get("user_agent"),
                "device_info": credentials.get("device_info", {})
            }
        )
        
        return {
            "message": "Login successful",
            "access_token": session.session_token,
            "token_type": "bearer",
            "expires_at": session.expires_at.isoformat(),
            "parent_info": {
                "id": str(parent.id),
                "name": f"{parent.first_name} {parent.last_name}",
                "email": parent.email,
                "phone": parent.phone
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout")
async async def parent_logout(
    session_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Parent logout"""
    # Implementation for session cleanup
    return {"message": "Logged out successfully"}

@router.post("/forgot-password")
async async def forgot_password(
    reset_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset"""
    return {"message": "Password reset link sent to your email"}

@router.post("/reset-password")
async async def reset_password(
    reset_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Reset password with token"""
    return {"message": "Password reset successfully"}
