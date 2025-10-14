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
        """Create and send notification"""
        
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
        
        # Generate recipients
        recipients = await self._generate_recipients(notification)
        notification.total_recipients = len(recipients)
        
        # Add recipients to database
        for recipient_data in recipients:
            recipient = NotificationRecipient(
                notification_id=notification.id,
                **recipient_data
            )
            self.db.add(recipient)
        
        # Update notification status
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(notification)
        
        # Trigger delivery (async in production)
        await self._trigger_delivery(notification)
        
        return notification
    
    # BULK OPERATIONS USING RAW SQL FOR HIGH PERFORMANCE
    
    async def bulk_create_notifications(self, notifications_data: List[dict], tenant_id: UUID) -> dict:
        """Bulk create notifications using raw SQL for maximum performance"""
        try:
            if not notifications_data:
                raise HTTPException(status_code=400, detail="No notification data provided")
            
            # Validate and prepare bulk insert data
            now = datetime.utcnow()
            insert_data = []
            validation_errors = []
            
            for idx, notification_data in enumerate(notifications_data):
                try:
                    # Validate required fields
                    required_fields = ["sender_id", "sender_type", "title", "message", "notification_type", "recipient_type"]
                    for field in required_fields:
                        if not notification_data.get(field):
                            validation_errors.append(f"Row {idx + 1}: Missing required field '{field}'")
                            continue
                    
                    if validation_errors:
                        continue
                    
                    # Prepare notification record
                    notification_record = {
                        "id": str(uuid.uuid4()),
                        "tenant_id": str(tenant_id),
                        "sender_id": str(notification_data["sender_id"]),
                        "sender_type": notification_data["sender_type"],
                        "title": notification_data["title"],
                        "message": notification_data["message"],
                        "short_message": notification_data.get("short_message"),
                        "notification_type": notification_data["notification_type"],
                        "priority": notification_data.get("priority", "normal"),
                        "recipient_type": notification_data["recipient_type"],
                        "recipient_config": notification_data.get("recipient_config"),
                        "delivery_channels": notification_data.get("delivery_channels", ["in_app"]),
                        "scheduled_at": notification_data.get("scheduled_at"),
                        "expires_at": notification_data.get("expires_at"),
                        "attachments": notification_data.get("attachments"),
                        "action_url": notification_data.get("action_url"),
                        "action_text": notification_data.get("action_text"),
                        "category": notification_data.get("category"),
                        "tags": notification_data.get("tags"),
                        "academic_year": notification_data.get("academic_year"),
                        "term": notification_data.get("term"),
                        "status": "sent",
                        "sent_at": now,
                        "created_at": now,
                        "updated_at": now,
                        "is_deleted": False
                    }
                    insert_data.append(notification_record)
                    
                except Exception as e:
                    validation_errors.append(f"Row {idx + 1}: {str(e)}")
            
            if validation_errors:
                raise HTTPException(
                    status_code=400, 
                    detail={"message": "Validation errors found", "errors": validation_errors}
                )
            
            # Bulk insert using raw SQL
            bulk_insert_sql = text("""
                INSERT INTO notifications (
                    id, tenant_id, sender_id, sender_type, title, message, short_message,
                    notification_type, priority, recipient_type, recipient_config,
                    delivery_channels, scheduled_at, expires_at, attachments, action_url,
                    action_text, category, tags, academic_year, term, status, sent_at,
                    total_recipients, delivered_count, read_count, failed_count,
                    created_at, updated_at, is_deleted
                ) VALUES (
                    :id, :tenant_id, :sender_id, :sender_type, :title, :message, :short_message,
                    :notification_type, :priority, :recipient_type, :recipient_config,
                    :delivery_channels, :scheduled_at, :expires_at, :attachments, :action_url,
                    :action_text, :category, :tags, :academic_year, :term, :status, :sent_at,
                    0, 0, 0, 0, :created_at, :updated_at, :is_deleted
                )
            """)
            
            await self.db.execute(bulk_insert_sql, insert_data)
            await self.db.commit()
            
            return {
                "total_records_processed": len(notifications_data),
                "successful_imports": len(insert_data),
                "failed_imports": len(validation_errors),
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk notification creation failed: {str(e)}")
    
    async def bulk_send_to_recipients(self, notification_ids: List[UUID], recipient_configs: List[dict]) -> dict:
        """Bulk send notifications to multiple recipient configurations"""
        try:
            if len(notification_ids) != len(recipient_configs):
                raise HTTPException(status_code=400, detail="Notification IDs and recipient configs count mismatch")
            
            total_recipients = 0
            processed_notifications = 0
            
            for notification_id, recipient_config in zip(notification_ids, recipient_configs):
                # Get notification
                notification = await self.get(notification_id)
                if not notification:
                    continue
                
                # Generate recipients for this config
                notification.recipient_config = recipient_config
                recipients = await self._generate_recipients(notification)
                
                # Bulk insert recipients
                now = datetime.utcnow()
                recipient_data = []
                
                for recipient in recipients:
                    recipient_data.append({
                        "id": str(uuid.uuid4()),
                        "tenant_id": str(notification.tenant_id),
                        "notification_id": str(notification_id),
                        "recipient_id": str(recipient["recipient_id"]),
                        "recipient_type": recipient["recipient_type"],
                        "recipient_name": recipient.get("recipient_name"),
                        "recipient_email": recipient.get("recipient_email"),
                        "recipient_phone": recipient.get("recipient_phone"),
                        "status": "sent",
                        "created_at": now,
                        "updated_at": now,
                        "is_deleted": False
                    })
                
                if recipient_data:
                    bulk_recipient_sql = text("""
                        INSERT INTO notification_recipients (
                            id, tenant_id, notification_id, recipient_id, recipient_type,
                            recipient_name, recipient_email, recipient_phone, status,
                            created_at, updated_at, is_deleted
                        ) VALUES (
                            :id, :tenant_id, :notification_id, :recipient_id, :recipient_type,
                            :recipient_name, :recipient_email, :recipient_phone, :status,
                            :created_at, :updated_at, :is_deleted
                        )
                    """)
                    
                    await self.db.execute(bulk_recipient_sql, recipient_data)
                    
                    # Update notification recipient count
                    update_count_sql = text("""
                        UPDATE notifications
                        SET total_recipients = :total_recipients,
                            updated_at = :updated_at
                        WHERE id = :notification_id
                    """)
                    
                    await self.db.execute(
                        update_count_sql,
                        {
                            "total_recipients": len(recipient_data),
                            "updated_at": now,
                            "notification_id": notification_id
                        }
                    )
                    
                    total_recipients += len(recipient_data)
                    processed_notifications += 1
            
            await self.db.commit()
            
            return {
                "processed_notifications": processed_notifications,
                "total_recipients_added": total_recipients,
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk send failed: {str(e)}")
    
    async def bulk_update_notification_status(self, notification_ids: List[UUID], new_status: str, tenant_id: UUID) -> dict:
        """Bulk update notification status using raw SQL"""
        try:
            if not notification_ids:
                raise HTTPException(status_code=400, detail="No notification IDs provided")
            
            valid_statuses = ["draft", "scheduled", "sent", "delivered", "archived", "cancelled"]
            if new_status not in valid_statuses:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid status. Must be one of: {valid_statuses}"
                )
            
            update_sql = text("""
                UPDATE notifications
                SET status = :new_status,
                    updated_at = :updated_at
                WHERE tenant_id = :tenant_id
                AND id = ANY(:notification_ids)
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                update_sql,
                {
                    "new_status": new_status,
                    "updated_at": datetime.utcnow(),
                    "tenant_id": tenant_id,
                    "notification_ids": [str(nid) for nid in notification_ids]
                }
            )
            
            await self.db.commit()
            
            return {
                "updated_notifications": result.rowcount,
                "new_status": new_status,
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk status update failed: {str(e)}")
    
    async def bulk_schedule_notifications(self, schedule_data: List[dict], tenant_id: UUID) -> dict:
        """Bulk schedule notifications using raw SQL"""
        try:
            if not schedule_data:
                raise HTTPException(status_code=400, detail="No schedule data provided")
            
            scheduled_count = 0
            for schedule in schedule_data:
                notification_id = schedule["notification_id"]
                scheduled_at = schedule["scheduled_at"]
                
                update_sql = text("""
                    UPDATE notifications
                    SET status = 'scheduled',
                        scheduled_at = :scheduled_at,
                        updated_at = :updated_at
                    WHERE id = :notification_id
                    AND tenant_id = :tenant_id
                    AND is_deleted = false
                """)
                
                result = await self.db.execute(
                    update_sql,
                    {
                        "scheduled_at": scheduled_at,
                        "updated_at": datetime.utcnow(),
                        "notification_id": notification_id,
                        "tenant_id": tenant_id
                    }
                )
                
                if result.rowcount > 0:
                    scheduled_count += 1
            
            await self.db.commit()
            
            return {
                "scheduled_notifications": scheduled_count,
                "total_requests": len(schedule_data),
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk scheduling failed: {str(e)}")
    
    async def bulk_mark_as_read(self, notification_ids: List[UUID], user_id: UUID, user_type: str) -> dict:
        """Bulk mark notifications as read for a user"""
        try:
            if not notification_ids:
                raise HTTPException(status_code=400, detail="No notification IDs provided")
            
            now = datetime.utcnow()
            
            # Update recipient records
            update_recipients_sql = text("""
                UPDATE notification_recipients
                SET status = 'read',
                    read_at = :read_at,
                    updated_at = :updated_at
                WHERE recipient_id = :user_id
                AND recipient_type = :user_type
                AND notification_id = ANY(:notification_ids)
                AND read_at IS NULL
                AND is_deleted = false
            """)
            
            result = await self.db.execute(
                update_recipients_sql,
                {
                    "read_at": now,
                    "updated_at": now,
                    "user_id": user_id,
                    "user_type": user_type,
                    "notification_ids": [str(nid) for nid in notification_ids]
                }
            )
            
            # Update read counts in notifications
            update_counts_sql = text("""
                UPDATE notifications
                SET read_count = (
                    SELECT COUNT(*)
                    FROM notification_recipients nr
                    WHERE nr.notification_id = notifications.id
                    AND nr.read_at IS NOT NULL
                    AND nr.is_deleted = false
                ),
                updated_at = :updated_at
                WHERE id = ANY(:notification_ids)
            """)
            
            await self.db.execute(
                update_counts_sql,
                {
                    "updated_at": now,
                    "notification_ids": [str(nid) for nid in notification_ids]
                }
            )
            
            await self.db.commit()
            
            return {
                "marked_as_read": result.rowcount,
                "user_id": str(user_id),
                "user_type": user_type,
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk mark as read failed: {str(e)}")
    
    async def bulk_delete_notifications(self, notification_ids: List[UUID], tenant_id: UUID, hard_delete: bool = False) -> dict:
        """Bulk delete notifications using raw SQL"""
        try:
            if not notification_ids:
                raise HTTPException(status_code=400, detail="No notification IDs provided")
            
            if hard_delete:
                # Hard delete - remove completely
                delete_recipients_sql = text("""
                    DELETE FROM notification_recipients
                    WHERE notification_id = ANY(:notification_ids)
                    AND tenant_id = :tenant_id
                """)
                
                delete_logs_sql = text("""
                    DELETE FROM notification_delivery_logs
                    WHERE notification_id = ANY(:notification_ids)
                    AND tenant_id = :tenant_id
                """)
                
                delete_notifications_sql = text("""
                    DELETE FROM notifications
                    WHERE id = ANY(:notification_ids)
                    AND tenant_id = :tenant_id
                """)
                
                # Execute in order
                await self.db.execute(
                    delete_recipients_sql,
                    {"notification_ids": [str(nid) for nid in notification_ids], "tenant_id": tenant_id}
                )
                
                await self.db.execute(
                    delete_logs_sql,
                    {"notification_ids": [str(nid) for nid in notification_ids], "tenant_id": tenant_id}
                )
                
                result = await self.db.execute(
                    delete_notifications_sql,
                    {"notification_ids": [str(nid) for nid in notification_ids], "tenant_id": tenant_id}
                )
                
            else:
                # Soft delete
                soft_delete_sql = text("""
                    UPDATE notifications
                    SET is_deleted = true,
                        status = 'archived',
                        updated_at = :updated_at
                    WHERE id = ANY(:notification_ids)
                    AND tenant_id = :tenant_id
                    AND is_deleted = false
                """)
                
                result = await self.db.execute(
                    soft_delete_sql,
                    {
                        "updated_at": datetime.utcnow(),
                        "notification_ids": [str(nid) for nid in notification_ids],
                        "tenant_id": tenant_id
                    }
                )
            
            await self.db.commit()
            
            return {
                "deleted_notifications": result.rowcount,
                "delete_type": "hard" if hard_delete else "soft",
                "tenant_id": str(tenant_id),
                "status": "success"
            }
            
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Bulk delete failed: {str(e)}")
    
    async def get_comprehensive_notification_statistics(self, tenant_id: UUID, date_range: Optional[dict] = None) -> dict:
        """Get comprehensive notification statistics using raw SQL for performance"""
        try:
            base_where = "WHERE n.tenant_id = :tenant_id AND n.is_deleted = false"
            params = {"tenant_id": tenant_id}
            
            if date_range:
                if date_range.get("start_date"):
                    base_where += " AND n.sent_at >= :start_date"
                    params["start_date"] = date_range["start_date"]
                if date_range.get("end_date"):
                    base_where += " AND n.sent_at <= :end_date"
                    params["end_date"] = date_range["end_date"]
            
            # Main statistics
            stats_sql = text(f"""
                SELECT 
                    COUNT(*) as total_notifications,
                    COUNT(CASE WHEN n.status = 'sent' THEN 1 END) as sent_notifications,
                    COUNT(CASE WHEN n.status = 'delivered' THEN 1 END) as delivered_notifications,
                    COUNT(CASE WHEN n.status = 'failed' THEN 1 END) as failed_notifications,
                    SUM(n.total_recipients) as total_recipients,
                    SUM(n.delivered_count) as total_delivered,
                    SUM(n.read_count) as total_read,
                    SUM(n.failed_count) as total_failed,
                    SUM(n.clicked_count) as total_clicked,
                    AVG(n.total_recipients) as avg_recipients_per_notification
                FROM notifications n
                {base_where}
            """)
            
            result = await self.db.execute(stats_sql, params)
            stats = result.fetchone()
            
            # Notification type distribution
            type_distribution_sql = text(f"""
                SELECT n.notification_type, COUNT(*) as count
                FROM notifications n
                {base_where}
                GROUP BY n.notification_type
                ORDER BY count DESC
            """)
            
            type_result = await self.db.execute(type_distribution_sql, params)
            type_distribution = {row[0]: row[1] for row in type_result.fetchall()}
            
            # Priority distribution
            priority_distribution_sql = text(f"""
                SELECT n.priority, COUNT(*) as count
                FROM notifications n
                {base_where}
                GROUP BY n.priority
                ORDER BY count DESC
            """)
            
            priority_result = await self.db.execute(priority_distribution_sql, params)
            priority_distribution = {row[0]: row[1] for row in priority_result.fetchall()}
            
            # Channel performance
            channel_performance_sql = text(f"""
                SELECT 
                    ndl.channel,
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN ndl.status = 'success' THEN 1 END) as successful_deliveries,
                    AVG(EXTRACT(EPOCH FROM (ndl.delivered_at - ndl.attempted_at))) as avg_delivery_time_seconds
                FROM notification_delivery_logs ndl
                JOIN notifications n ON ndl.notification_id = n.id
                {base_where.replace('n.', 'n.')}
                GROUP BY ndl.channel
            """)
            
            channel_result = await self.db.execute(channel_performance_sql, params)
            channel_performance = {}
            for row in channel_result.fetchall():
                channel_performance[row[0]] = {
                    "total_attempts": row[1],
                    "successful_deliveries": row[2],
                    "success_rate": round((row[2] / row[1] * 100), 2) if row[1] > 0 else 0,
                    "avg_delivery_time_seconds": float(row[3]) if row[3] else 0
                }
            
            return {
                "total_notifications": stats[0] or 0,
                "sent_notifications": stats[1] or 0,
                "delivered_notifications": stats[2] or 0,
                "failed_notifications": stats[3] or 0,
                "total_recipients": stats[4] or 0,
                "total_delivered": stats[5] or 0,
                "total_read": stats[6] or 0,
                "total_failed": stats[7] or 0,
                "total_clicked": stats[8] or 0,
                "avg_recipients_per_notification": float(stats[9]) if stats[9] else 0,
                "delivery_rate": round((stats[5] / stats[4] * 100), 2) if stats[4] > 0 else 0,
                "read_rate": round((stats[6] / stats[5] * 100), 2) if stats[5] > 0 else 0,
                "click_rate": round((stats[8] / stats[6] * 100), 2) if stats[6] > 0 else 0,
                "notification_type_distribution": type_distribution,
                "priority_distribution": priority_distribution,
                "channel_performance": channel_performance,
                "tenant_id": str(tenant_id)
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
    
    # EXISTING METHODS (updated for async)
    
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
        # Implementation depends on your class-teacher relationship model
        # For now, return True - implement based on your specific requirements
        return True
    
    async def _generate_recipients(self, notification: Notification) -> List[Dict[str, Any]]:
        """Generate list of recipients based on notification configuration"""
        
        recipients = []
        recipient_type = notification.recipient_type
        recipient_config = notification.recipient_config or {}
        
        if recipient_type == RecipientType.INDIVIDUAL:
            # Individual recipients
            student_ids = recipient_config.get("student_ids", [])
            teacher_ids = recipient_config.get("teacher_ids", [])
            
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
                    {"student_ids": [str(sid) for sid in student_ids], "tenant_id": notification.tenant_id}
                )
                
                for row in result.fetchall():
                    recipients.append({
                        "tenant_id": notification.tenant_id,
                        "recipient_id": row[0],
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
                    {"teacher_ids": [str(tid) for tid in teacher_ids], "tenant_id": notification.tenant_id}
                )
                
                for row in result.fetchall():
                    recipients.append({
                        "tenant_id": notification.tenant_id,
                        "recipient_id": row[0],
                        "recipient_type": "teacher",
                        "recipient_name": f"{row[1] or ''} {row[2] or ''}".strip(),
                        "recipient_email": row[3],
                        "recipient_phone": row[4]
                    })
        
        elif recipient_type == RecipientType.CLASS:
            # Students in specific classes
            class_ids = recipient_config.get("class_ids", [])
            
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
                {"class_ids": [str(cid) for cid in class_ids], "tenant_id": notification.tenant_id}
            )
            
            for row in result.fetchall():
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": row[0],
                    "recipient_type": "student",
                    "recipient_name": f"{row[1]} {row[2]}",
                    "recipient_email": row[3],
                    "recipient_phone": row[4]
                })
        
        elif recipient_type == RecipientType.GRADE:
            # Students in specific grades
            grade_levels = recipient_config.get("grade_levels", [])
            
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
                {"grade_levels": grade_levels, "tenant_id": notification.tenant_id}
            )
            
            for row in result.fetchall():
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": row[0],
                    "recipient_type": "student",
                    "recipient_name": f"{row[1]} {row[2]}",
                    "recipient_email": row[3],
                    "recipient_phone": row[4]
                })
        
        elif recipient_type == RecipientType.ALL_STUDENTS:
            # All students in tenant
            all_students_sql = text("""
                SELECT id, first_name, last_name, email, phone
                FROM students
                WHERE tenant_id = :tenant_id
                AND status = 'active'
                AND is_deleted = false
            """)
            
            result = await self.db.execute(all_students_sql, {"tenant_id": notification.tenant_id})
            
            for row in result.fetchall():
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": row[0],
                    "recipient_type": "student",
                    "recipient_name": f"{row[1]} {row[2]}",
                    "recipient_email": row[3],
                    "recipient_phone": row[4]
                })
        
        elif recipient_type == RecipientType.ALL_TEACHERS:
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
            
            result = await self.db.execute(all_teachers_sql, {"tenant_id": notification.tenant_id})
            
            for row in result.fetchall():
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": row[0],
                    "recipient_type": "teacher",
                    "recipient_name": f"{row[1] or ''} {row[2] or ''}".strip(),
                    "recipient_email": row[3],
                    "recipient_phone": row[4]
                })
        
        return recipients
    
    async def _trigger_delivery(self, notification: Notification):
        """Trigger notification delivery through various channels"""
        
        # Get all recipients
        recipients_sql = text("""
            SELECT id, recipient_id, recipient_type, recipient_email, recipient_phone
            FROM notification_recipients
            WHERE notification_id = :notification_id
            AND is_deleted = false
        """)
        
        result = await self.db.execute(recipients_sql, {"notification_id": notification.id})
        recipients = result.fetchall()
        
        delivery_channels = notification.delivery_channels or ["in_app"]
        
        for recipient in recipients:
            for channel in delivery_channels:
                await self._send_via_channel(notification, recipient, channel)
    
    async def _send_via_channel(self, notification: Notification, recipient, channel: str):
        """Send notification via specific channel"""
        
        # Create delivery log
        delivery_log_sql = text("""
            INSERT INTO notification_delivery_logs (
                id, tenant_id, notification_id, recipient_id, channel,
                attempted_at, status, created_at, updated_at, is_deleted
            ) VALUES (
                :id, :tenant_id, :notification_id, :recipient_id, :channel,
                :attempted_at, :status, :created_at, :updated_at, :is_deleted
            )
        """)
        
        now = datetime.utcnow()
        
        await self.db.execute(
            delivery_log_sql,
            {
                "id": str(uuid.uuid4()),
                "tenant_id": notification.tenant_id,
                "notification_id": notification.id,
                "recipient_id": recipient[1],  # recipient_id
                "channel": channel,
                "attempted_at": now,
                "status": "success",
                "created_at": now,
                "updated_at": now,
                "is_deleted": False
            }
        )
        
        # Update recipient status
        update_recipient_sql = text("""
            UPDATE notification_recipients
            SET status = 'delivered',
                delivered_at = :delivered_at,
                updated_at = :updated_at
            WHERE id = :recipient_id
        """)
        
        await self.db.execute(
            update_recipient_sql,
            {
                "delivered_at": now,
                "updated_at": now,
                "recipient_id": recipient[0]  # id
            }
        )
        
        await self.db.commit()
        
        # Here you would integrate with actual delivery services:
        # - Email: SendGrid, AWS SES, etc.
        # - SMS: Twilio, AWS SNS, etc.  
        # - Push: Firebase, Apple Push, etc.
        # - In-app: WebSocket, Server-Sent Events, etc.
