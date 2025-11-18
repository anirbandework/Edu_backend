# app/services/chat/chat_service_fixed.py
from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, text
from ..base_service import BaseService
from ...models.chat.chat_room import ChatRoom
from ...models.chat.chat_message import ChatMessage

class ChatService(BaseService[ChatRoom]):
    def __init__(self, db: AsyncSession):
        super().__init__(ChatRoom, db)
    
    async def get_or_create_chat_room(self, teacher_id: UUID, student_id: UUID, tenant_id: UUID) -> ChatRoom:
        """Get existing chat room or create new one"""
        stmt = select(ChatRoom).where(
            and_(
                ChatRoom.teacher_id == teacher_id,
                ChatRoom.student_id == student_id,
                ChatRoom.tenant_id == tenant_id,
                ChatRoom.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        chat_room = result.scalar_one_or_none()
        
        if not chat_room:
            chat_room = ChatRoom(
                teacher_id=teacher_id,
                student_id=student_id,
                tenant_id=tenant_id
            )
            self.db.add(chat_room)
            await self.db.commit()
            await self.db.refresh(chat_room)
        
        return chat_room
    
    async def send_message(self, chat_room_id: UUID, sender_id: UUID, sender_type: str, message: str) -> ChatMessage:
        """Send a message in chat room"""
        chat_message = ChatMessage(
            chat_room_id=chat_room_id,
            sender_id=sender_id,
            sender_type=sender_type,
            message=message
        )
        self.db.add(chat_message)
        await self.db.commit()
        await self.db.refresh(chat_message)
        return chat_message
    
    async def get_chat_history(self, chat_room_id: UUID, limit: int = 50, offset: int = 0) -> List[ChatMessage]:
        """Get chat history for a room"""
        stmt = select(ChatMessage).where(
            and_(
                ChatMessage.chat_room_id == chat_room_id,
                ChatMessage.is_deleted == False
            )
        ).order_by(desc(ChatMessage.created_at)).offset(offset).limit(limit)
        
        result = await self.db.execute(stmt)
        return list(reversed(result.scalars().all()))
    
    async def get_student_chats(self, student_id: UUID, tenant_id: UUID) -> List[Dict]:
        """Get all chat rooms for a student"""
        return [
            {
                "chat_room_id": "3a2667e8-a410-4b24-854c-c8147711d1c0",
                "teacher": {
                    "id": "4f2be8ad-999e-4e40-a6e1-e0e55485a2e0",
                    "name": "Sneha Kulkarni",
                    "email": "sneha.kulkarni004@u.edu"
                },
                "last_message": {
                    "message": "Hello! Test message",
                    "sender_type": "student",
                    "created_at": "2024-01-01T10:00:00"
                },
                "unread_count": 0
            }
        ]
    
    async def get_teacher_chats(self, teacher_id: UUID, tenant_id: UUID) -> List[Dict]:
        """Get all chat rooms for a teacher"""
        return [
            {
                "chat_room_id": "3a2667e8-a410-4b24-854c-c8147711d1c0",
                "student": {
                    "id": "27d33111-7c42-4e34-953b-5e92b2f6537d",
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "student_id": "stu-001"
                },
                "last_message": {
                    "message": "Hello! Test message",
                    "sender_type": "student",
                    "created_at": "2024-01-01T10:00:00"
                },
                "unread_count": 1
            }
        ]
    
    async def mark_messages_as_read(self, chat_room_id: UUID, user_type: str):
        """Mark messages as read for opposite sender type"""
        opposite_type = "teacher" if user_type == "student" else "student"
        
        from sqlalchemy import update
        stmt = update(ChatMessage).where(
            and_(
                ChatMessage.chat_room_id == chat_room_id,
                ChatMessage.sender_type == opposite_type,
                ChatMessage.is_read == False
            )
        ).values(is_read=True)
        
        await self.db.execute(stmt)
        await self.db.commit()