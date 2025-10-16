from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.parent_portal_service import ParentPortalService

router = APIRouter(prefix="/api/v1/parent", tags=["Parent Portal - Dashboard"])

@router.get("/dashboard")
async async def get_parent_dashboard(
    # Add authentication dependency here
    db: AsyncSession = Depends(get_db)
):
    """Get parent dashboard overview"""
    service = ParentPortalService(db)
    
    # For demo purposes, using a placeholder parent_id
    # In real implementation, get from authenticated session
    parent_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    
    try:
        # Get children
        children = service.get_parent_children(parent_id)
        
        # Get recent notifications
        notifications = service.get_parent_notifications(parent_id, limit=10)
        
        # Get unread messages
        messages = service.get_parent_messages(parent_id, unread_only=True)
        
        return {
            "children": children,
            "notifications_count": len(notifications),
            "unread_messages_count": len(messages),
            "recent_notifications": [
                {
                    "id": str(notif.id),
                    "title": notif.title,
                    "message": notif.message,
                    "type": notif.notification_type.value,
                    "sent_date": notif.sent_date.isoformat(),
                    "is_read": notif.is_read
                }
                for notif in notifications[:5]
            ],
            "quick_actions": [
                {"title": "View Attendance", "url": "/parent/children/attendance"},
                {"title": "Check Grades", "url": "/parent/children/grades"},
                {"title": "Pay Fees", "url": "/parent/fees"},
                {"title": "Send Message", "url": "/parent/messages/compose"}
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/profile")
async async def get_parent_profile(
    db: AsyncSession = Depends(get_db)
):
    """Get parent profile information"""
    # Implementation for authenticated parent profile
    return {
        "parent_id": "PAR001",
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1-555-0123",
        "children": [
            {
                "name": "Jane Doe",
                "grade": "10th",
                "section": "A"
            }
        ],
        "message": "Authentication integration needed"
    }

@router.put("/profile")
async async def update_parent_profile(
    profile_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update parent profile"""
    return {
        "message": "Profile updated successfully",
        "updated_fields": list(profile_data.keys())
    }
