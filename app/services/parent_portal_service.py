# from typing import List, Optional, Dict, Any
# from uuid import UUID
# from datetime import datetime, date, timedelta
# from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
# from sqlalchemy import and_, or_, func, desc
# from passlib.context import CryptContext
# import secrets
# from .base_service import BaseService
# from ..models.tenant_specific.parent_portal import (
#     Parent, StudentParent, ParentMessage, ParentNotification, 
#     ParentPortalSession, ParentFeedback, ParentEvent, ParentEventRegistration,
#     ParentRelationship, MessageStatus, MessageType, NotificationType
# )

# # Password hashing
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# class ParentPortalService(BaseService[Parent]):
#     async def __init__(self, db: Session):
#         super().__init__(Parent, db)
    
#     async def create_parent(self, parent_data: dict) -> Parent:
#         """Create a new parent account"""
        
#         # Hash password
#         if "password" in parent_data:
#             parent_data["password_hash"] = pwd_context.hash(parent_data.pop("password"))
        
#         # Generate unique parent_id if not provided
#         if not parent_data.get("parent_id"):
#             parent_data["parent_id"] = self._generate_parent_id()
        
#         # Generate username if not provided
#         if not parent_data.get("username"):
#             parent_data["username"] = self._generate_username(
#                 parent_data["first_name"], parent_data["last_name"]
#             )
        
#         parent = self.create(parent_data)
        
#         # Send welcome notification
#         self._send_welcome_notification(parent)
        
#         return parent
    
#     async def _generate_parent_id(self) -> str:
#         """Generate unique parent ID"""
#         timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#         return f"PAR{timestamp}"
    
#     async def _generate_username(self, first_name: str, last_name: str) -> str:
#         """Generate unique username"""
#         base_username = f"{first_name.lower()}.{last_name.lower()}"
#         counter = 1
#         username = base_username
        
#         while self.await db.execute(select(Parent).filter(Parent.username == username).first():
#             username = f"{base_username}{counter}"
#             counter += 1
        
#         return username
    
#     async def _send_welcome_notification(self, parent: Parent):
#         """Send welcome notification to new parent"""
#         notification = ParentNotification(
#             tenant_id=parent.tenant_id,
#             parent_id=parent.id,
#             notification_type=NotificationType.GENERAL,
#             title="Welcome to Parent Portal",
#             message=f"Dear {parent.first_name}, welcome to our school's parent portal. You can now access your child's information, communicate with teachers, and stay updated on school activities.",
#             sent_date=datetime.now(),
#             is_auto_generated=True
#         )
        
#         self.db.add(notification)
#         self.db.commit()
    
#     async def link_student_to_parent(
#         self,
#         student_id: UUID,
#         parent_id: UUID,
#         relationship: ParentRelationship,
#         permissions: Dict[str, bool] = None
#     ) -> StudentParent:
#         """Link a student to a parent"""
        
#         default_permissions = {
#             "can_view_grades": True,
#             "can_view_attendance": True,
#             "can_view_disciplinary": True,
#             "can_receive_communications": True,
#             "can_make_payments": False
#         }
        
#         if permissions:
#             default_permissions.update(permissions)
        
#         # Get parent to get tenant_id
#         parent = self.get(parent_id)
#         if not parent:
#             raise ValueError("Parent not found")
        
#         student_parent = StudentParent(
#             tenant_id=parent.tenant_id,
#             student_id=student_id,
#             parent_id=parent_id,
#             relationship=relationship,
#             **default_permissions
#         )
        
#         self.db.add(student_parent)
#         self.db.commit()
#         self.db.refresh(student_parent)
        
#         return student_parent
    
#     async def authenticate_parent(self, username: str, password: str) -> Optional[Parent]:
#         """Authenticate parent login"""
        
#         parent = self.await db.execute(select(Parent).filter(
#             Parent.username == username,
#             Parent.is_active == True,
#             Parent.is_deleted == False
#         ).first()
        
#         if not parent:
#             return None
        
#         # Check if account is locked
#         if parent.account_locked:
#             if parent.locked_until and datetime.now() < parent.locked_until:
#                 return None
#             else:
#                 # Unlock account
#                 parent.account_locked = False
#                 parent.locked_until = None
#                 parent.login_attempts = 0
        
#         # Verify password
#         if not pwd_context.verify(password, parent.password_hash):
#             # Increment login attempts
#             parent.login_attempts += 1
            
#             # Lock account after 5 failed attempts
#             if parent.login_attempts >= 5:
#                 parent.account_locked = True
#                 parent.locked_until = datetime.now() + timedelta(minutes=30)
            
#             self.db.commit()
#             return None
        
#         # Successful login - reset attempts and update last login
#         parent.login_attempts = 0
#         parent.last_login = datetime.now()
#         self.db.commit()
        
#         return parent
    
#     async def create_session(self, parent_id: UUID, session_data: dict) -> ParentPortalSession:
#         """Create a new portal session"""
        
