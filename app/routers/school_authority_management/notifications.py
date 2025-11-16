# app/routers/school_authority/notifications.py
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
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
    recipient_config: dict  # REQUIRED: Specify who receives the notification
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
    
    class Config:
        schema_extra = {
            "example": {
                "tenant_id": "3fd85f64-5717-4562-b3fc-2c963f66afa6",
                "title": "Important Announcement",
                "message": "This is an important message for students",
                "notification_type": "announcement",
                "priority": "normal",
                "recipient_type": "individual",
                "recipient_config": {
                    "student_ids": ["student-uuid-1", "student-uuid-2"]
                },
                "delivery_channels": ["in_app"]
            }
        }

router = APIRouter(prefix="/api/v1/school_authority/notifications", tags=["School Authority - Notifications"])

async def _validate_and_get_sender_type(db: AsyncSession, sender_id: UUID) -> SenderType:
    """Validate sender exists and return their actual type from database"""
    
    print(f"DEBUG: Validating sender_id: {sender_id}")
    
    # Check if sender is a student FIRST (should not be allowed to send)
    student_sql = text("""
        SELECT id FROM students 
        WHERE id = :sender_id AND is_deleted = false
    """)
    result = await db.execute(student_sql, {"sender_id": str(sender_id)})
    student_result = result.fetchone()
    print(f"DEBUG: Student check: {student_result}")
    if student_result:
        print(f"DEBUG: Student found - raising 403 error")
        raise HTTPException(
            status_code=403, 
            detail="Students are not allowed to send notifications"
        )
    
    # Check if sender is a school authority
    school_authority_sql = text("""
        SELECT id FROM school_authorities 
        WHERE id = :sender_id AND is_deleted = false
    """)
    result = await db.execute(school_authority_sql, {"sender_id": str(sender_id)})
    sa_result = result.fetchone()
    print(f"DEBUG: School authority check: {sa_result}")
    if sa_result:
        return SenderType.SCHOOL_AUTHORITY
    
    # Check if sender is a teacher
    teacher_sql = text("""
        SELECT id FROM teachers 
        WHERE id = :sender_id AND is_deleted = false
    """)
    result = await db.execute(teacher_sql, {"sender_id": str(sender_id)})
    teacher_result = result.fetchone()
    print(f"DEBUG: Teacher check: {teacher_result}")
    if teacher_result:
        return SenderType.TEACHER
    
    # Sender not found in any valid table
    print(f"DEBUG: Sender {sender_id} not found in any table")
    raise HTTPException(
        status_code=404, 
        detail="Sender not found or invalid sender type"
    )

@router.post("/send", response_model=dict)
async def send_notification(
    notification_data: NotificationCreate,
    sender_id: UUID,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """Send notification to recipients
    
    recipient_config examples:
    - Individual students: {"student_ids": ["uuid1", "uuid2"]}
    - Individual teachers: {"teacher_ids": ["uuid1", "uuid2"]}
    - Entire class: {"class_id": "class-uuid"}
    - Entire grade: {"grade": "10"}
    - All students: {} (when recipient_type is "all_students")
    - All teachers: {} (when recipient_type is "all_teachers")
    """
    print("DEBUG: Send notification endpoint called")
    print(f"DEBUG: Sender ID: {sender_id}")
    print(f"DEBUG: Notification data: {notification_data.model_dump()}")
    
    service = NotificationService(db)
    
    try:
        # Validate sender and determine actual sender type from database
        sender_type_enum = await _validate_and_get_sender_type(db, sender_id)
        print(f"DEBUG: Validated sender type: {sender_type_enum}")
        
        # Create notification
        print(f"DEBUG: Creating notification for sender {sender_id}")
        print(f"DEBUG: Sender type: {sender_type_enum}")
        print(f"DEBUG: Notification data: {notification_data.model_dump()}")
        
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
    except HTTPException as he:
        print(f"DEBUG: HTTPException caught: status={he.status_code}, detail={he.detail}")
        raise  # Re-raise HTTPException with original status code
    except Exception as e:
        print(f"DEBUG: General exception in send notification: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get("/debug/sender-check/{sender_id}")
async def debug_sender_check(
    sender_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Debug: Check if sender exists in any table"""
    try:
        results = {}
        
        # Check students
        student_sql = text("SELECT id, first_name, last_name FROM students WHERE id = :sender_id AND is_deleted = false")
        result = await db.execute(student_sql, {"sender_id": sender_id})
        student = result.fetchone()
        results["student"] = {"found": bool(student), "data": f"{student[1]} {student[2]}" if student else None}
        
        # Check teachers
        teacher_sql = text("SELECT id, teacher_id FROM teachers WHERE id = :sender_id AND is_deleted = false")
        result = await db.execute(teacher_sql, {"sender_id": sender_id})
        teacher = result.fetchone()
        results["teacher"] = {"found": bool(teacher), "data": teacher[1] if teacher else None}
        
        # Check school_authorities
        sa_sql = text("SELECT id, first_name, last_name FROM school_authorities WHERE id = :sender_id AND is_deleted = false")
        result = await db.execute(sa_sql, {"sender_id": sender_id})
        sa = result.fetchone()
        results["school_authority"] = {"found": bool(sa), "data": f"{sa[1]} {sa[2]}" if sa else None}
        
        return {
            "sender_id": sender_id,
            "results": results
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

        
    

@router.get("/debug/student-classes/{student_id}")
async def debug_student_classes(
    student_id: str,
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Debug: Check student's class assignment (without enrollments table)"""
    try:
        # Check if student has class_id field
        student_class_sql = text("""
            SELECT 
                s.id,
                s.class_id,
                s.first_name,
                s.last_name,
                c.class_name,
                c.grade_level,
                c.section
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.id = :student_id
            AND s.tenant_id = :tenant_id
            AND s.is_deleted = false
        """)
        
        result = await db.execute(student_class_sql, {"student_id": student_id, "tenant_id": tenant_id})
        student_data = result.fetchone()
        
        if not student_data:
            return {"error": "Student not found"}
        
        return {
            "student_id": student_id,
            "tenant_id": tenant_id,
            "student_name": f"{student_data[2]} {student_data[3]}",
            "class_id": str(student_data[1]) if student_data[1] else None,
            "class_name": student_data[4],
            "grade_level": student_data[5],
            "section": student_data[6]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

@router.get("/debug/available-classes")
async def debug_available_classes(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Debug: Check what classes exist in the tenant (without enrollments)"""
    try:
        classes_sql = text("""
            SELECT 
                c.id,
                c.class_name,
                c.grade_level,
                c.section,
                c.status,
                COUNT(s.id) as student_count
            FROM classes c
            LEFT JOIN students s ON c.id = s.class_id AND s.status = 'active' AND s.is_deleted = false
            WHERE c.tenant_id = :tenant_id
            AND c.is_deleted = false
            GROUP BY c.id, c.class_name, c.grade_level, c.section, c.status
            ORDER BY c.grade_level, c.section
        """)
        
        result = await db.execute(classes_sql, {"tenant_id": tenant_id})
        classes = result.fetchall()
        
        return {
            "tenant_id": tenant_id,
            "total_classes": len(classes),
            "classes": [
                {
                    "class_id": str(c[0]),
                    "class_name": c[1],
                    "grade_level": c[2],
                    "section": c[3],
                    "status": c[4],
                    "student_count": c[5]
                } for c in classes
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")