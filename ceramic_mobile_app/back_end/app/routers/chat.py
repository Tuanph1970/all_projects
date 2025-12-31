from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime
import json
from app.core.database import get_db
from app.routers.auth import get_current_user, get_user_from_token
from app.models.user import User
from app.models.chat import ChatRoom, Message
from app.schemas.chat import MessageCreate, MessageResponse, ChatRoomResponse
from app.services.websocket_manager import manager

router = APIRouter()

@router.post("/rooms/{chat_room_id}/messages", response_model=MessageResponse)
def send_message(
    chat_room_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify chat room exists and user has access
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == chat_room_id).first()
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    if current_user.id not in [chat_room.customer_id, chat_room.seller_id]:
        raise HTTPException(status_code=403, detail="Not authorized to send messages in this chat room")
    
    db_message = Message(
        chat_room_id=chat_room_id,
        sender_id=current_user.id,
        receiver_id=message.receiver_id,
        content=message.content,
        message_type=message.message_type,
        image_url=message.image_url
    )
    db.add(db_message)
    
    # Update chat room last message time
    from sqlalchemy.sql import func
    chat_room.last_message_at = func.now()
    
    db.commit()
    db.refresh(db_message)
    return db_message

@router.get("/rooms", response_model=List[ChatRoomResponse])
def read_chat_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get chat rooms for current user
    chat_rooms = db.query(ChatRoom).filter(
        or_(
            ChatRoom.customer_id == current_user.id,
            ChatRoom.seller_id == current_user.id
        )
    ).order_by(ChatRoom.last_message_at.desc()).all()

    enhanced_rooms = []
    for room in chat_rooms:
        # Get other participant's name
        other_user_id = room.seller_id if room.customer_id == current_user.id else room.customer_id
        other_user = db.query(User).filter(User.id == other_user_id).first()
        other_user_name = other_user.full_name if other_user else "Unknown User"
        
        # Get unread message count
        unread_count = db.query(Message).filter(
            Message.chat_room_id == room.id,
            Message.receiver_id == current_user.id,
            Message.is_read == False
        ).count()
        
        # Get last message
        last_message = db.query(Message).filter(
            Message.chat_room_id == room.id
        ).order_by(Message.created_at.desc()).first()
        
        # Get product info if exists
        product_title = None
        if room.product_id:
            from app.models.product import Product
            product = db.query(Product).filter(Product.id == room.product_id).first()
            product_title = product.name if product else "Unknown Product"
        
        # Check if other user is online
        is_online = manager.is_user_online(other_user_id)
        
        room_dict = {
            "id": room.id,
            "customer_id": room.customer_id,
            "seller_id": room.seller_id,
            "product_id": room.product_id,
            "is_active": room.is_active,
            "last_message_at": room.last_message_at,
            "created_at": room.created_at,
            "updated_at": room.updated_at,
            "messages": [],
            "customer_name": other_user_name if room.customer_id != current_user.id else current_user.full_name,
            "seller_name": other_user_name if room.seller_id != current_user.id else current_user.full_name,
            "product_title": product_title,
            "unread_count": unread_count,
            "last_message": last_message.content if last_message else None,
            "is_online": is_online
        }
        
        enhanced_rooms.append(ChatRoomResponse(**room_dict))
    
    return enhanced_rooms

@router.get("/rooms/{chat_room_id}/messages", response_model=List[MessageResponse])
def read_messages(
    chat_room_id: int,
    skip: int = 0,
    limit: int = 50,
    mark_as_read: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify access to chat room
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == chat_room_id).first()
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    if current_user.id not in [chat_room.customer_id, chat_room.seller_id]:
        raise HTTPException(status_code=403, detail="Not authorized to view this chat room")
    
    # Get messages with sender names
    messages_query = db.query(Message, User.full_name).join(
        User, Message.sender_id == User.id
    ).filter(
        Message.chat_room_id == chat_room_id,
        Message.is_deleted == False
    ).order_by(Message.created_at.desc()).offset(skip).limit(limit)
    
    # Build response with sender names
    messages = []
    for message, sender_name in messages_query:
        message_dict = {
            "id": message.id,
            "chat_room_id": message.chat_room_id,
            "sender_id": message.sender_id,
            "receiver_id": message.receiver_id,
            "content": message.content,
            "message_type": message.message_type,
            "image_url": message.image_url,
            "is_read": message.is_read,
            "created_at": message.created_at,
            "read_at": message.read_at,
            "sender_name": sender_name
        }
        messages.append(MessageResponse(**message_dict))
    
    # Mark messages as read if requested
    if mark_as_read:
        unread_messages = db.query(Message).filter(
            Message.chat_room_id == chat_room_id,
            Message.receiver_id == current_user.id,
            Message.is_read == False
        ).all()
        
        for msg in unread_messages:
            msg.is_read = True
            from sqlalchemy.sql import func
            msg.read_at = func.now()
        
        if unread_messages:
            db.commit()

            # Note: WebSocket broadcast for read receipts should be handled via WebSocket connection
            # Cannot use asyncio.create_task in synchronous route
    
    return messages

@router.post("/rooms", response_model=ChatRoomResponse)
def create_or_get_chat_room(
    seller_id: int,
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if chat room already exists
    existing_room = db.query(ChatRoom).filter(
        and_(
            ChatRoom.customer_id == current_user.id,
            ChatRoom.seller_id == seller_id,
            ChatRoom.product_id == product_id
        )
    ).first()
    
    if existing_room:
        return existing_room
    
    # Create new chat room
    chat_room = ChatRoom(
        customer_id=current_user.id,
        seller_id=seller_id,
        product_id=product_id
    )
    db.add(chat_room)
    db.commit()
    db.refresh(chat_room)
    return chat_room

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for real-time messaging"""
    try:
        # Authenticate user via token
        if not token:
            await websocket.close(code=1008, reason="No token provided")
            return
        
        user = get_user_from_token(token, db)
        if not user or user.id != user_id:
            await websocket.close(code=1008, reason="Invalid authentication")
            return
        
        # Connect user
        await manager.connect(websocket, user_id)
        
        try:
            while True:
                # Receive message from WebSocket
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle the message
                await manager.handle_message(websocket, message_data, user_id, db)
                
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)
        except Exception as e:
            print(f"WebSocket error for user {user_id}: {e}")
            manager.disconnect(websocket, user_id)
    
    except Exception as e:
        print(f"WebSocket connection error: {e}")
        await websocket.close(code=1011, reason="Internal server error")

@router.get("/online-users")
def get_online_users(current_user: User = Depends(get_current_user)):
    """Get list of online users"""
    return {
        "online_users": manager.get_online_users(),
        "total_online": len(manager.get_online_users())
    }

@router.get("/rooms/{chat_room_id}/typing")
def get_typing_users(
    chat_room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users currently typing in a chat room"""
    # Verify access to chat room
    chat_room = db.query(ChatRoom).filter(ChatRoom.id == chat_room_id).first()
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    if current_user.id not in [chat_room.customer_id, chat_room.seller_id]:
        raise HTTPException(status_code=403, detail="Not authorized to view this chat room")
    
    typing_users = manager.typing_users.get(chat_room_id, {})
    return {
        "chat_room_id": chat_room_id,
        "typing_users": list(typing_users.keys())
    }