#         parent = self.get(parent_id)
#         if not parent:
#             raise ValueError("Parent not found")
        
#         # Generate session token
#         session_token = secrets.token_urlsafe(32)
#         expires_at = datetime.now() + timedelta(hours=24)  # 24-hour session
        
#         session = ParentPortalSession(
#             tenant_id=parent.tenant_id,
#             parent_id=parent_id,
#             session_token=session_token,
#             login_time=datetime.now(),
#             expires_at=expires_at,
#             **session_data
#         )
        
#         self.db.add(session)
#         self.db.commit()
#         self.db.refresh(session)
        
#         return session
    
#     async def get_parent_children(self, parent_id: UUID) -> List[Dict[str, Any]]:
#         """Get all children linked to a parent"""
        
#         student_parents = self.await db.execute(select(StudentParent).filter(
#             StudentParent.parent_id == parent_id,
#             StudentParent.is_active == True,
#             StudentParent.is_deleted == False
#         ).all()
        
#         children = []
#         for sp in student_parents:
#             child_info = {
#                 "student_id": str(sp.student_id),
#                 "student_name": f"{sp.student.first_name} {sp.student.last_name}",
#                 "grade_level": sp.student.grade_level,
#                 "section": sp.student.section,
#                 "class_name": sp.student.enrollment_details.get("class_name") if sp.student.enrollment_details else None,
#                 "relationship": sp.relationship.value,
#                 "is_primary_contact": sp.is_primary_contact,
#                 "permissions": {
#                     "can_view_grades": sp.can_view_grades,
#                     "can_view_attendance": sp.can_view_attendance,
#                     "can_view_disciplinary": sp.can_view_disciplinary,
#                     "can_receive_communications": sp.can_receive_communications,
#                     "can_make_payments": sp.can_make_payments
#                 }
#             }
#             children.append(child_info)
        
#         return children
    
#     async def send_message_to_parent(
#         self,
#         parent_id: UUID,
#         sender_id: UUID,
#         sender_type: str,
#         message_data: dict
#     ) -> ParentMessage:
#         """Send message to parent"""
        
#         parent = self.get(parent_id)
#         if not parent:
#             raise ValueError("Parent not found")
        
#         message = ParentMessage(
#             tenant_id=parent.tenant_id,
#             parent_id=parent_id,
#             sender_id=sender_id,
#             sender_type=sender_type,
#             sent_date=datetime.now(),
#             **message_data
#         )
        
#         self.db.add(message)
#         self.db.commit()
#         self.db.refresh(message)
        
#         # Create notification
#         self._create_message_notification(message)
        
#         return message
    
#     async def _create_message_notification(self, message: ParentMessage):
#         """Create notification for new message"""
#         notification = ParentNotification(
#             tenant_id=message.tenant_id,
#             parent_id=message.parent_id,
#             student_id=message.student_id,
#             notification_type=NotificationType.GENERAL,
#             title=f"New Message: {message.subject}",
#             message=f"You have received a new message from {message.sender_type}",
#             reference_type="message",
#             reference_id=message.id,
#             sent_date=datetime.now(),
#             is_auto_generated=True
#         )
        
#         self.db.add(notification)
#         self.db.commit()
    
#     async def get_parent_messages(
#         self,
#         parent_id: UUID,
#         message_type: Optional[MessageType] = None,
#         unread_only: bool = False
#     ) -> List[ParentMessage]:
#         """Get messages for a parent"""
        
#         query = self.await db.execute(select(ParentMessage).filter(
#             ParentMessage.parent_id == parent_id,
#             ParentMessage.is_deleted == False
#         )
        
#         if message_type:
#             query = query.filter(ParentMessage.message_type == message_type)
        
#         if unread_only:
#             query = query.filter(ParentMessage.read_date.is_(None))
        
#         return query.order_by(desc(ParentMessage.sent_date)).all()
    
#     async def mark_message_as_read(self, message_id: UUID) -> ParentMessage:
#         """Mark message as read"""
        
#         message = self.await db.execute(select(ParentMessage).filter(
#             ParentMessage.id == message_id
#         ).first()
        
#         if message:
#             message.status = MessageStatus.READ
#             message.read_date = datetime.now()
#             self.db.commit()
        
#         return message
    
#     async def create_notification(self, notification_data: dict) -> ParentNotification:
#         """Create a notification for parent"""
        
#         notification = ParentNotification(
#             sent_date=datetime.now(),
#             **notification_data
#         )
        
#         self.db.add(notification)
#         self.db.commit()
#         self.db.refresh(notification)
        
#         return notification
    
#     async def get_parent_notifications(
#         self,
#         parent_id: UUID,
#         notification_type: Optional[NotificationType] = None,
#         unread_only: bool = False,
#         limit: int = 50
#     ) -> List[ParentNotification]:
#         """Get notifications for a parent"""
        
#         query = self.await db.execute(select(ParentNotification).filter(
#             ParentNotification.parent_id == parent_id,
#             ParentNotification.is_archived == False,
#             ParentNotification.is_deleted == False
#         )
        
