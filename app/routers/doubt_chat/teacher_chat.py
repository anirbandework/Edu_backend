from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db
from ..core.cache import cache_manager
from ..core.cache_decorators import cache_response, invalidate_cache_pattern

from ...core.database import get_db
from ...services.doubt_chat_service import DoubtChatService
from ...models.tenant_specific.doubt_chat import (
    ChatStatus, MessageType, ParticipantRole, TeacherAvailability, 
    ChatParticipant, ChatMessage
)

router = APIRouter(prefix="/api/v1/teacher/chat", tags=["Teacher - Doubt Chat"])

@router.get("/rooms", response_model=dict)
async async def get_teacher_chat_rooms(
    teacher_id: UUID,  # In real app, get from authenticated session
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[ChatStatus] = Query(None),
    subject_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated chat rooms for a teacher"""
    service = DoubtChatService(db)
    
    try:
        filters = {"teacher_id": teacher_id}
        if status:
            filters["status"] = status
        if subject_id:
            filters["subject_id"] = subject_id
        
        result = service.get_paginated(page=page, size=size, **filters)
        
        formatted_rooms = []
        for room in result["items"]:
            # Get last message
            last_message = service.db.query(ChatMessage).filter(
                ChatMessage.chat_room_id == room.id,
                ChatMessage.is_deleted == False
            ).order_by(ChatMessage.sent_at.desc()).first()
            
            # Get unread count for teacher
            teacher_participant = service.db.query(ChatParticipant).filter(
                ChatParticipant.chat_room_id == room.id,
                ChatParticipant.participant_id == teacher_id
            ).first()
            
            unread_count = 0
            if teacher_participant and teacher_participant.last_message_read_at:
                unread_count = service.db.query(ChatMessage).filter(
                    ChatMessage.chat_room_id == room.id,
                    ChatMessage.sent_at > teacher_participant.last_message_read_at,
                    ChatMessage.sender_id != teacher_id,
                    ChatMessage.is_deleted == False
                ).count()
            else:
                unread_count = service.db.query(ChatMessage).filter(
                    ChatMessage.chat_room_id == room.id,
                    ChatMessage.sender_id != teacher_id,
                    ChatMessage.is_deleted == False
                ).count()
            
            room_data = {
                "id": str(room.id),
                "room_name": room.room_name,
                "room_code": room.room_code,
                "topic": room.topic,
                "description": room.description,
                "subject_name": room.subject.subject_name,
                "student_name": f"{room.student.first_name} {room.student.last_name}",
                "student_grade": room.student.grade_level,
                "student_section": room.student.section,
                "status": room.status.value,
                "urgency_level": room.urgency_level,
                "started_at": room.started_at.isoformat(),
                "last_activity_at": room.last_activity_at.isoformat(),
                "total_messages": room.total_messages,
                "unread_count": unread_count,
                "is_resolved": room.is_resolved,
                "chapter": room.chapter,
                "lesson": room.lesson,
                "last_message": {
                    "content": last_message.content[:100] + "..." if last_message and len(last_message.content) > 100 else last_message.content if last_message else None,
                    "sender_name": last_message.sender_name if last_message else None,
                    "sent_at": last_message.sent_at.isoformat() if last_message else None
                } if last_message else None
            }
            formatted_rooms.append(room_data)
        
        return {
            "items": formatted_rooms,
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "has_next": result["has_next"],
            "has_previous": result["has_previous"],
            "total_pages": result["total_pages"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rooms/{room_id}/messages", response_model=List[dict])
async async def get_teacher_chat_history(
    room_id: UUID,
    teacher_id: UUID,  # In real app, get from authenticated session
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    before_message_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for teacher"""
    service = DoubtChatService(db)
    
    try:
        messages = service.get_chat_history(
            chat_room_id=room_id,
            user_id=teacher_id,
            limit=limit,
            offset=offset,
            before_message_id=before_message_id
        )
        return messages
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rooms/{room_id}/messages", response_model=dict)
async async def send_teacher_message(
    room_id: UUID,
    message_data: dict,
    teacher_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Send a message as teacher"""
    service = DoubtChatService(db)
    
    try:
        message = service.send_message(
            chat_room_id=room_id,
            sender_id=teacher_id,
            sender_role=ParticipantRole.TEACHER,
            message_data=message_data
        )
        
        return {
            "id": str(message.id),
            "message": "Message sent successfully",
            "content": message.content,
            "message_type": message.message_type.value,
            "sent_at": message.sent_at.isoformat(),
            "message_sequence": message.message_sequence
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/availability", response_model=dict)
async async def update_teacher_availability(
    availability_data: dict,
    teacher_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Update teacher availability for chat sessions"""
    service = DoubtChatService(db)
    
    try:
        # Update or create availability record
        availability = service.db.query(TeacherAvailability).filter(
            TeacherAvailability.teacher_id == teacher_id,
            TeacherAvailability.subject_id == UUID(availability_data["subject_id"]),
            TeacherAvailability.day_of_week == availability_data["day_of_week"]
        ).first()
        
        if availability:
            # Update existing
            for key, value in availability_data.items():
                if hasattr(availability, key) and key not in ["teacher_id"]:
                    setattr(availability, key, value)
        else:
            # Create new
            availability = TeacherAvailability(
                teacher_id=teacher_id,
                **availability_data
            )
            service.db.add(availability)
        
        service.db.commit()
        service.db.refresh(availability)
        
        return {
            "message": "Availability updated successfully",
            "day_of_week": availability.day_of_week,
            "start_time": availability.start_time,
            "end_time": availability.end_time,
            "max_concurrent_chats": availability.max_concurrent_chats,
            "is_available": availability.is_available
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/availability", response_model=List[dict])
async async def get_teacher_availability(
    teacher_id: UUID,  # In real app, get from authenticated session
    subject_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get teacher availability schedule"""
    service = DoubtChatService(db)
    
    try:
        query = service.db.query(TeacherAvailability).filter(
            TeacherAvailability.teacher_id == teacher_id
        )
        
        if subject_id:
            query = query.filter(TeacherAvailability.subject_id == subject_id)
        
        availabilities = query.all()
        
        return [
            {
                "id": str(avail.id),
                "subject_id": str(avail.subject_id),
                "subject_name": avail.subject.subject_name,
                "day_of_week": avail.day_of_week,
                "start_time": avail.start_time,
                "end_time": avail.end_time,
                "max_concurrent_chats": avail.max_concurrent_chats,
                "current_active_chats": avail.current_active_chats,
                "is_available": avail.is_available,
                "auto_accept_chats": avail.auto_accept_chats,
                "response_time_commitment": avail.response_time_commitment,
                "applicable_grades": avail.applicable_grades,
                "preferred_topics": avail.preferred_topics
            }
            for avail in availabilities
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analytics", response_model=dict)
async async def get_teacher_chat_analytics(
    teacher_id: UUID,  # In real app, get from authenticated session
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics for teacher's chat sessions"""
    service = DoubtChatService(db)
    
    try:
        # Basic analytics query
        query = service.db.query(service.model).filter(
            service.model.teacher_id == teacher_id,
            service.model.is_deleted == False
        )
        
        if start_date:
            query = query.filter(service.model.started_at >= datetime.fromisoformat(start_date))
        
        if end_date:
            query = query.filter(service.model.started_at <= datetime.fromisoformat(end_date))
        
        chat_rooms = query.all()
        
        total_chats = len(chat_rooms)
        resolved_chats = len([room for room in chat_rooms if room.is_resolved])
        active_chats = len([room for room in chat_rooms if room.status == ChatStatus.ACTIVE])
        
        # Calculate average duration and response times
        completed_chats = [room for room in chat_rooms if room.duration_minutes > 0]
        avg_duration = sum(room.duration_minutes for room in completed_chats) / len(completed_chats) if completed_chats else 0
        
        # Subject-wise breakdown
        subject_stats = {}
        for room in chat_rooms:
            subject_name = room.subject.subject_name
            if subject_name not in subject_stats:
                subject_stats[subject_name] = {
                    "total_chats": 0,
                    "resolved_chats": 0,
                    "total_messages": 0
                }
            subject_stats[subject_name]["total_chats"] += 1
            if room.is_resolved:
                subject_stats[subject_name]["resolved_chats"] += 1
            subject_stats[subject_name]["total_messages"] += room.total_messages
        
        return {
            "total_chats": total_chats,
            "active_chats": active_chats,
            "resolved_chats": resolved_chats,
            "resolution_rate": round((resolved_chats / total_chats * 100), 2) if total_chats > 0 else 0,
            "average_duration_minutes": round(avg_duration, 2),
            "total_messages_sent": sum(room.total_messages for room in chat_rooms),
            "subject_breakdown": subject_stats,
            "urgency_breakdown": {
                urgency: len([room for room in chat_rooms if room.urgency_level == urgency])
                for urgency in ["low", "normal", "high", "urgent"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rooms/{room_id}/resolve", response_model=dict)
async async def mark_chat_resolved(
    room_id: UUID,
    resolution_data: dict,
    teacher_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Mark chat as resolved by teacher"""
    service = DoubtChatService(db)
    
    try:
        chat_room = service.close_chat_room(
            chat_room_id=room_id,
            closed_by=teacher_id,
            resolution_data=resolution_data
        )
        
        return {
            "id": str(chat_room.id),
            "message": "Chat marked as resolved",
            "status": chat_room.status.value,
            "is_resolved": chat_room.is_resolved,
            "resolved_at": chat_room.resolved_at.isoformat() if chat_room.resolved_at else None,
            "resolution_summary": chat_room.resolution_summary
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rooms/{room_id}", response_model=dict)
async async def get_teacher_chat_room_details(
    room_id: UUID,
    teacher_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a chat room for teacher"""
    service = DoubtChatService(db)
    
    try:
        chat_room = service.get(room_id)
        if not chat_room:
            raise HTTPException(status_code=404, detail="Chat room not found")
        
        # Verify teacher is the assigned teacher
        if chat_room.teacher_id != teacher_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get student information
        student_info = {
            "id": str(chat_room.student.id),
            "name": f"{chat_room.student.first_name} {chat_room.student.last_name}",
            "grade": chat_room.student.grade_level,
            "section": chat_room.student.section,
            "roll_number": chat_room.student.roll_number,
            "email": chat_room.student.email
        }
        
        # Get message statistics
        total_student_messages = service.db.query(ChatMessage).filter(
            ChatMessage.chat_room_id == room_id,
            ChatMessage.sender_role == ParticipantRole.STUDENT,
            ChatMessage.is_deleted == False
        ).count()
        
        total_teacher_messages = service.db.query(ChatMessage).filter(
            ChatMessage.chat_room_id == room_id,
            ChatMessage.sender_role == ParticipantRole.TEACHER,
            ChatMessage.is_deleted == False
        ).count()
        
        return {
            "id": str(chat_room.id),
            "room_name": chat_room.room_name,
            "room_code": chat_room.room_code,
            "topic": chat_room.topic,
            "description": chat_room.description,
            "urgency_level": chat_room.urgency_level,
            "status": chat_room.status.value,
            "subject": {
                "id": str(chat_room.subject.id),
                "name": chat_room.subject.subject_name,
                "code": chat_room.subject.subject_code
            },
            "student": student_info,
            "started_at": chat_room.started_at.isoformat(),
            "last_activity_at": chat_room.last_activity_at.isoformat(),
            "total_messages": chat_room.total_messages,
            "student_messages": total_student_messages,
            "teacher_messages": total_teacher_messages,
            "is_resolved": chat_room.is_resolved,
            "resolved_at": chat_room.resolved_at.isoformat() if chat_room.resolved_at else None,
            "resolution_summary": chat_room.resolution_summary,
            "academic_year": chat_room.academic_year,
            "chapter": chat_room.chapter,
            "lesson": chat_room.lesson,
            "duration_minutes": chat_room.duration_minutes,
            "closed_at": chat_room.closed_at.isoformat() if chat_room.closed_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rooms/{room_id}/messages/{message_id}/reaction", response_model=dict)
async async def add_teacher_message_reaction(
    room_id: UUID,
    message_id: UUID,
    reaction_data: dict,
    teacher_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Add reaction to a message as teacher"""
    try:
        from ...models.tenant_specific.doubt_chat import MessageReaction
        from ...models.tenant_specific.teacher import Teacher
        
        # Verify teacher is participant
        service = DoubtChatService(db)
        participant = service.db.query(ChatParticipant).filter(
            ChatParticipant.chat_room_id == room_id,
            ChatParticipant.participant_id == teacher_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get teacher info
        teacher = service.db.query(Teacher).filter(Teacher.id == teacher_id).first()
        teacher_name = f"{teacher.personal_info.get('basic_details', {}).get('first_name', '')} {teacher.personal_info.get('basic_details', {}).get('last_name', '')}"
        
        # Check if reaction already exists
        existing_reaction = service.db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == teacher_id,
            MessageReaction.reaction_type == reaction_data["reaction_type"]
        ).first()
        
        if existing_reaction:
            # Remove existing reaction
            service.db.delete(existing_reaction)
            service.db.commit()
            return {"message": "Reaction removed"}
        
        # Add new reaction
        reaction = MessageReaction(
            tenant_id=participant.tenant_id,
            message_id=message_id,
            user_id=teacher_id,
            user_role=ParticipantRole.TEACHER,
            user_name=teacher_name,
            reaction_type=reaction_data["reaction_type"],
            reaction_emoji=reaction_data.get("reaction_emoji", "👍"),
            reacted_at=datetime.now()
        )
        
        service.db.add(reaction)
        service.db.commit()
        
        return {
            "message": "Reaction added successfully",
            "reaction_type": reaction.reaction_type,
            "reaction_emoji": reaction.reaction_emoji
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/subjects", response_model=List[dict])
async async def get_teacher_subjects(
    teacher_id: UUID,  # In real app, get from authenticated session
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get subjects taught by the teacher"""
    service = DoubtChatService(db)
    
    try:
        from ...models.tenant_specific.grades_assessment import ClassSubject, Subject
        
        # Get subjects taught by the teacher
        subjects = service.db.query(Subject, ClassSubject).join(
            ClassSubject, Subject.id == ClassSubject.subject_id
        ).filter(
            ClassSubject.teacher_id == teacher_id,
            ClassSubject.is_active == True,
            Subject.is_active == True,
            Subject.tenant_id == tenant_id
        ).distinct().all()
        
        result = []
        for subject, class_subject in subjects:
            # Get active chat count for this subject
            active_chats = service.db.query(service.model).filter(
                service.model.teacher_id == teacher_id,
                service.model.subject_id == subject.id,
                service.model.status == ChatStatus.ACTIVE,
                service.model.is_deleted == False
            ).count()
            
            # Get total chats for this subject
            total_chats = service.db.query(service.model).filter(
                service.model.teacher_id == teacher_id,
                service.model.subject_id == subject.id,
                service.model.is_deleted == False
            ).count()
            
            result.append({
                "subject_id": str(subject.id),
                "subject_name": subject.subject_name,
                "subject_code": subject.subject_code,
                "description": subject.description,
                "department": subject.department,
                "active_chats": active_chats,
                "total_chats": total_chats
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
