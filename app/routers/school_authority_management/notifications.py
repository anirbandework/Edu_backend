# app/routers/school_authority/notifications.py
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from ...core.database import get_db
from ...services.notification_service import NotificationService
from ...models.tenant_specific.notification import (
    NotificationType, NotificationPriority, SenderType, RecipientType,
    NotificationStatus, DeliveryChannel
)

# Pydantic Models
class NotificationCreate(BaseModel):
    tenant_id: UUID
    title: str
    message: str
    short_message: Optional[str] = None
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    recipient_type: RecipientType
    recipient_config: Optional[dict] = None
    delivery_channels: Optional[List[str]] = ["in_app"]
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    attachments: Optional[dict] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    academic_year: Optional[str] = None
    term: Optional[str] = None

class NotificationUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    short_message: Optional[str] = None
    priority: Optional[NotificationPriority] = None
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    attachments: Optional[dict] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

# BULK OPERATION MODELS
class BulkNotificationCreate(BaseModel):
    tenant_id: UUID
    notifications: List[dict]

class BulkSendToRecipients(BaseModel):
    notification_recipients: List[dict]  # [{"notification_id": UUID, "recipient_config": {...}}]

class BulkStatusUpdate(BaseModel):
    notification_ids: List[UUID]
    new_status: str
    tenant_id: UUID

class BulkScheduleUpdate(BaseModel):
    schedules: List[dict]  # [{"notification_id": UUID, "scheduled_at": datetime}]
    tenant_id: UUID

class BulkMarkAsRead(BaseModel):
    notification_ids: List[UUID]
    user_id: UUID
    user_type: str

class BulkDeleteRequest(BaseModel):
    notification_ids: List[UUID]
    tenant_id: UUID
    hard_delete: bool = False

class NotificationTemplate(BaseModel):
    tenant_id: UUID
    created_by: UUID
    template_name: str
    template_code: str
    description: Optional[str] = None
    subject_template: str
    body_template: str
    short_message_template: Optional[str] = None
    notification_type: NotificationType
    default_priority: NotificationPriority = NotificationPriority.NORMAL
    supported_channels: Optional[List[str]] = ["in_app"]
    template_variables: Optional[dict] = None
    sample_data: Optional[dict] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

router = APIRouter(prefix="/api/v1/school_authority/notifications", tags=["School Authority - Notifications"])

