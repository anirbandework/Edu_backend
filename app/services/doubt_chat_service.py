from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import and_, or_, func, desc
import secrets
from .base_service import BaseService
from ..models.tenant_specific.doubt_chat import (
    ChatRoom, ChatParticipant, ChatMessage, MessageReaction, 
    ChatSession, DoubtCategory, ChatAnalytics, TeacherAvailability,
    ChatStatus, MessageType, MessageStatus, ParticipantRole
)

class DoubtChatService(BaseService[ChatRoom]):
    async def __init__(self, db: Session):
        super().__init__(ChatRoom, db)
    
    async def get_available_teachers_for_subject(
        self,
        student_id: UUID,
        subject_id: UUID,
        tenant_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get available teachers for a specific subject that can help the student"""
        
        # Get student's class to find assigned teachers
        from ..models.tenant_specific.student import Student
        from ..models.tenant_specific.grades_assessment import ClassSubject
        from ..models.tenant_specific.teacher import Teacher
        
        student = self.await db.execute(select(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError("Student not found")
        
        # Get teachers assigned to teach this subject to student's class or grade
        query = self.await db.execute(select(Teacher, ClassSubject, TeacherAvailability).join(
            ClassSubject, Teacher.id == ClassSubject.teacher_id
        ).outerjoin(
            TeacherAvailability, and_(
                TeacherAvailability.teacher_id == Teacher.id,
                TeacherAvailability.subject_id == subject_id
            )
        ).filter(
            ClassSubject.subject_id == subject_id,
            Teacher.tenant_id == tenant_id,
            Teacher.status == "active",
            Teacher.is_deleted == False,
            or_(
                ClassSubject.class_id == student.class_id,
                ClassSubject.class_id.is_(None)  # Teachers available for all classes
            )
        )
        
        current_day = datetime.now().strftime('%A').lower()
        current_time = datetime.now().strftime('%H:%M:%S')
        
        available_teachers = []
        for teacher, class_subject, availability in query.all():
            # Check if teacher is currently available
            is_available = True
            if availability:
                is_available = (
                    availability.is_available and
                    availability.day_of_week == current_day and
                    availability.start_time <= current_time <= availability.end_time and
                    availability.current_active_chats < availability.max_concurrent_chats
                )
            
            teacher_info = {
                "teacher_id": str(teacher.id),
                "teacher_name": f"{teacher.personal_info.get('basic_details', {}).get('first_name', '')} {teacher.personal_info.get('basic_details', {}).get('last_name', '')}",
                "email": teacher.personal_info.get('contact_info', {}).get('primary_email', ''),
                "department": teacher.employment.get('job_information', {}).get('department', ''),
                "experience_years": teacher.qualifications.get('professional_experience', {}).get('total_years', 0),
                "specializations": teacher.academic_responsibilities.get('specializations', []),
                "is_currently_available": is_available,
                "max_concurrent_chats": availability.max_concurrent_chats if availability else 3,
                "current_active_chats": availability.current_active_chats if availability else 0,
                "response_time_commitment": availability.response_time_commitment if availability else "within_hour",
                "auto_accept_chats": availability.auto_accept_chats if availability else False
            }
            available_teachers.append(teacher_info)
        
        return available_teachers
    
    async def create_chat_room(
        self,
        student_id: UUID,
        teacher_id: UUID,
        subject_id: UUID,
        chat_data: dict
    ) -> ChatRoom:
        """Create a new doubt chat room"""
        
        # Generate unique room code
        room_code = self._generate_room_code()
        
        # Auto-generate room name if not provided
        if not chat_data.get("room_name"):
            from ..models.tenant_specific.student import Student
            from ..models.tenant_specific.teacher import Teacher
            from ..models.tenant_specific.grades_assessment import Subject
            
            student = self.await db.execute(select(Student).filter(Student.id == student_id).first()
            teacher = self.await db.execute(select(Teacher).filter(Teacher.id == teacher_id).first()
            subject = self.await db.execute(select(Subject).filter(Subject.id == subject_id).first()
            
            chat_data["room_name"] = f"{student.first_name} - {teacher.personal_info.get('basic_details', {}).get('first_name', 'Teacher')} ({subject.subject_name})"
        
        # Create chat room
        chat_room = ChatRoom(
            student_id=student_id,
            teacher_id=teacher_id,
            subject_id=subject_id,
            room_code=room_code,
            started_at=datetime.now(),
            last_activity_at=datetime.now(),
            **chat_data
        )
        
        self.db.add(chat_room)
        self.db.flush()  # Get the ID
        
        # Add participants
        self._add_participants(chat_room)
        
        # Update teacher's active chat count
        self._update_teacher_active_chats(teacher_id, subject_id, 1)
        
        self.db.commit()
        self.db.refresh(chat_room)
        
        # Send welcome system message
        self._send_welcome_message(chat_room)
        
        return chat_room
    
    async def _generate_room_code(self) -> str:
        """Generate unique room code"""
        while True:
            code = f"CHAT{secrets.token_hex(4).upper()}"
            if not self.await db.execute(select(ChatRoom).filter(ChatRoom.room_code == code).first():
                return code
    
    async def _add_participants(self, chat_room: ChatRoom):
        """Add student and teacher as participants"""
        from ..models.tenant_specific.student import Student
        from ..models.tenant_specific.teacher import Teacher
        
        # Get participant details
        student = self.await db.execute(select(Student).filter(Student.id == chat_room.student_id).first()
        teacher = self.await db.execute(select(Teacher).filter(Teacher.id == chat_room.teacher_id).first()
        
        # Add student participant
        student_participant = ChatParticipant(
            tenant_id=chat_room.tenant_id,
            chat_room_id=chat_room.id,
            participant_id=chat_room.student_id,
            participant_role=ParticipantRole.STUDENT,
            participant_name=f"{student.first_name} {student.last_name}",
            joined_at=datetime.now(),
            is_active=True
        )
        self.db.add(student_participant)
        
        # Add teacher participant
        teacher_participant = ChatParticipant(
            tenant_id=chat_room.tenant_id,
            chat_room_id=chat_room.id,
            participant_id=chat_room.teacher_id,
            participant_role=ParticipantRole.TEACHER,
            participant_name=f"{teacher.personal_info.get('basic_details', {}).get('first_name', '')} {teacher.personal_info.get('basic_details', {}).get('last_name', '')}",
            joined_at=datetime.now(),
            is_active=True
        )
        self.db.add(teacher_participant)
    
    async def _update_teacher_active_chats(self, teacher_id: UUID, subject_id: UUID, increment: int):
        """Update teacher's active chat count"""
        availability = self.await db.execute(select(TeacherAvailability).filter(
            TeacherAvailability.teacher_id == teacher_id,
            TeacherAvailability.subject_id == subject_id
        ).first()
        
        if availability:
            availability.current_active_chats = max(0, availability.current_active_chats + increment)
            self.db.commit()
    
    async def _send_welcome_message(self, chat_room: ChatRoom):
        """Send welcome system message"""
        welcome_message = ChatMessage(
            tenant_id=chat_room.tenant_id,
            chat_room_id=chat_room.id,
            sender_id=chat_room.teacher_id,  # System message from teacher's perspective
            sender_role=ParticipantRole.TEACHER,
            sender_name="System",
            message_type=MessageType.TEXT,
            content=f"Welcome to the doubt chat! Feel free to ask your questions about {chat_room.topic or 'the subject'}. I'm here to help you understand the concepts better.",
            message_sequence=1,
            sent_at=datetime.now(),
            is_system_message=True
        )
        
        self.db.add(welcome_message)
        
        # Update chat room message count
        chat_room.total_messages += 1
        self.db.commit()
    
    async def send_message(
        self,
        chat_room_id: UUID,
        sender_id: UUID,
        sender_role: ParticipantRole,
        message_data: dict
    ) -> ChatMessage:
        """Send a message in the chat room"""
        
        chat_room = self.get(chat_room_id)
        if not chat_room:
            raise ValueError("Chat room not found")
        
        if chat_room.status != ChatStatus.ACTIVE:
            raise ValueError("Chat room is not active")
        
        # Verify sender is a participant
        participant = self.await db.execute(select(ChatParticipant).filter(
            ChatParticipant.chat_room_id == chat_room_id,
            ChatParticipant.participant_id == sender_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise ValueError("Sender is not a participant in this chat")
        
        # Get next sequence number
        last_sequence = self.await db.execute(select(func.max(ChatMessage.message_sequence)).filter(
            ChatMessage.chat_room_id == chat_room_id
        ).scalar() or 0
        
        # Create message
        message = ChatMessage(
            tenant_id=chat_room.tenant_id,
            chat_room_id=chat_room_id,
            sender_id=sender_id,
            sender_role=sender_role,
            sender_name=participant.participant_name,
            message_sequence=last_sequence + 1,
            sent_at=datetime.now(),
            **message_data
        )
        
        self.db.add(message)
        
        # Update chat room and participant statistics
        chat_room.total_messages += 1
        chat_room.last_activity_at = datetime.now()
        
        participant.messages_sent += 1
        participant.last_seen_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(message)
        
        # Mark message as delivered to other participants (simplified)
        self._mark_message_delivered(message)
        
        return message
    
    async def _mark_message_delivered(self, message: ChatMessage):
        """Mark message as delivered to other participants"""
        # In a real implementation, this would handle WebSocket delivery
        message.status = MessageStatus.DELIVERED
        message.delivered_at = datetime.now()
        self.db.commit()
    
    async def get_chat_history(
        self,
        chat_room_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        before_message_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get chat history for a user"""
        
        # Verify user is a participant
        participant = self.await db.execute(select(ChatParticipant).filter(
            ChatParticipant.chat_room_id == chat_room_id,
            ChatParticipant.participant_id == user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise ValueError("User is not a participant in this chat")
        
        query = self.await db.execute(select(ChatMessage).filter(
            ChatMessage.chat_room_id == chat_room_id,
            ChatMessage.is_deleted == False
        )
        
        if before_message_id:
            # For pagination - get messages before a specific message
            before_message = self.await db.execute(select(ChatMessage).filter(
                ChatMessage.id == before_message_id
            ).first()
            if before_message:
                query = query.filter(ChatMessage.message_sequence < before_message.message_sequence)
        
        messages = query.order_by(desc(ChatMessage.message_sequence)).offset(offset).limit(limit).all()
        
        # Convert to response format
        chat_history = []
        for message in reversed(messages):  # Reverse to get chronological order
            message_data = {
                "id": str(message.id),
                "sender_id": str(message.sender_id),
                "sender_name": message.sender_name,
                "sender_role": message.sender_role.value,
                "message_type": message.message_type.value,
                "content": message.content,
                "sent_at": message.sent_at.isoformat(),
                "message_sequence": message.message_sequence,
                "is_reply": message.is_reply,
                "reply_to_message_id": str(message.reply_to_message_id) if message.reply_to_message_id else None,
                "is_edited": message.is_edited,
                "edited_at": message.edited_at.isoformat() if message.edited_at else None,
                "is_system_message": message.is_system_message,
                "is_important": message.is_important,
                "is_pinned": message.is_pinned,
                "file_metadata": message.file_metadata,
                "attachments": message.attachments,
                "related_topic": message.related_topic,
                "status": message.status.value,
                "delivered_at": message.delivered_at.isoformat() if message.delivered_at else None,
                "read_at": message.read_at.isoformat() if message.read_at else None,
                "reactions": self._get_message_reactions(message.id)
            }
            chat_history.append(message_data)
        
        # Update participant's last read time
        participant.last_message_read_at = datetime.now()
        self.db.commit()
        
        return chat_history
    
    async def _get_message_reactions(self, message_id: UUID) -> List[Dict[str, Any]]:
        """Get reactions for a message"""
        reactions = self.await db.execute(select(MessageReaction).filter(
            MessageReaction.message_id == message_id
        ).all()
        
        return [
            {
                "reaction_type": reaction.reaction_type,
                "reaction_emoji": reaction.reaction_emoji,
                "user_name": reaction.user_name,
                "user_role": reaction.user_role.value,
                "reacted_at": reaction.reacted_at.isoformat()
            }
            for reaction in reactions
        ]
    
    async def get_student_chat_rooms(
        self,
        student_id: UUID,
        status: Optional[ChatStatus] = None,
        subject_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get all chat rooms for a student"""
        
        query = self.await db.execute(select(ChatRoom).filter(
            ChatRoom.student_id == student_id,
            ChatRoom.is_deleted == False
        )
        
        if status:
            query = query.filter(ChatRoom.status == status)
        
        if subject_id:
            query = query.filter(ChatRoom.subject_id == subject_id)
        
        chat_rooms = query.order_by(desc(ChatRoom.last_activity_at)).all()
        
        result = []
        for room in chat_rooms:
            # Get last message
            last_message = self.await db.execute(select(ChatMessage).filter(
                ChatMessage.chat_room_id == room.id,
                ChatMessage.is_deleted == False
            ).order_by(desc(ChatMessage.sent_at)).first()
            
            # Get unread message count
            participant = self.await db.execute(select(ChatParticipant).filter(
                ChatParticipant.chat_room_id == room.id,
                ChatParticipant.participant_id == student_id
            ).first()
            
            unread_count = 0
            if participant and participant.last_message_read_at:
                unread_count = self.await db.execute(select(ChatMessage).filter(
                    ChatMessage.chat_room_id == room.id,
                    ChatMessage.sent_at > participant.last_message_read_at,
                    ChatMessage.sender_id != student_id,
                    ChatMessage.is_deleted == False
                ).count()
            else:
                unread_count = self.await db.execute(select(ChatMessage).filter(
                    ChatMessage.chat_room_id == room.id,
                    ChatMessage.sender_id != student_id,
                    ChatMessage.is_deleted == False
                ).count()
            
            room_data = {
                "id": str(room.id),
                "room_name": room.room_name,
                "room_code": room.room_code,
                "topic": room.topic,
                "subject_name": room.subject.subject_name,
                "subject_code": room.subject.subject_code,
                "teacher_name": f"{room.teacher.personal_info.get('basic_details', {}).get('first_name', '')} {room.teacher.personal_info.get('basic_details', {}).get('last_name', '')}",
                "status": room.status.value,
                "urgency_level": room.urgency_level,
                "started_at": room.started_at.isoformat(),
                "last_activity_at": room.last_activity_at.isoformat(),
                "total_messages": room.total_messages,
                "unread_count": unread_count,
                "is_resolved": room.is_resolved,
                "last_message": {
                    "content": last_message.content[:100] + "..." if last_message and len(last_message.content) > 100 else last_message.content if last_message else None,
                    "sender_name": last_message.sender_name if last_message else None,
                    "sent_at": last_message.sent_at.isoformat() if last_message else None
                } if last_message else None
            }
            result.append(room_data)
        
        return result
    
    async def close_chat_room(
        self,
        chat_room_id: UUID,
        closed_by: UUID,
        resolution_data: Optional[dict] = None
    ) -> ChatRoom:
        """Close a chat room and mark as resolved"""
        
        chat_room = self.get(chat_room_id)
        if not chat_room:
            raise ValueError("Chat room not found")
        
        chat_room.status = ChatStatus.CLOSED
        chat_room.closed_at = datetime.now()
        
        if resolution_data:
            chat_room.is_resolved = resolution_data.get("is_resolved", True)
            chat_room.resolved_at = datetime.now()
            chat_room.resolution_summary = resolution_data.get("resolution_summary")
            chat_room.student_feedback = resolution_data.get("student_feedback")
            chat_room.teacher_feedback = resolution_data.get("teacher_feedback")
        
        # Calculate total duration
        duration = datetime.now() - chat_room.started_at
        chat_room.duration_minutes = int(duration.total_seconds() / 60)
        
        # Update teacher's active chat count
        self._update_teacher_active_chats(chat_room.teacher_id, chat_room.subject_id, -1)
        
        self.db.commit()
        self.db.refresh(chat_room)
    
        return chat_room