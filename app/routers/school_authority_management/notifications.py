# app/routers/school_authority/notifications.py
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import timedelta
from ...utils.pagination import Paginator, PaginationParams
from ...utils.cache_decorators import cache_paginated_response
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

router = APIRouter(prefix="/api/v1/school_authority/notifications", tags=["School Authority - Notifications"])

@router.post("/send", response_model=dict)
async def send_notification(
    notification_data: NotificationCreate,
    sender_id: UUID,
    sender_type: str = "school_authority",  # Can be "teacher", "school_authority"
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """Send notification to recipients"""
    service = NotificationService(db)
    
    try:
        print(f"DEBUG: Send notification endpoint called")
        print(f"DEBUG: Sender ID: {sender_id}, Sender Type: {sender_type}")
        print(f"DEBUG: Notification data: {notification_data.model_dump()}")
        
        # Convert sender_type string to enum
        if sender_type.lower() == "teacher":
            sender_type_enum = SenderType.TEACHER
        elif sender_type.lower() == "school_authority":
            sender_type_enum = SenderType.SCHOOL_AUTHORITY
        else:
            sender_type_enum = SenderType.SCHOOL_AUTHORITY  # Default
        
        notification = await service.create_notification(
            sender_id=sender_id,
            sender_type=sender_type_enum,
            notification_data=notification_data.model_dump()
        )
        
        return {
            "id": str(notification.id),
            "message": "Notification sent successfully",
            "title": notification.title,
            "total_recipients": notification.total_recipients,
            "delivered_count": notification.delivered_count,
            "sent_at": notification.sent_at.isoformat() if notification.sent_at else None
        }
    except Exception as e:
        print(f"DEBUG: Error in send notification: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/for-user/{user_id}")
async def get_notifications_for_user(
    user_id: UUID,
    user_type: str = Query(..., description="Type of user: student, teacher"),
    tenant_id: UUID = Query(..., description="Tenant ID"),
    notification_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for a specific user (student/teacher)"""
    service = NotificationService(db)
    
    try:
        print(f"DEBUG: Getting notifications for user {user_id}, type {user_type}, tenant {tenant_id}")
        
        notifications = await service.get_notifications_for_user(
            user_id=user_id,
            user_type=user_type,
            tenant_id=tenant_id,
            notification_type=notification_type,
            status=status,
            unread_only=unread_only,
            limit=limit
        )
        
        return notifications  # Return the list directly as expected by Flutter
        
    except Exception as e:
        print(f"DEBUG: Error getting notifications: {str(e)}")
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
        result = await service.mark_notification_as_read(notification_id, user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# DEBUG ENDPOINTS
@router.get("/debug/all-notifications")
async def debug_all_notifications(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Debug: See all notifications in the database for a tenant"""
    try:
        notifications_sql = text("""
            SELECT 
                n.id,
                n.title,
                n.total_recipients,
                n.delivered_count,
                n.status,
                n.created_at,
                n.sender_id,
                n.sender_type
            FROM notifications n
            WHERE n.tenant_id = :tenant_id
            AND n.is_deleted = false
            ORDER BY n.created_at DESC
            LIMIT 20
        """)
        
        result = await db.execute(notifications_sql, {"tenant_id": tenant_id})
        notifications = result.fetchall()
        
        return {
            "tenant_id": tenant_id,
            "total_notifications": len(notifications),
            "notifications": [
                {
                    "id": str(n[0]),
                    "title": n[1],
                    "total_recipients": n[2],
                    "delivered_count": n[3],
                    "status": n[4],
                    "created_at": n[5].isoformat() if n[5] else None,
                    "sender_id": str(n[6]),
                    "sender_type": n[7]
                } for n in notifications
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

@router.get("/debug/all-recipients")
async def debug_all_recipients(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Debug: See all notification recipients for a tenant"""
    try:
        recipients_sql = text("""
            SELECT 
                nr.id,
                nr.notification_id,
                nr.recipient_id,
                nr.recipient_type,
                nr.recipient_name,
                nr.status,
                nr.created_at,
                n.title
            FROM notification_recipients nr
            JOIN notifications n ON nr.notification_id = n.id
            WHERE nr.tenant_id = :tenant_id
            AND nr.is_deleted = false
            ORDER BY nr.created_at DESC
            LIMIT 50
        """)
        
        result = await db.execute(recipients_sql, {"tenant_id": tenant_id})
        recipients = result.fetchall()
        
        return {
            "tenant_id": tenant_id,
            "total_recipients": len(recipients),
            "recipients": [
                {
                    "id": str(r[0]),
                    "notification_id": str(r[1]),
                    "recipient_id": str(r[2]),
                    "recipient_type": r[3],
                    "recipient_name": r[4],
                    "status": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                    "notification_title": r[7]
                } for r in recipients
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

@router.get("/debug/student-check/{student_id}")
async def debug_student_check(
    student_id: str,
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Debug: Check if student exists and their details"""
    try:
        student_sql = text("""
            SELECT 
                id,
                first_name,
                last_name,
                status,
                tenant_id,
                is_deleted
            FROM students
            WHERE id = :student_id
        """)
        
        result = await db.execute(student_sql, {"student_id": student_id})
        student = result.fetchone()
        
        if not student:
            return {
                "student_found": False,
                "message": "Student not found in database"
            }
        
        return {
            "student_found": True,
            "student": {
                "id": str(student[0]),
                "name": f"{student[1]} {student[2]}",
                "status": student[3],
                "tenant_id": str(student[4]),
                "is_deleted": student[5],
                "tenant_matches": str(student[4]) == tenant_id
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

@router.post("/debug/create-test-notification")
async def create_test_notification(
    student_id: str,
    tenant_id: str,
    sender_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Debug: Create a test notification directly for debugging"""
    try:
        print(f"DEBUG: Creating test notification for student {student_id}")
        
        service = NotificationService(db)
        
        # FIXED: Convert string UUIDs to UUID objects properly
        try:
            student_uuid = UUID(student_id)
            tenant_uuid = UUID(tenant_id) 
            sender_uuid = UUID(sender_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(e)}")
        
        # Create test notification data
        test_notification_data = {
            "tenant_id": tenant_uuid,  # FIXED: Use UUID object
            "title": "🧪 Test Notification - Debug",
            "message": "This is a test notification created for debugging purposes. If you can see this, the notification system is working correctly!",
            "notification_type": NotificationType.ANNOUNCEMENT,
            "priority": NotificationPriority.NORMAL, 
            "recipient_type": RecipientType.INDIVIDUAL,
            "recipient_config": {
                "student_ids": [str(student_uuid)]  # FIXED: Keep as string in config
            },
            "delivery_channels": ["in_app"],
            "category": "System Test"
        }
        
        notification = await service.create_notification(
            sender_id=sender_uuid,  # FIXED: Use UUID object
            sender_type=SenderType.TEACHER,
            notification_data=test_notification_data
        )
        
        return {
            "success": True,
            "notification_id": str(notification.id),
            "title": notification.title,
            "total_recipients": notification.total_recipients,
            "delivered_count": notification.delivered_count,
            "status": notification.status.value,
            "message": "Test notification created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Error creating test notification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create test notification: {str(e)}")

        
    