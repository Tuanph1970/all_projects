from pydantic import BaseModel
from typing import Optional, List, Union
from datetime import datetime

class MessageBase(BaseModel):
    content: str
    message_type: str = "text"
    image_url: Optional[str] = None

class MessageCreate(MessageBase):
    receiver_id: int
    chat_room_id: Optional[int] = None
    product_id: Optional[int] = None

class MessageResponse(MessageBase):
    id: int
    chat_room_id: int
    sender_id: int
    receiver_id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    sender_name: Optional[str] = None
    reply_to_id: Optional[int] = None
    client_message_id: Optional[str] = None

    class Config:
        from_attributes = True

class ChatRoomResponse(BaseModel):
    id: int
    customer_id: int
    seller_id: int
    product_id: Optional[int] = None
    is_active: bool
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[MessageResponse] = []
    customer_name: Optional[str] = None
    seller_name: Optional[str] = None
    product_title: Optional[str] = None
    unread_count: Optional[int] = 0
    last_message: Optional[str] = None
    is_online: Optional[bool] = False

    class Config:
        from_attributes = True

# WebSocket message schemas
class WSMessageBase(BaseModel):
    type: str

class WSChatMessage(WSMessageBase):
    type: str = "chat_message"
    chat_room_id: int
    receiver_id: int
    content: str
    message_type: str = "text"
    image_url: Optional[str] = None

class WSTypingIndicator(WSMessageBase):
    type: Union[str, str] = "typing_start"
    chat_room_id: int

class WSMarkRead(WSMessageBase):
    type: str = "mark_read"
    chat_room_id: int
    message_ids: List[int]

class WSHeartbeat(WSMessageBase):
    type: str = "heartbeat"

class WSNewMessage(WSMessageBase):
    type: str = "new_message"
    data: MessageResponse

class WSUserTyping(WSMessageBase):
    type: str = "user_typing"
    data: dict

class WSMessagesRead(WSMessageBase):
    type: str = "messages_read"
    data: dict

class WSError(WSMessageBase):
    type: str = "error"
    message: str

class WSHeartbeatResponse(WSMessageBase):
    type: str = "heartbeat_response"
    timestamp: str
