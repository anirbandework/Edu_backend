from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import and_, or_, func, desc
from .base_service import BaseService
from ..models.tenant_specific.notification_service import (
    Notification, NotificationRecipient, NotificationTemplate, 
    NotificationDeliveryLog, NotificationPreference, NotificationGroup,
    NotificationType, NotificationPriority, NotificationStatus, 
    DeliveryChannel, RecipientType, SenderType
)

class NotificationService(BaseService[Notification]):
    async def __init__(self, db: Session):
        super().__init__(Notification, db)
    
    async def create_notification(
        self, 
        sender_id: UUID,
        sender_type: SenderType,
        notification_data: dict
    ) -> Notification:
        """Create and send notification"""
        
        # Validate sender permissions
        if not self._validate_sender_permissions(sender_id, sender_type, notification_data):
            raise ValueError("Insufficient permissions to send notification")
        
        # Create notification
        notification = Notification(
            sender_id=sender_id,
            sender_type=sender_type,
            **notification_data
        )
        self.db.add(notification)
        self.db.flush()  # Get the ID without committing
        
        # Generate recipients
        recipients = self._generate_recipients(notification)
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
        notification.sent_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(notification)
        
        # Trigger delivery (in real app, this would be async)
        self._trigger_delivery(notification)
        
        return notification
    
    async def _validate_sender_permissions(
        self, 
        sender_id: UUID, 
        sender_type: SenderType, 
        notification_data: dict
    ) -> bool:
        """Validate if sender has permission to send notification"""
        
        recipient_type = notification_data.get("recipient_type")
        
        if sender_type == SenderType.SCHOOL_AUTHORITY:
            # School authorities can send to anyone
            return True
        
        elif sender_type == SenderType.TEACHER:
            # Teachers can only send to students
            if recipient_type in [
                RecipientType.INDIVIDUAL,
                RecipientType.CLASS, 
                RecipientType.GRADE,
                RecipientType.ALL_STUDENTS,
                RecipientType.CUSTOM_GROUP
            ]:
                # Additional check: teacher should be assigned to the class/students
                return self._verify_teacher_assignment(sender_id, notification_data)
            else:
                return False  # Teachers cannot send to other teachers
        
        return False
    
    async def _verify_teacher_assignment(self, teacher_id: UUID, notification_data: dict) -> bool:
        """Verify teacher is assigned to the target class/students"""
        
        recipient_type = notification_data.get("recipient_type")
        recipient_config = notification_data.get("recipient_config", {})
        
        if recipient_type == RecipientType.CLASS:
            # Check if teacher is assigned to this class
            from ..models.tenant_specific.grades_assessment import ClassSubject
            
            class_id = recipient_config.get("class_id")
            if class_id:
                assignment = self.await db.execute(select(ClassSubject).filter(
                    ClassSubject.teacher_id == teacher_id,
                    ClassSubject.class_id == class_id,
                    ClassSubject.is_active == True
                ).first()
                return assignment is not None
        
        elif recipient_type == RecipientType.INDIVIDUAL:
            # Check if teacher teaches any of the individual students
            student_ids = recipient_config.get("student_ids", [])
            if student_ids:
                from ..models.tenant_specific.grades_assessment import ClassSubject
                from ..models.tenant_specific.student import Student
                
                # Get classes where teacher is assigned
                teacher_classes = self.await db.execute(select(ClassSubject.class_id).filter(
                    ClassSubject.teacher_id == teacher_id,
                    ClassSubject.is_active == True
                ).subquery()
                
                # Check if students are in any of teacher's classes
                student_in_class = self.await db.execute(select(Student).filter(
                    Student.id.in_(student_ids),
                    Student.class_id.in_(teacher_classes)
                ).first()
                
                return student_in_class is not None
        
        # For other cases, allow (can be restricted further based on requirements)
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
            
            for student_id in student_ids:
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": student_id,
                    "recipient_type": "student"
                })
            
            for teacher_id in teacher_ids:
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": teacher_id,
                    "recipient_type": "teacher"
                })
        
        elif recipient_type == RecipientType.CLASS:
            # All students in specific class(es)
            class_ids = recipient_config.get("class_ids", [])
            
            from ..models.tenant_specific.student import Student
            
            students = self.await db.execute(select(Student).filter(
                Student.class_id.in_(class_ids),
                Student.is_active == True,
                Student.is_deleted == False
            ).all()
            
            for student in students:
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": student.id,
                    "recipient_type": "student"
                })
        
        elif recipient_type == RecipientType.GRADE:
            # All students in specific grade level(s)
            grade_levels = recipient_config.get("grade_levels", [])
            
            from ..models.tenant_specific.student import Student
            
            students = self.await db.execute(select(Student).filter(
                Student.grade_level.in_(grade_levels),
                Student.tenant_id == notification.tenant_id,
                Student.is_active == True,
                Student.is_deleted == False
            ).all()
            
            for student in students:
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": student.id,
                    "recipient_type": "student"
                })
        
        elif recipient_type == RecipientType.ALL_STUDENTS:
            # All students in the tenant
            from ..models.tenant_specific.student import Student
            
            students = self.await db.execute(select(Student).filter(
                Student.tenant_id == notification.tenant_id,
                Student.is_active == True,
                Student.is_deleted == False
            ).all()
            
            for student in students:
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": student.id,
                    "recipient_type": "student"
                })
        
        elif recipient_type == RecipientType.ALL_TEACHERS:
            # All teachers in the tenant
            from ..models.tenant_specific.teacher import Teacher
            
            teachers = self.await db.execute(select(Teacher).filter(
                Teacher.tenant_id == notification.tenant_id,
                Teacher.status == "active",
                Teacher.is_deleted == False
            ).all()
            
            for teacher in teachers:
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": teacher.id,
                    "recipient_type": "teacher"
                })
        
        elif recipient_type == RecipientType.DEPARTMENT:
            # All teachers in specific department
            departments = recipient_config.get("departments", [])
            
            from ..models.tenant_specific.teacher import Teacher
            
            teachers = self.await db.execute(select(Teacher).filter(
                Teacher.tenant_id == notification.tenant_id,
                Teacher.employment["job_information"]["department"].astext.in_(departments),
                Teacher.status == "active",
                Teacher.is_deleted == False
            ).all()
            
            for teacher in teachers:
                recipients.append({
                    "tenant_id": notification.tenant_id,
                    "recipient_id": teacher.id,
                    "recipient_type": "teacher"
                })
        
        return recipients
    
    async def _trigger_delivery(self, notification: Notification):
        """Trigger notification delivery through various channels"""
        
        # Get all recipients
        recipients = self.await db.execute(select(NotificationRecipient).filter(
            NotificationRecipient.notification_id == notification.id
        ).all()
        
        delivery_channels = notification.delivery_channels or ["in_app"]
        
        for recipient in recipients:
            for channel in delivery_channels:
                self._send_via_channel(notification, recipient, channel)
    
    async def _send_via_channel(
        self, 
        notification: Notification, 
        recipient: NotificationRecipient, 
        channel: str
    ):
        """Send notification via specific channel"""
        
        # Create delivery log
        delivery_log = NotificationDeliveryLog(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
            recipient_id=recipient.recipient_id,
            channel=DeliveryChannel(channel),
            attempted_at=datetime.now(),
            status="success"  # In real implementation, this would depend on actual delivery
        )
        
        self.db.add(delivery_log)
        
        # Update recipient status
        recipient.status = NotificationStatus.DELIVERED
        recipient.delivered_at = datetime.now()
        
        self.db.commit()
        
        # Here you would integrate with actual delivery services:
        # - Email service (SendGrid, AWS SES, etc.)
        # - SMS service (Twilio, AWS SNS, etc.)  
        # - Push notification service (Firebase, etc.)
        # - In-app notification (WebSocket, etc.)
    
    async def get_notifications_for_user(
        self,
        user_id: UUID,
        user_type: str,
        tenant_id: UUID,
        notification_type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get notifications for a specific user"""
        
        query = self.await db.execute(select(
            Notification, NotificationRecipient
        ).join(
            NotificationRecipient
        ).filter(
            NotificationRecipient.recipient_id == user_id,
            NotificationRecipient.recipient_type == user_type,
            Notification.tenant_id == tenant_id,
            NotificationRecipient.is_deleted == False,
            Notification.is_deleted == False
        )
        
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)
        
        if status:
            query = query.filter(NotificationRecipient.status == status)
        
        if unread_only:
            query = query.filter(NotificationRecipient.read_at.is_(None))
        
        results = query.order_by(desc(Notification.sent_at)).limit(limit).all()
        
        notifications = []
        for notification, recipient in results:
            notifications.append({
                "id": str(notification.id),
                "title": notification.title,
                "message": notification.message,
                "notification_type": notification.notification_type.value,
                "priority": notification.priority.value,
                "sender_type": notification.sender_type.value,
                "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                "read_at": recipient.read_at.isoformat() if recipient.read_at else None,
                "is_starred": recipient.is_starred,
                "is_archived": recipient.is_archived,
                "action_url": notification.action_url,
                "action_text": notification.action_text,
                "attachments": notification.attachments,
                "recipient_status": recipient.status.value
            })
        
        return notifications
    
    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> bool:
        """Mark notification as read for specific user"""
        
        recipient = self.await db.execute(select(NotificationRecipient).filter(
            NotificationRecipient.notification_id == notification_id,
            NotificationRecipient.recipient_id == user_id
        ).first()
        
        if recipient and not recipient.read_at:
            recipient.read_at = datetime.now()
            recipient.status = NotificationStatus.READ
            self.db.commit()
            
            # Update notification read count
            notification = self.await db.execute(select(Notification).filter(
                Notification.id == notification_id
            ).first()
            
            if notification:
                notification.read_count += 1
                self.db.commit()
            
            return True
        
        return False
    
    async def get_notification_stats(
        self,
        sender_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get notification statistics for sender"""
        
        query = self.await db.execute(select(Notification).filter(
            Notification.sender_id == sender_id,
            Notification.is_deleted == False
        )
        
        if start_date:
            query = query.filter(Notification.sent_at >= start_date)
        
        if end_date:
            query = query.filter(Notification.sent_at <= end_date)
        
        notifications = query.all()
        
        total_sent = len(notifications)
        total_recipients = sum(n.total_recipients for n in notifications)
        total_delivered = sum(n.delivered_count for n in notifications)
        total_read = sum(n.read_count for n in notifications)
        
        return {
            "total_notifications": total_sent,
            "total_recipients": total_recipients,
            "delivery_rate": round((total_delivered / total_recipients * 100), 2) if total_recipients > 0 else 0,
            "read_rate": round((total_read / total_delivered * 100), 2) if total_delivered > 0 else 0,
            "notifications_by_type": self._get_type_breakdown(notifications),
            "notifications_by_priority": self._get_priority_breakdown(notifications)
        }
    
    async def _get_type_breakdown(self, notifications: List[Notification]) -> Dict[str, int]:
        """Get breakdown by notification type"""
        breakdown = {}
        for notification in notifications:
            type_name = notification.notification_type.value
            breakdown[type_name] = breakdown.get(type_name, 0) + 1
        return breakdown
    
    async def _get_priority_breakdown(self, notifications: List[Notification]) -> Dict[str, int]:
        """Get breakdown by priority"""
        breakdown = {}
        for notification in notifications:
            priority_name = notification.priority.value
            breakdown[priority_name] = breakdown.get(priority_name, 0) + 1
        return breakdown
    
    async def create_template(self, template_data: dict) -> NotificationTemplate:
        """Create notification template"""
        template = NotificationTemplate(**template_data)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template
    
    async def send_from_template(
        self,
        template_id: UUID,
        sender_id: UUID,
        sender_type: SenderType,
        variables: dict,
        recipient_config: dict
    ) -> Notification:
        """Send notification using template"""
        
        template = self.await db.execute(select(NotificationTemplate).filter(
            NotificationTemplate.id == template_id
        ).first()
        
        if not template:
            raise ValueError("Template not found")
        
        # Replace variables in template
        title = self._replace_variables(template.subject_template, variables)
        message = self._replace_variables(template.body_template, variables)
        
        # Create notification from template
        notification_data = {
            "tenant_id": template.tenant_id,
            "title": title,
            "message": message,
            "notification_type": template.notification_type,
            "priority": template.default_priority,
            "recipient_type": RecipientType.INDIVIDUAL,  # Override as needed
            "recipient_config": recipient_config,
            "delivery_channels": template.supported_channels or ["in_app"]
        }
        
        # Update template usage count
        template.usage_count += 1
        self.db.commit()
        
        return self.create_notification(sender_id, sender_type, notification_data)
    
    async def _replace_variables(self, template_text: str, variables: dict) -> str:
        """Replace variables in template text"""
        for key, value in variables.items():
            template_text = template_text.replace(f"{{{key}}}", str(value))
        return template_text