# EXISTING ENDPOINTS (updated for async)
@router.post("/send", response_model=dict)
async def send_notification(
    notification_data: NotificationCreate,
    sender_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Send notification to recipients"""
    service = NotificationService(db)
    
    try:
        notification = await service.create_notification(
            sender_id=sender_id,
            sender_type=SenderType.SCHOOL_AUTHORITY,
            notification_data=notification_data.model_dump()
        )
        
        return {
            "id": str(notification.id),
            "message": "Notification sent successfully",
            "title": notification.title,
            "total_recipients": notification.total_recipients,
            "sent_at": notification.sent_at.isoformat() if notification.sent_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sent", response_model=dict)
async def get_sent_notifications(
    sender_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    notification_type: Optional[NotificationType] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated notifications sent by school authority"""
    service = NotificationService(db)
    
    try:
        filters = {
            "sender_id": sender_id,
            "is_deleted": False
        }
        
        if notification_type:
            filters["notification_type"] = notification_type
        
        result = await service.get_paginated(page=page, size=size, **filters)
        
        formatted_notifications = [
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
                "failed_count": notification.failed_count,
                "status": notification.status.value,
                "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                "created_at": notification.created_at.isoformat()
            }
            for notification in result["items"]
        ]
        
        return {
            "items": formatted_notifications,
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "has_next": result["has_next"],
            "has_previous": result["has_previous"],
            "total_pages": result["total_pages"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NEW BULK OPERATION ENDPOINTS

@router.post("/bulk/create", response_model=dict)
async def bulk_create_notifications(
    import_data: BulkNotificationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk create notifications from CSV/JSON data"""
    service = NotificationService(db)
    
    result = await service.bulk_create_notifications(
        notifications_data=import_data.notifications,
        tenant_id=import_data.tenant_id
    )
    
    return {
        "message": f"Bulk creation completed. {result['successful_imports']} notifications created successfully",
        **result
    }

@router.post("/bulk/send-to-recipients", response_model=dict)
async def bulk_send_to_recipients(
    send_data: BulkSendToRecipients,
    db: AsyncSession = Depends(get_db)
):
    """Bulk send notifications to different recipient configurations"""
    service = NotificationService(db)
    
    notification_ids = [UUID(item["notification_id"]) for item in send_data.notification_recipients]
    recipient_configs = [item["recipient_config"] for item in send_data.notification_recipients]
    
    result = await service.bulk_send_to_recipients(
        notification_ids=notification_ids,
        recipient_configs=recipient_configs
    )
    
    return {
        "message": f"Bulk send completed. {result['processed_notifications']} notifications processed, {result['total_recipients_added']} recipients added",
        **result
    }

@router.post("/bulk/update-status", response_model=dict)
async def bulk_update_status(
    status_data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update notification status"""
    service = NotificationService(db)
    
    result = await service.bulk_update_notification_status(
        notification_ids=status_data.notification_ids,
        new_status=status_data.new_status,
        tenant_id=status_data.tenant_id
    )
    
    return {
        "message": f"Status update completed. {result['updated_notifications']} notifications updated to '{result['new_status']}'",
        **result
    }

@router.post("/bulk/schedule", response_model=dict)
async def bulk_schedule_notifications(
    schedule_data: BulkScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Bulk schedule notifications"""
    service = NotificationService(db)
    
    result = await service.bulk_schedule_notifications(
        schedule_data=schedule_data.schedules,
        tenant_id=schedule_data.tenant_id
    )
    
    return {
        "message": f"Bulk scheduling completed. {result['scheduled_notifications']} notifications scheduled",
        **result
    }

@router.post("/bulk/mark-as-read", response_model=dict)
async def bulk_mark_as_read(
    read_data: BulkMarkAsRead,
    db: AsyncSession = Depends(get_db)
):
    """Bulk mark notifications as read for a user"""
    service = NotificationService(db)
    
    result = await service.bulk_mark_as_read(
        notification_ids=read_data.notification_ids,
        user_id=read_data.user_id,
        user_type=read_data.user_type
    )
    
    return {
        "message": f"Mark as read completed. {result['marked_as_read']} notifications marked as read",
        **result
    }

@router.post("/bulk/delete", response_model=dict)
async def bulk_delete_notifications(
    delete_data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk delete notifications"""
    service = NotificationService(db)
    
    result = await service.bulk_delete_notifications(
        notification_ids=delete_data.notification_ids,
        tenant_id=delete_data.tenant_id,
        hard_delete=delete_data.hard_delete
    )
    
    return {
        "message": f"Bulk delete completed. {result['deleted_notifications']} notifications {result['delete_type']} deleted",
        **result
    }

@router.get("/analytics/comprehensive")
async def get_comprehensive_statistics(
    tenant_id: UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive notification statistics and analytics"""
    service = NotificationService(db)
    
    date_range = {}
    if start_date:
        date_range["start_date"] = start_date
    if end_date:
        date_range["end_date"] = end_date
    
    stats = await service.get_comprehensive_notification_statistics(
        tenant_id=tenant_id,
        date_range=date_range if date_range else None
    )
    
    return {
        "message": "Comprehensive notification statistics retrieved successfully",
        **stats
    }

# EXISTING ENDPOINTS (updated)
@router.get("/stats", response_model=dict)
async def get_notification_stats(
    sender_id: UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get notification statistics for school authority"""
    service = NotificationService(db)
    
    try:
        # Use the comprehensive statistics method
        tenant_result = await service.db.execute(
            text("SELECT tenant_id FROM notifications WHERE sender_id = :sender_id LIMIT 1"),
            {"sender_id": sender_id}
        )
        tenant_row = tenant_result.fetchone()
        
        if not tenant_row:
            return {"message": "No notifications found for this sender"}
        
        tenant_id = tenant_row[0]
        date_range = {}
        if start_date:
            date_range["start_date"] = start_date
        if end_date:
            date_range["end_date"] = end_date
            
        stats = await service.get_comprehensive_notification_statistics(
            tenant_id=tenant_id,
            date_range=date_range if date_range else None
        )
        
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{notification_id}", response_model=dict)
async def get_notification_details(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed notification information"""
    service = NotificationService(db)
    
    notification = await service.get(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Get recipient summary using raw SQL for performance
    recipient_summary_sql = text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN delivered_at IS NOT NULL THEN 1 END) as delivered,
            COUNT(CASE WHEN read_at IS NOT NULL THEN 1 END) as read,
            COUNT(CASE WHEN delivered_at IS NULL THEN 1 END) as pending
        FROM notification_recipients
        WHERE notification_id = :notification_id
        AND is_deleted = false
    """)
    
    result = await db.execute(recipient_summary_sql, {"notification_id": notification_id})
    summary = result.fetchone()
    
    return {
        "id": str(notification.id),
        "title": notification.title,
        "message": notification.message,
        "short_message": notification.short_message,
        "notification_type": notification.notification_type.value,
        "priority": notification.priority.value,
        "recipient_type": notification.recipient_type.value,
        "recipient_config": notification.recipient_config,
        "delivery_channels": notification.delivery_channels,
        "total_recipients": notification.total_recipients,
        "delivered_count": notification.delivered_count,
        "read_count": notification.read_count,
        "failed_count": notification.failed_count,
        "clicked_count": notification.clicked_count,
        "status": notification.status.value,
        "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
        "scheduled_at": notification.scheduled_at.isoformat() if notification.scheduled_at else None,
        "expires_at": notification.expires_at.isoformat() if notification.expires_at else None,
        "attachments": notification.attachments,
        "action_url": notification.action_url,
        "action_text": notification.action_text,
        "category": notification.category,
        "tags": notification.tags,
        "recipients_summary": {
            "total": summary[0] if summary else 0,
            "delivered": summary[1] if summary else 0,
            "read": summary[2] if summary else 0,
            "pending": summary[3] if summary else 0
        }
    }

@router.post("/templates", response_model=dict)
async def create_notification_template(
    template_data: NotificationTemplate,
    db: AsyncSession = Depends(get_db)
):
    """Create notification template"""
    service = NotificationService(db)
    
    try:
        template = await service.create_template(template_data.model_dump())
        return {
            "id": str(template.id),
            "message": "Template created successfully",
            "template_name": template.template_name,
            "template_code": template.template_code
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/for-user/{user_id}")
async def get_notifications_for_user(
    user_id: UUID,
    user_type: str,
    tenant_id: UUID,
    notification_type: Optional[NotificationType] = Query(None),
    status: Optional[NotificationStatus] = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for a specific user (student/teacher)"""
    service = NotificationService(db)
    
    try:
        notifications = await service.get_notifications_for_user(
            user_id=user_id,
            user_type=user_type,
            tenant_id=tenant_id,
            notification_type=notification_type,
            status=status,
            unread_only=unread_only,
            limit=limit
        )
        
        return {
            "notifications": notifications,
            "total_count": len(notifications),
            "unread_count": len([n for n in notifications if not n.get("read_at")])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{notification_id}/mark-read")
async def mark_notification_as_read(
    notification_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Mark specific notification as read for user"""
    service = NotificationService(db)
    
    try:
        success = await service.mark_as_read(notification_id, user_id)
        
        if success:
            return {"message": "Notification marked as read successfully"}
        else:
            return {"message": "Notification was already read or not found"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