#         if notification_type:
#             query = query.filter(ParentNotification.notification_type == notification_type)
        
#         if unread_only:
#             query = query.filter(ParentNotification.is_read == False)
        
#         return query.order_by(desc(ParentNotification.sent_date)).limit(limit).all()
    
#     async def submit_feedback(
#         self,
#         parent_id: UUID,
#         feedback_data: dict
#     ) -> ParentFeedback:
#         """Submit feedback from parent"""
        
#         parent = self.get(parent_id)
#         if not parent:
#             raise ValueError("Parent not found")
        
#         feedback = ParentFeedback(
#             tenant_id=parent.tenant_id,
#             parent_id=parent_id,
#             **feedback_data
#         )
        
#         self.db.add(feedback)
#         self.db.commit()
#         self.db.refresh(feedback)
        
#         return feedback
    
#     async def create_event(self, event_data: dict) -> ParentEvent:
#         """Create a parent event"""
        
#         event = ParentEvent(**event_data)
#         self.db.add(event)
#         self.db.commit()
#         self.db.refresh(event)
        
#         return event
    
#     async def register_for_event(
#         self,
#         event_id: UUID,
#         parent_id: UUID,
#         registration_data: dict
#     ) -> ParentEventRegistration:
#         """Register parent for an event"""
        
#         event = self.await db.execute(select(ParentEvent).filter(ParentEvent.id == event_id).first()
#         if not event:
#             raise ValueError("Event not found")
        
#         parent = self.get(parent_id)
#         if not parent:
#             raise ValueError("Parent not found")
        
#         # Check if registration is still open
#         if event.registration_deadline and datetime.now() > event.registration_deadline:
#             raise ValueError("Registration deadline has passed")
        
#         # Check capacity
#         if event.max_participants and event.current_participants >= event.max_participants:
#             raise ValueError("Event is at full capacity")
        
#         registration = ParentEventRegistration(
#             tenant_id=parent.tenant_id,
#             event_id=event_id,
#             parent_id=parent_id,
#             registration_date=datetime.now(),
#             **registration_data
#         )
        
#         self.db.add(registration)
        
#         # Update participant count
#         event.current_participants += registration_data.get("number_of_attendees", 1)
        
#         self.db.commit()
#         self.db.refresh(registration)
        
#         return registration
    
#     async def get_child_attendance_summary(
#         self,
#         parent_id: UUID,
#         student_id: UUID,
#         start_date: Optional[date] = None,
#         end_date: Optional[date] = None
#     ) -> Dict[str, Any]:
#         """Get attendance summary for parent's child"""
        
#         # Verify parent can access this student's data
#         student_parent = self.await db.execute(select(StudentParent).filter(
#             StudentParent.parent_id == parent_id,
#             StudentParent.student_id == student_id,
#             StudentParent.can_view_attendance == True
#         ).first()
        
#         if not student_parent:
#             raise ValueError("Access denied or invalid student")
        
#         # Get attendance data
#         from ..services.attendance_service import AttendanceService
#         attendance_service = AttendanceService(self.db)
        
#         return attendance_service.get_attendance_statistics(
#             student_id=student_id,
#             start_date=start_date,
#             end_date=end_date
#         )
    
#     async def get_child_grades(
#         self,
#         parent_id: UUID,
#         student_id: UUID,
#         academic_year: Optional[str] = None
#     ) -> List[Dict[str, Any]]:
#         """Get grades for parent's child"""
        
#         # Verify parent can access this student's data
#         student_parent = self.await db.execute(select(StudentParent).filter(
#             StudentParent.parent_id == parent_id,
#             StudentParent.student_id == student_id,
#             StudentParent.can_view_grades == True
#         ).first()
        
#         if not student_parent:
#             raise ValueError("Access denied or invalid student")
        
#         # Get grades data
#         from ..services.grades_service import GradesService
#         grades_service = GradesService(self.db)
        
#         grades = grades_service.get_student_grades(
#             student_id=student_id,
#             academic_year=academic_year
#         )
        
#         # Convert to parent-friendly format
#         grade_data = []
#         for grade in grades:
#             grade_info = {
#                 "subject_name": grade.class_subject.subject.subject_name,
#                 "subject_code": grade.class_subject.subject.subject_code,
#                 "teacher_name": f"{grade.class_subject.teacher.personal_info.get('basic_details', {}).get('first_name', '')} {grade.class_subject.teacher.personal_info.get('basic_details', {}).get('last_name', '')}",
#                 "percentage": float(grade.percentage) if grade.percentage else None,
#                 "letter_grade": grade.letter_grade,
#                 "gpa": float(grade.gpa) if grade.gpa else None,
#                 "component_grades": grade.component_grades,
#                 "teacher_comments": grade.teacher_comments,
#                 "last_updated": grade.last_updated.isoformat() if grade.last_updated else None
#             }
#             grade_data.append(grade_info)
        
#         return grade_data
