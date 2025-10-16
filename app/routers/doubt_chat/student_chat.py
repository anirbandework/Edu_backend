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
    ChatStatus, MessageType, ParticipantRole, ChatParticipant, 
    MessageReaction, ChatMessage
)

router = APIRouter(prefix="/api/v1/student/chat", tags=["Student - Doubt Chat"])

@router.get("/subjects", response_model=List[dict])
async async def get_subjects_with_teachers(
    student_id: UUID,  # In real app, get from authenticated session
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get subjects where student can chat with teachers"""
    service = DoubtChatService(db)
    
    try:
        # Get subjects for student's class/grade
        from ...models.tenant_specific.student import Student
        from ...models.tenant_specific.grades_assessment import Subject, ClassSubject
        
        student = service.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Get subjects taught in student's class
        subjects = service.db.query(Subject, ClassSubject).join(
            ClassSubject, Subject.id == ClassSubject.subject_id
        ).filter(
            ClassSubject.class_id == student.class_id,
            ClassSubject.is_active == True,
            Subject.is_active == True,
            Subject.tenant_id == tenant_id
        ).all()
        
        result = []
        for subject, class_subject in subjects:
            # Get available teachers count for this subject
            teachers = service.get_available_teachers_for_subject(
                student_id=student_id,
                subject_id=subject.id,
                tenant_id=tenant_id
            )
            
            result.append({
                "subject_id": str(subject.id),
                "subject_name": subject.subject_name,
                "subject_code": subject.subject_code,
                "description": subject.description,
                "department": subject.department,
                "available_teachers": len([t for t in teachers if t["is_currently_available"]]),
                "total_teachers": len(teachers)
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/teachers/{subject_id}", response_model=List[dict])
async async def get_available_teachers(
    subject_id: UUID,
    student_id: UUID,  # In real app, get from authenticated session
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get available teachers for a specific subject"""
    service = DoubtChatService(db)
    
    try:
        teachers = service.get_available_teachers_for_subject(
            student_id=student_id,
            subject_id=subject_id,
            tenant_id=tenant_id
        )
        return teachers
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rooms", response_model=dict)
async async def create_chat_room(
    chat_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Create a new doubt chat room"""
    service = DoubtChatService(db)
    
    try:
        chat_room = service.create_chat_room(
            student_id=UUID(chat_data["student_id"]),
            teacher_id=UUID(chat_data["teacher_id"]),
            subject_id=UUID(chat_data["subject_id"]),
            chat_data={k: v for k, v in chat_data.items() 
                      if k not in ["student_id", "teacher_id", "subject_id"]}
        )
        
        return {
            "id": str(chat_room.id),
            "room_code": chat_room.room_code,
            "room_name": chat_room.room_name,
            "message": "Chat room created successfully",
            "started_at": chat_room.started_at.isoformat(),
            "subject_name": chat_room.subject.subject_name,
            "teacher_name": f"{chat_room.teacher.personal_info.get('basic_details', {}).get('first_name', '')} {chat_room.teacher.personal_info.get('basic_details', {}).get('last_name', '')}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rooms", response_model=dict)
async async def get_student_chat_rooms(
    student_id: UUID,  # In real app, get from authenticated session
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[ChatStatus] = Query(None),
    subject_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated chat rooms for a student"""
    service = DoubtChatService(db)
    
    try:
        filters = {"student_id": student_id}
        if status:
            filters["status"] = status
        if subject_id:
            filters["subject_id"] = subject_id
        
        result = service.get_paginated(page=page, size=size, **filters)
        
        formatted_rooms = [
            {
                "id": str(room.id),
                "room_name": room.room_name,
                "room_code": room.room_code,
                "topic": room.topic,
                "subject_name": room.subject.subject_name,
                "teacher_name": f"{room.teacher.personal_info.get('basic_details', {}).get('first_name', '')} {room.teacher.personal_info.get('basic_details', {}).get('last_name', '')}",
                "status": room.status.value,
                "urgency_level": room.urgency_level,
                "started_at": room.started_at.isoformat(),
                "last_activity_at": room.last_activity_at.isoformat(),
                "total_messages": room.total_messages,
                "is_resolved": room.is_resolved
            }
            for room in result["items"]
        ]
        
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
async async def get_chat_history(
    room_id: UUID,
    user_id: UUID,  # In real app, get from authenticated session
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    before_message_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a room"""
    service = DoubtChatService(db)
    
    try:
        messages = service.get_chat_history(
            chat_room_id=room_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            before_message_id=before_message_id
        )
        return messages
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rooms/{room_id}/messages", response_model=dict)
async async def send_message(
    room_id: UUID,
    message_data: dict,
    sender_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Send a message in the chat room"""
    service = DoubtChatService(db)
    
    try:
        message = service.send_message(
            chat_room_id=room_id,
            sender_id=sender_id,
            sender_role=ParticipantRole.STUDENT,
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

@router.post("/rooms/{room_id}/close", response_model=dict)
async async def close_chat_room(
    room_id: UUID,
    resolution_data: dict,
    student_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Close and resolve a chat room"""
    service = DoubtChatService(db)
    
    try:
        chat_room = service.close_chat_room(
            chat_room_id=room_id,
            closed_by=student_id,
            resolution_data=resolution_data
        )
        
        return {
            "id": str(chat_room.id),
            "message": "Chat room closed successfully",
            "status": chat_room.status.value,
            "is_resolved": chat_room.is_resolved,
            "closed_at": chat_room.closed_at.isoformat() if chat_room.closed_at else None,
            "duration_minutes": chat_room.duration_minutes
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rooms/{room_id}", response_model=dict)
async async def get_chat_room_details(
    room_id: UUID,
    user_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a chat room"""
    service = DoubtChatService(db)
    
    try:
        chat_room = service.get(room_id)
        if not chat_room:
            raise HTTPException(status_code=404, detail="Chat room not found")
        
        # Verify user is a participant
        participant = service.db.query(ChatParticipant).filter(
            ChatParticipant.chat_room_id == room_id,
            ChatParticipant.participant_id == user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(status_code=403, detail="Access denied")
        
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
            "teacher": {
                "id": str(chat_room.teacher.id),
                "name": f"{chat_room.teacher.personal_info.get('basic_details', {}).get('first_name', '')} {chat_room.teacher.personal_info.get('basic_details', {}).get('last_name', '')}",
                "department": chat_room.teacher.employment.get('job_information', {}).get('department', '')
            },
            "started_at": chat_room.started_at.isoformat(),
            "last_activity_at": chat_room.last_activity_at.isoformat(),
            "total_messages": chat_room.total_messages,
            "is_resolved": chat_room.is_resolved,
            "academic_year": chat_room.academic_year,
            "chapter": chat_room.chapter,
            "lesson": chat_room.lesson
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rooms/{room_id}/messages/{message_id}/reaction", response_model=dict)
async async def add_message_reaction(
    room_id: UUID,
    message_id: UUID,
    reaction_data: dict,
    user_id: UUID,  # In real app, get from authenticated session
    db: AsyncSession = Depends(get_db)
):
    """Add reaction to a message"""
    try:
        from ...models.tenant_specific.student import Student
        
        # Verify user is participant
        service = DoubtChatService(db)
        participant = service.db.query(ChatParticipant).filter(
            ChatParticipant.chat_room_id == room_id,
            ChatParticipant.participant_id == user_id,
            ChatParticipant.is_active == True
        ).first()
        
        if not participant:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get user info
        student = service.db.query(Student).filter(Student.id == user_id).first()
        
        # Check if reaction already exists
        existing_reaction = service.db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == user_id,
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
            user_id=user_id,
            user_role=ParticipantRole.STUDENT,
            user_name=f"{student.first_name} {student.last_name}",
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
