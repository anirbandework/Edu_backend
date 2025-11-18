# app/routers/chat/websocket_router.py
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging
from ...core.database import get_db
from ...services.chat.chat_service import ChatService
from ...services.chat.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: UUID = Query(...),
    user_type: str = Query(..., regex="^(teacher|student)$"),
    tenant_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time chat"""
    await websocket_manager.connect(websocket, user_id, user_type, tenant_id)
    service = ChatService(db)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            message_type = message_data.get("type")
            
            if message_type == "join_room":
                # Join a specific chat room
                chat_room_id = UUID(message_data.get("chat_room_id"))
                logger.info(f"User {user_id} ({user_type}) joining room {chat_room_id}")
                await websocket_manager.join_chat_room(user_id, chat_room_id)
                
            elif message_type == "leave_room":
                # Leave a specific chat room
                chat_room_id = UUID(message_data.get("chat_room_id"))
                await websocket_manager.leave_chat_room(user_id, chat_room_id)
                
            elif message_type == "send_message":
                # Send a chat message
                logger.info(f"RECEIVED WEBSOCKET MESSAGE: {message_data}")
                try:
                    teacher_id = UUID(message_data.get("teacher_id"))
                    student_id = UUID(message_data.get("student_id"))
                    message_text = message_data.get("message")
                    
                    logger.info(f"Processing message from {user_id} ({user_type}): {message_text}")
                    
                    # Get or create chat room
                    chat_room = await service.get_or_create_chat_room(
                        teacher_id=teacher_id,
                        student_id=student_id,
                        tenant_id=tenant_id
                    )
                    
                    logger.info(f"Chat room ID: {chat_room.id}")
                    
                    # Send message to database
                    message = await service.send_message(
                        chat_room_id=chat_room.id,
                        sender_id=user_id,
                        sender_type=user_type,
                        message=message_text
                    )
                    
                    logger.info(f"Message saved to database with ID: {message.id}")
                    
                    # Broadcast message to room subscribers
                    broadcast_data = {
                        "type": "new_message",
                        "message_id": str(message.id),
                        "chat_room_id": str(chat_room.id),
                        "sender_id": str(user_id),
                        "sender_type": user_type,
                        "message": message_text,
                        "timestamp": message.created_at.isoformat()
                    }
                    
                    logger.info(f"Broadcasting message to room {chat_room.id}")
                    await websocket_manager.broadcast_to_room(
                        broadcast_data, 
                        chat_room.id, 
                        exclude_user=user_id
                    )
                    
                    # Send confirmation to sender
                    await websocket_manager.send_personal_message({
                        "type": "message_sent",
                        "message_id": str(message.id),
                        "timestamp": message.created_at.isoformat()
                    }, user_id)
                    
                    logger.info(f"Message processing complete for {message.id}")
                    
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    await websocket_manager.send_personal_message({
                        "type": "error",
                        "message": "Failed to send message"
                    }, user_id)
                    
            elif message_type == "mark_read":
                # Mark messages as read
                try:
                    chat_room_id = UUID(message_data.get("chat_room_id"))
                    await service.mark_messages_as_read(chat_room_id, user_type)
                    
                    # Notify other user in the room
                    await websocket_manager.broadcast_to_room({
                        "type": "messages_read",
                        "chat_room_id": str(chat_room_id),
                        "reader_type": user_type
                    }, chat_room_id, exclude_user=user_id)
                    
                except Exception as e:
                    logger.error(f"Error marking messages as read: {e}")
                    
            elif message_type == "typing":
                # Handle typing indicators
                try:
                    chat_room_id = UUID(message_data.get("chat_room_id"))
                    is_typing = message_data.get("is_typing", False)
                    
                    await websocket_manager.broadcast_to_room({
                        "type": "typing_indicator",
                        "chat_room_id": str(chat_room_id),
                        "user_id": str(user_id),
                        "user_type": user_type,
                        "is_typing": is_typing
                    }, chat_room_id, exclude_user=user_id)
                    
                except Exception as e:
                    logger.error(f"Error handling typing indicator: {e}")
                    
            else:
                # Unknown message type
                await websocket_manager.send_personal_message({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }, user_id)
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected from chat")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        websocket_manager.disconnect(user_id)