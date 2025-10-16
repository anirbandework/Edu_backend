from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.notification_service import NotificationService
from ...models.tenant_specific.notification_service import SenderType

router = APIRouter(prefix="/api/v1/teachers/notifications", tags=["Teachers - Notifications"])

@router.post("/send", response_model=dict)
async async def send_teacher_notification(
    notification_data: dict,
    teacher_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Send notification to students (teachers can only send to students)"""
    service = NotificationService(db)
    
    try:
        notification = service.create_notification(
            sender_id=teacher_id,
            sender_type=SenderType.TEACHER,
            notification_data=notification_data
        )
        
        return {
            "id": str(notification.id),
            "message": "Notification sent successfully",
            "title": notification.title,
            "total_recipients": notification.total_recipients,
            "sent_at": notification.sent_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sent", response_model=List[dict])
async async def get_teacher_sent_notifications(
    teacher_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get notifications sent by teacher"""
    service = NotificationService(db)
    
    try:
        notifications = service.get_multi(
            sender_id=teacher_id,
            is_deleted=False,
            limit=limit
        )
        
        return [
            {
                "id": str(notification.id),
                "title": notification.title,
                "message": notification.message[:100] + "..." if len(notification.message) > 100 else notification.message,
                "notification_type": notification.notification_type.value,
                "priority": notification.priority.value,
                "recipient_type": notification.recipient_type.value,
                "total_recipients": notification.total_recipients,
                "delivered_count": notification.delivered_count,
                "read_count": notification.read_count,
                "status": notification.status.value,
                "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                "created_at": notification.created_at.isoformat()
            }
            for notification in notifications
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats", response_model=dict)
async async def get_teacher_notification_stats(
    teacher_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get notification statistics for teacher"""
    service = NotificationService(db)
    
    try:
        stats = service.get_notification_stats(sender_id=teacher_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
