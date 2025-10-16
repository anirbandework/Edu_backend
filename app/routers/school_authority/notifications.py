from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.notification_service import NotificationService
from ...models.tenant_specific.notification_service import (
    NotificationType, NotificationPriority, SenderType, RecipientType
)

router = APIRouter(prefix="/api/v1/school_authority/notifications", tags=["School Authority - Notifications"])

@router.post("/send", response_model=dict)
async async def send_notification(
    notification_data: dict,
    sender_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Send notification to recipients"""
    service = NotificationService(db)
    
    try:
        notification = service.create_notification(
            sender_id=sender_id,
            sender_type=SenderType.SCHOOL_AUTHORITY,
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

@router.get("/sent", response_model=dict)
async async def get_sent_notifications(
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
        
        result = service.get_paginated(page=page, size=size, **filters)
        
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
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats", response_model=dict)
async async def get_notification_stats(
    sender_id: UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get notification statistics for school authority"""
    service = NotificationService(db)
    
    try:
        stats = service.get_notification_stats(
            sender_id=sender_id,
            start_date=start_date,
            end_date=end_date
        )
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{notification_id}", response_model=dict)
async async def get_notification_details(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed notification information"""
    service = NotificationService(db)
    
    notification = service.get(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Get recipient details
    recipients = service.db.query(service.NotificationRecipient).filter(
        service.NotificationRecipient.notification_id == notification_id
    ).all()
    
    return {
        "id": str(notification.id),
        "title": notification.title,
        "message": notification.message,
        "notification_type": notification.notification_type.value,
        "priority": notification.priority.value,
        "recipient_type": notification.recipient_type.value,
        "recipient_config": notification.recipient_config,
        "delivery_channels": notification.delivery_channels,
        "total_recipients": notification.total_recipients,
        "delivered_count": notification.delivered_count,
        "read_count": notification.read_count,
        "failed_count": notification.failed_count,
        "status": notification.status.value,
        "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
        "attachments": notification.attachments,
        "action_url": notification.action_url,
        "action_text": notification.action_text,
        "recipients_summary": {
            "total": len(recipients),
            "delivered": len([r for r in recipients if r.delivered_at]),
            "read": len([r for r in recipients if r.read_at]),
            "pending": len([r for r in recipients if not r.delivered_at])
        }
    }

@router.post("/templates", response_model=dict)
async async def create_notification_template(
    template_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create notification template"""
    service = NotificationService(db)
    
    try:
        template = service.create_template(template_data)
        return {
            "id": str(template.id),
            "message": "Template created successfully",
            "template_name": template.template_name,
            "template_code": template.template_code
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/send-from-template", response_model=dict)
async async def send_from_template(
    template_data: dict,
    sender_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Send notification using template"""
    service = NotificationService(db)
    
    try:
        notification = service.send_from_template(
            template_id=UUID(template_data["template_id"]),
            sender_id=sender_id,
            sender_type=SenderType.SCHOOL_AUTHORITY,
            variables=template_data.get("variables", {}),
            recipient_config=template_data["recipient_config"]
        )
        
        return {
            "id": str(notification.id),
            "message": "Notification sent from template successfully",
            "total_recipients": notification.total_recipients
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
