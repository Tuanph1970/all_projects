from typing import Dict, List, Optional
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.chat import ChatRoom, Message
from app.models.user import User

class ConnectionManager:
    def __init__(self):
        # Store active connections: {user_id: [websocket_connections]}
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Store typing users: {chat_room_id: {user_id: timestamp}}
        self.typing_users: Dict[int, Dict[int, datetime]] = {}
        # Store user presence: {user_id: last_seen}
        self.user_presence: Dict[int, datetime] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept WebSocket connection and register user"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        self.user_presence[user_id] = datetime.utcnow()
        
        # Broadcast online status to relevant chat rooms
        await self.broadcast_presence_update(user_id, "online")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove WebSocket connection and handle cleanup"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # If no more connections for this user, mark as offline
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                if user_id in self.user_presence:
                    del self.user_presence[user_id]
                
                # Broadcast offline status
                asyncio.create_task(self.broadcast_presence_update(user_id, "offline"))
    
    async def send_personal_message(self, message: str, user_id: int):
        """Send message to specific user"""
        if user_id in self.active_connections:
            disconnected_connections = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(message)
                except Exception:
                    # Connection is dead, mark for removal
                    disconnected_connections.append(websocket)
            
            # Clean up dead connections
            for dead_ws in disconnected_connections:
                self.active_connections[user_id].remove(dead_ws)
    
    async def send_to_chat_room(self, message: dict, chat_room_id: int, db: Session):
        """Send message to all users in a chat room"""
        try:
            # Get chat room participants
            chat_room = db.query(ChatRoom).filter(ChatRoom.id == chat_room_id).first()
            if not chat_room:
                return
            
            participants = [chat_room.customer_id, chat_room.seller_id]
            message_json = json.dumps(message)
            
            for user_id in participants:
                await self.send_personal_message(message_json, user_id)
                
        except Exception as e:
            print(f"Error sending message to chat room {chat_room_id}: {e}")
    
    async def handle_message(self, websocket: WebSocket, data: dict, user_id: int, db: Session):
        """Handle incoming WebSocket message"""
        try:
            message_type = data.get("type")
            
            if message_type == "chat_message":
                await self.handle_chat_message(data, user_id, db)
            elif message_type == "typing_start":
                await self.handle_typing_start(data, user_id, db)
            elif message_type == "typing_stop":
                await self.handle_typing_stop(data, user_id, db)
            elif message_type == "mark_read":
                await self.handle_mark_read(data, user_id, db)
            elif message_type == "heartbeat":
                await self.handle_heartbeat(user_id)
                
        except Exception as e:
            error_message = {
                "type": "error",
                "message": f"Error processing message: {str(e)}"
            }
            await websocket.send_text(json.dumps(error_message))
    
    async def handle_chat_message(self, data: dict, sender_id: int, db: Session):
        """Handle new chat message"""
        try:
            chat_room_id = data.get("chat_room_id")
            content = data.get("content")
            message_type = data.get("message_type", "text")
            image_url = data.get("image_url")
            receiver_id = data.get("receiver_id")
            
            if not chat_room_id or not content or not receiver_id:
                return
            
            # Verify chat room access
            chat_room = db.query(ChatRoom).filter(ChatRoom.id == chat_room_id).first()
            if not chat_room or sender_id not in [chat_room.customer_id, chat_room.seller_id]:
                return
            
            # Create message in database
            db_message = Message(
                chat_room_id=chat_room_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=content,
                message_type=message_type,
                image_url=image_url
            )
            db.add(db_message)
            
            # Update chat room last message time
            from sqlalchemy.sql import func
            chat_room.last_message_at = func.now()
            
            db.commit()
            db.refresh(db_message)
            
            # Broadcast message to chat room participants
            message_data = {
                "type": "new_message",
                "data": {
                    "id": db_message.id,
                    "chat_room_id": db_message.chat_room_id,
                    "sender_id": db_message.sender_id,
                    "receiver_id": db_message.receiver_id,
                    "content": db_message.content,
                    "message_type": db_message.message_type,
                    "image_url": db_message.image_url,
                    "is_read": db_message.is_read,
                    "created_at": db_message.created_at.isoformat(),
                    "read_at": db_message.read_at.isoformat() if db_message.read_at else None
                }
            }
            
            await self.send_to_chat_room(message_data, chat_room_id, db)
            
        except Exception as e:
            print(f"Error handling chat message: {e}")
    
    async def handle_typing_start(self, data: dict, user_id: int, db: Session):
        """Handle typing indicator start"""
        chat_room_id = data.get("chat_room_id")
        if not chat_room_id:
            return
        
        if chat_room_id not in self.typing_users:
            self.typing_users[chat_room_id] = {}
        
        self.typing_users[chat_room_id][user_id] = datetime.utcnow()
        
        # Broadcast typing indicator
        typing_data = {
            "type": "user_typing",
            "data": {
                "chat_room_id": chat_room_id,
                "user_id": user_id,
                "is_typing": True
            }
        }
        
        await self.send_to_chat_room(typing_data, chat_room_id, db)
    
    async def handle_typing_stop(self, data: dict, user_id: int, db: Session):
        """Handle typing indicator stop"""
        chat_room_id = data.get("chat_room_id")
        if not chat_room_id:
            return
        
        if chat_room_id in self.typing_users and user_id in self.typing_users[chat_room_id]:
            del self.typing_users[chat_room_id][user_id]
        
        # Broadcast typing stop
        typing_data = {
            "type": "user_typing",
            "data": {
                "chat_room_id": chat_room_id,
                "user_id": user_id,
                "is_typing": False
            }
        }
        
        await self.send_to_chat_room(typing_data, chat_room_id, db)
    
    async def handle_mark_read(self, data: dict, user_id: int, db: Session):
        """Handle message read confirmation"""
        try:
            message_ids = data.get("message_ids", [])
            chat_room_id = data.get("chat_room_id")
            
            if not message_ids or not chat_room_id:
                return
            
            # Mark messages as read
            messages = db.query(Message).filter(
                Message.id.in_(message_ids),
                Message.receiver_id == user_id
            ).all()
            
            for message in messages:
                if not message.is_read:
                    message.is_read = True
                    from sqlalchemy.sql import func
                    message.read_at = func.now()
            
            db.commit()
            
            # Broadcast read receipts
            read_data = {
                "type": "messages_read",
                "data": {
                    "chat_room_id": chat_room_id,
                    "message_ids": message_ids,
                    "reader_id": user_id,
                    "read_at": datetime.utcnow().isoformat()
                }
            }
            
            await self.send_to_chat_room(read_data, chat_room_id, db)
            
        except Exception as e:
            print(f"Error marking messages as read: {e}")
    
    async def handle_heartbeat(self, user_id: int):
        """Handle heartbeat for presence"""
        self.user_presence[user_id] = datetime.utcnow()
        
        # Send heartbeat response
        heartbeat_data = {
            "type": "heartbeat_response",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_personal_message(json.dumps(heartbeat_data), user_id)
    
    async def broadcast_presence_update(self, user_id: int, status: str):
        """Broadcast user presence update to relevant chat rooms"""
        # This would require getting all chat rooms for the user
        # For now, we'll skip this implementation
        pass
    
    def get_online_users(self) -> List[int]:
        """Get list of currently online users"""
        return list(self.active_connections.keys())
    
    def is_user_online(self, user_id: int) -> bool:
        """Check if user is currently online"""
        return user_id in self.active_connections

# Global connection manager instance
manager = ConnectionManager()