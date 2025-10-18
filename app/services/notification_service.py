# app/services/notification_service.py
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func, desc, and_, or_
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .base_service import BaseService
from ..models.tenant_specific.notification import (
    Notification, NotificationRecipient, NotificationTemplate, 
    NotificationDeliveryLog, NotificationPreference, NotificationGroup,
    NotificationSchedule, NotificationBatch,
    NotificationType, NotificationPriority, NotificationStatus, 
    DeliveryChannel, RecipientType, SenderType
)


class NotificationService(BaseService[Notification]):
    def __init__(self, db: AsyncSession):
        super().__init__(Notification, db)
    
    async def create_notification(
        self, 
        sender_id: UUID,
        sender_type: SenderType,
        notification_data: dict
    ) -> Notification:
        """Create and send notification - FIXED VERSION"""
        
        print(f"DEBUG: Creating notification for sender {sender_id}")
        print(f"DEBUG: Sender type: {sender_type}")
        print(f"DEBUG: Notification data: {notification_data}")
        
        # Validate sender permissions
        if not await self._validate_sender_permissions(sender_id, sender_type, notification_data):
            raise HTTPException(status_code=403, detail="Insufficient permissions to send notification")
        
        # Create notification
        notification = Notification(
            sender_id=sender_id,
            sender_type=sender_type,
            **notification_data
        )
        self.db.add(notification)
        await self.db.flush()  # Get ID without committing
        
        print(f"DEBUG: Created notification with ID: {notification.id}")
        
        # Generate recipients
        recipients = await self._generate_recipients(notification)
        notification.total_recipients = len(recipients)
        
        print(f"DEBUG: Generated {len(recipients)} recipients")
        
        # Add recipients to database - FIXED VERSION
        for recipient_data in recipients:
            recipient = NotificationRecipient(
                notification_id=notification.id,
                tenant_id=recipient_data["tenant_id"],
                recipient_id=recipient_data["recipient_id"],
                recipient_type=recipient_data["recipient_type"],
                recipient_name=recipient_data["recipient_name"],
                recipient_email=recipient_data.get("recipient_email"),
                recipient_phone=recipient_data.get("recipient_phone"),
                status=NotificationStatus.DELIVERED,  # Set initial status
                delivered_at=datetime.utcnow(),  # Set delivery timestamp
            )
            self.db.add(recipient)
            print(f"DEBUG: Added recipient: {recipient_data['recipient_name']} ({recipient_data['recipient_id']})")
        
        # Update notification status and counts
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        notification.delivered_count = len(recipients)
        
        await self.db.commit()
        await self.db.refresh(notification)
        
        print(f"DEBUG: Notification committed successfully")
        print(f"DEBUG: Total recipients: {notification.total_recipients}")
        print(f"DEBUG: Delivered count: {notification.delivered_count}")
        
        return notification
    
    # MAIN METHODS THAT YOUR FLUTTER APP NEEDS
    
    async def get_notifications_for_user(
        self,
        user_id: UUID,
        user_type: str,
        tenant_id: UUID,
        notification_type: Optional[str] = None,
        status: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[dict]:
        """Get notifications for a specific user (student/teacher) - FIXED VERSION"""
        
        try:
            print(f"DEBUG: Getting notifications for user {user_id}, type {user_type}, tenant {tenant_id}")
            print(f"DEBUG: Unread only: {unread_only}")
            
            # Convert UUID to string for comparison
            user_id_str = str(user_id)
            tenant_id_str = str(tenant_id)
            
            # Base query to get notifications for the user
            base_where = """
                WHERE nr.recipient_id = :user_id 
                AND nr.recipient_type = :user_type 
                AND n.tenant_id = :tenant_id 
                AND n.is_deleted = false 
                AND nr.is_deleted = false
            """
            
            params = {
                "user_id": user_id_str,
                "user_type": user_type,
                "tenant_id": tenant_id_str
            }
            
            # Add additional filters
            if notification_type:
                base_where += " AND n.notification_type = :notification_type"
                params["notification_type"] = notification_type
            
            if status:
                base_where += " AND n.status = :status"
                params["status"] = status
            
            if unread_only:
                base_where += " AND nr.read_at IS NULL"
            
            # Main query
            notifications_sql = text(f"""
                SELECT 
                    n.id,
                    n.tenant_id,
                    n.sender_id,
                    n.sender_type,
                    n.title,
                    n.message,
                    n.short_message,
                    n.notification_type,
                    n.priority,
                    n.recipient_type,
                    n.recipient_config,
                    n.delivery_channels,
                    n.scheduled_at,
                    n.expires_at,
                    n.attachments,
                    n.action_url,
                    n.action_text,
                    n.category,
                    n.tags,
                    n.academic_year,
                    n.term,
                    n.status,
                    n.sent_at,
                    n.created_at,
                    n.updated_at,
                    nr.read_at,
                    CASE WHEN nr.read_at IS NULL THEN false ELSE true END as is_read
                FROM notifications n
                JOIN notification_recipients nr ON n.id = nr.notification_id
                {base_where}
                ORDER BY n.created_at DESC
                LIMIT :limit
            """)
            
            params["limit"] = limit
            
            result = await self.db.execute(notifications_sql, params)
            rows = result.fetchall()
            
            print(f"DEBUG: Found {len(rows)} notifications for user")
            
            notifications = []
            for row in rows:
                notification = {
                    "id": str(row[0]),
                    "tenant_id": str(row[1]),
                    "sender_id": str(row[2]),
                    "sender_type": row[3],
                    "title": row[4],
                    "message": row[5],
                    "short_message": row[6],
                    "notification_type": row[7],
                    "priority": row[8],
                    "recipient_type": row[9],
                    "recipient_config": row[10],
                    "delivery_channels": row[11],
                    "scheduled_at": row[12].isoformat() if row[12] else None,
                    "expires_at": row[13].isoformat() if row[13] else None,
                    "attachments": row[14],
                    "action_url": row[15],
                    "action_text": row[16],
                    "category": row[17],
                    "tags": row[18],
                    "academic_year": row[19],
                    "term": row[20],
                    "status": row[21],
                    "sent_at": row[22].isoformat() if row[22] else None,
                    "created_at": row[23].isoformat() if row[23] else None,
                    "updated_at": row[24].isoformat() if row[24] else None,
                    "read_at": row[25].isoformat() if row[25] else None,
                    "is_read": row[26]
                }
                notifications.append(notification)
            
            return notifications
            
        except Exception as e:
            print(f"DEBUG: Error getting notifications: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get user notifications: {str(e)}")

    async def mark_notification_as_read(
        self,
        notification_id: UUID,
        user_id: UUID
    ) -> dict:
        """Mark a specific notification as read for a user"""
        
        try:
            now = datetime.utcnow()
            
            # Update the notification recipient record
            update_sql = text("""
                UPDATE notification_recipients
                SET read_at = :read_at,
                    status = 'read',
                    updated_at = :updated_at
                WHERE notification_id = :notification_id
                AND recipient_id = :user_id
                AND read_at IS NULL
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                update_sql,
                {
                    "read_at": now,
                    "updated_at": now,
                    "notification_id": str(notification_id),
                    "user_id": str(user_id)
                }
            )
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Notification not found or already read")
            
            # Update read count in the notification
            update_count_sql = text("""
                UPDATE notifications
                SET read_count = (
                    SELECT COUNT(*)
                    FROM notification_recipients nr
                    WHERE nr.notification_id = notifications.id
                    AND nr.read_at IS NOT NULL
                    AND nr.is_deleted = false
                ),
                updated_at = :updated_at
                WHERE id = :notification_id
            """)
            
            await self.db.execute(
                update_count_sql,
                {
                    "updated_at": now,
                    "notification_id": str(notification_id)
                }
            )
            
            await self.db.commit()
            
            return {
                "message": "Notification marked as read",
                "notification_id": str(notification_id),
                "user_id": str(user_id),
                "read_at": now.isoformat()
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")

    # FIXED RECIPIENT GENERATION METHOD
    async def _generate_recipients(self, notification: Notification) -> List[Dict[str, Any]]:
        """Generate list of recipients based on notification configuration - FIXED VERSION"""
        
        print(f"DEBUG: Generating recipients for notification {notification.id}")
        print(f"DEBUG: Recipient type: {notification.recipient_type}")
        print(f"DEBUG: Recipient config: {notification.recipient_config}")
        print(f"DEBUG: Tenant ID: {notification.tenant_id}")
        
        recipients = []
        recipient_type = notification.recipient_type
        recipient_config = notification.recipient_config or {}
        
        try:
            if recipient_type == RecipientType.INDIVIDUAL:
                # Individual recipients
                student_ids = recipient_config.get("student_ids", [])
                teacher_ids = recipient_config.get("teacher_ids", [])
                
                print(f"DEBUG: Individual - Student IDs: {student_ids}")
                print(f"DEBUG: Individual - Teacher IDs: {teacher_ids}")
                
                # Get student details
                if student_ids:
                    student_sql = text("""
                        SELECT id, first_name, last_name, email, phone
                        FROM students
                        WHERE id = ANY(:student_ids)
                        AND tenant_id = :tenant_id
                        AND is_deleted = false
                    """)
                    
                    result = await self.db.execute(
                        student_sql,
                        {"student_ids": [str(sid) for sid in student_ids], "tenant_id": str(notification.tenant_id)}
                    )
                    
                    student_rows = result.fetchall()
                    print(f"DEBUG: Found {len(student_rows)} students")
                    
                    for row in student_rows:
                        recipients.append({
                            "tenant_id": str(notification.tenant_id),
                            "recipient_id": str(row[0]),
                            "recipient_type": "student",
                            "recipient_name": f"{row[1]} {row[2]}",
                            "recipient_email": row[3],
                            "recipient_phone": row[4]
                        })
                
                # Get teacher details
                if teacher_ids:
                    teacher_sql = text("""
                        SELECT id, 
                               personal_info->>'basic_details'->>'first_name' as first_name,
                               personal_info->>'basic_details'->>'last_name' as last_name,
                               personal_info->>'contact_info'->>'primary_email' as email,
                               personal_info->>'contact_info'->>'primary_phone' as phone
                        FROM teachers
                        WHERE id = ANY(:teacher_ids)
                        AND tenant_id = :tenant_id
                        AND is_deleted = false
                    """)
                    
                    result = await self.db.execute(
                        teacher_sql,
                        {"teacher_ids": [str(tid) for tid in teacher_ids], "tenant_id": str(notification.tenant_id)}
                    )
                    
                    teacher_rows = result.fetchall()
                    print(f"DEBUG: Found {len(teacher_rows)} teachers")
                    
                    for row in teacher_rows:
                        recipients.append({
                            "tenant_id": str(notification.tenant_id),
                            "recipient_id": str(row[0]),
                            "recipient_type": "teacher",
                            "recipient_name": f"{row[1] or ''} {row[2] or ''}".strip(),
                            "recipient_email": row[3],
                            "recipient_phone": row[4]
                        })
            
            elif recipient_type == RecipientType.ALL_STUDENTS:
                print("DEBUG: Getting all students")
                # All students in tenant
                all_students_sql = text("""
                    SELECT id, first_name, last_name, email, phone
                    FROM students
                    WHERE tenant_id = :tenant_id
                    AND status = 'active'
                    AND is_deleted = false
                """)
                
                result = await self.db.execute(all_students_sql, {"tenant_id": str(notification.tenant_id)})
                student_rows = result.fetchall()
                print(f"DEBUG: Found {len(student_rows)} active students")
                
                for row in student_rows:
                    recipients.append({
                        "tenant_id": str(notification.tenant_id),
                        "recipient_id": str(row[0]),
                        "recipient_type": "student",
                        "recipient_name": f"{row[1]} {row[2]}",
                        "recipient_email": row[3],
                        "recipient_phone": row[4]
                    })
            
            elif recipient_type == RecipientType.ALL_TEACHERS:
                print("DEBUG: Getting all teachers")
                # All teachers in tenant
                all_teachers_sql = text("""
                    SELECT id,
                           personal_info->>'basic_details'->>'first_name' as first_name,
                           personal_info->>'basic_details'->>'last_name' as last_name,
                           personal_info->>'contact_info'->>'primary_email' as email,
                           personal_info->>'contact_info'->>'primary_phone' as phone
                    FROM teachers
                    WHERE tenant_id = :tenant_id
                    AND status = 'active'
                    AND is_deleted = false
                """)
                
                result = await self.db.execute(all_teachers_sql, {"tenant_id": str(notification.tenant_id)})
                teacher_rows = result.fetchall()
                print(f"DEBUG: Found {len(teacher_rows)} active teachers")
                
                for row in teacher_rows:
                    recipients.append({
                        "tenant_id": str(notification.tenant_id),
                        "recipient_id": str(row[0]),
                        "recipient_type": "teacher",
                        "recipient_name": f"{row[1] or ''} {row[2] or ''}".strip(),
                        "recipient_email": row[3],
                        "recipient_phone": row[4]
                    })
            
            elif recipient_type == RecipientType.CLASS:
                # Students in specific classes
                class_ids = recipient_config.get("class_ids", [])
                
                print(f"DEBUG: Class - Class IDs: {class_ids}")
                
                if class_ids:
                    class_students_sql = text("""
                        SELECT s.id, s.first_name, s.last_name, s.email, s.phone
                        FROM students s
                        JOIN enrollments e ON s.id = e.student_id
                        WHERE e.class_id = ANY(:class_ids)
                        AND s.tenant_id = :tenant_id
                        AND s.is_deleted = false
                        AND e.status = 'active'
                        AND e.is_deleted = false
                    """)
                    
                    result = await self.db.execute(
                        class_students_sql,
                        {"class_ids": [str(cid) for cid in class_ids], "tenant_id": str(notification.tenant_id)}
                    )
                    
                    class_rows = result.fetchall()
                    print(f"DEBUG: Found {len(class_rows)} students in classes")
                    
                    for row in class_rows:
                        recipients.append({
                            "tenant_id": str(notification.tenant_id),
                            "recipient_id": str(row[0]),
                            "recipient_type": "student",
                            "recipient_name": f"{row[1]} {row[2]}",
                            "recipient_email": row[3],
                            "recipient_phone": row[4]
                        })
            
            elif recipient_type == RecipientType.GRADE:
                # Students in specific grades
                grade_levels = recipient_config.get("grade_levels", [])
                
                print(f"DEBUG: Grade - Grade levels: {grade_levels}")
                
                if grade_levels:
                    grade_students_sql = text("""
                        SELECT id, first_name, last_name, email, phone
                        FROM students
                        WHERE grade_level = ANY(:grade_levels)
                        AND tenant_id = :tenant_id
                        AND status = 'active'
                        AND is_deleted = false
                    """)
                    
                    result = await self.db.execute(
                        grade_students_sql,
                        {"grade_levels": grade_levels, "tenant_id": str(notification.tenant_id)}
                    )
                    
                    grade_rows = result.fetchall()
                    print(f"DEBUG: Found {len(grade_rows)} students in grades")
                    
                    for row in grade_rows:
                        recipients.append({
                            "tenant_id": str(notification.tenant_id),
                            "recipient_id": str(row[0]),
                            "recipient_type": "student",
                            "recipient_name": f"{row[1]} {row[2]}",
                            "recipient_email": row[3],
                            "recipient_phone": row[4]
                        })
            
            print(f"DEBUG: Generated {len(recipients)} total recipients")
            for i, recipient in enumerate(recipients):
                print(f"DEBUG: Recipient {i+1}: {recipient['recipient_name']} ({recipient['recipient_id']})")
            
            return recipients
            
        except Exception as e:
            print(f"DEBUG: Error in _generate_recipients: {str(e)}")
            raise e
    
    # Keep all existing validation and utility methods
    async def _validate_sender_permissions(
        self, 
        sender_id: UUID, 
        sender_type: SenderType, 
        notification_data: dict
    ) -> bool:
        """Validate if sender has permission to send notification"""
        
        recipient_type = notification_data.get("recipient_type")
        
        if sender_type == SenderType.SCHOOL_AUTHORITY or sender_type == SenderType.ADMIN:
            return True
        
        elif sender_type == SenderType.TEACHER:
            if recipient_type in [
                RecipientType.INDIVIDUAL,
                RecipientType.CLASS, 
                RecipientType.GRADE,
                RecipientType.ALL_STUDENTS,
                RecipientType.CUSTOM_GROUP
            ]:
                return await self._verify_teacher_assignment(sender_id, notification_data)
            else:
                return False
        
        return False
    
    async def _verify_teacher_assignment(self, teacher_id: UUID, notification_data: dict) -> bool:
        """Verify teacher is assigned to the target class/students"""
        # For now, return True - implement based on your specific requirements
        return True
