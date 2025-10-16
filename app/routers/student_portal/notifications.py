from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.notification_service import NotificationService
from ...models.tenant_specific.notification_service import NotificationType, NotificationStatus

router = APIRouter(prefix="/api/v1/student/notifications", tags=["Student Portal - Notifications"])

@router.get("/", response_model=List[dict])
async async def get_student_notifications(
    student_id: UUID,  # In real app, get from authenticated session
    tenant_id: UUID,
    notification_type: Optional[NotificationType] = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for student"""
    service = NotificationService(db)
    
    try:
        notifications = service.get_notifications_for_user(
            user_id=student_id,
            user_type="student",
            tenant_id=tenant_id,
            notification_type=notification_type,
            unread_only=unread_only,
            limit=limit
        )
        return notifications
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{notification_id}/read", response_model=dict)
async async def mark_notification_read(
    notification_id: UUID,
    student_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Mark notification as read"""
    service = NotificationService(db)
    
    try:
        success = service.mark_as_read(notification_id, student_id)
        if success:
            return {"message": "Notification marked as read"}
        else:
            return {"message": "Notification already read or not found"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/unread-count", response_model=dict)
async async def get_unread_count(
    student_id: UUID,  # In real app, get from authenticated session
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread notifications"""
    service = NotificationService(db)
    
    try:
        notifications = service.get_notifications_for_user(
            user_id=student_id,
            user_type="student",
            tenant_id=tenant_id,
            unread_only=True,
            limit=1000  # High limit to get accurate count
        )
        
        return {
            "unread_count": len(notifications),
            "total_notifications": len(service.get_notifications_for_user(
                user_id=student_id,
                user_type="student", 
                tenant_id=tenant_id,
                limit=1000
            ))
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
