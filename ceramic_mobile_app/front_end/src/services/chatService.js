import { API_CONFIG } from '../constants/config.js';
import { secureStorage } from '../utils/secureStorage.js';

class ChatService {
  ws = null;
  reconnectAttempts = 0;
  maxReconnectAttempts = 5;
  reconnectDelay = 1000; // Start with 1 second
  heartbeatInterval = null;
  messageListeners = [];
  connectionListeners = [];
  typingTimeouts = new Map();
  isConnecting = false;
  shouldReconnect = true;

  // WebSocket connection management
  async connect(userId) {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.isConnecting = true;

    try {
      const tokens = await secureStorage.getTokens();
      if (!tokens?.accessToken) {
        throw new Error('No authentication token found');
      }

      // Create WebSocket URL using centralized config
      const wsUrl = `${API_CONFIG.WS_URL}/api/v1/chat/ws/${userId}?token=${encodeURIComponent(tokens.accessToken)}`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.startHeartbeat();
        this.notifyConnectionListeners(true);
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleWebSocketMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.isConnecting = false;
        this.stopHeartbeat();
        this.notifyConnectionListeners(false);
        
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect(userId);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.isConnecting = false;
      };

    } catch (error) {
      this.isConnecting = false;
      console.error('Error connecting to WebSocket:', error);
      throw error;
    }
  }

  scheduleReconnect(userId) {
    this.reconnectAttempts++;
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${this.reconnectDelay}ms`);
    
    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect(userId);
      }
    }, this.reconnectDelay);

    // Exponential backoff with jitter
    this.reconnectDelay = Math.min(this.reconnectDelay * 2 + Math.random() * 1000, 30000);
  }

  disconnect() {
    this.shouldReconnect = false;
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.notifyConnectionListeners(false);
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendMessage({
          type: 'heartbeat'
        });
      }
    }, 30000); // Send heartbeat every 30 seconds
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  handleWebSocketMessage(message) {
    switch (message.type) {
      case 'new_message':
      case 'messages_read':
      case 'user_typing':
        this.notifyMessageListeners(message);
        break;
      case 'error':
        console.error('WebSocket error message:', message);
        break;
      case 'heartbeat_response':
        // Handle heartbeat response silently
        break;
      default:
        console.log('Unknown message type:', message.type);
        break;
    }
  }

  // Message sending
  sendMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, message not sent:', message);
    }
  }

  sendChatMessage(
    chatRoomId, 
    receiverId, 
    content, 
    messageType = 'text',
    imageUrl = null,
    clientMessageId = null
  ) {
    this.sendMessage({
      type: 'send_message',
      chat_room_id: chatRoomId,
      receiver_id: receiverId,
      content,
      message_type: messageType,
      image_url: imageUrl,
      client_message_id: clientMessageId
    });
  }

  sendTypingIndicator(chatRoomId, isTyping) {
    // Clear existing timeout for this chat room
    if (this.typingTimeouts.has(chatRoomId)) {
      clearTimeout(this.typingTimeouts.get(chatRoomId));
      this.typingTimeouts.delete(chatRoomId);
    }

    this.sendMessage({
      type: 'typing',
      chat_room_id: chatRoomId,
      is_typing: isTyping
    });

    // Auto-stop typing after 3 seconds of no activity
    if (isTyping) {
      const timeout = setTimeout(() => {
        this.sendTypingIndicator(chatRoomId, false);
      }, 3000);
      this.typingTimeouts.set(chatRoomId, timeout);
    }
  }

  markMessagesAsRead(chatRoomId, messageIds) {
    if (messageIds.length === 0) return;
    
    this.sendMessage({
      type: 'mark_read',
      chat_room_id: chatRoomId,
      message_ids: messageIds
    });
  }

  // Event listeners
  addMessageListener(callback) {
    this.messageListeners.push(callback);
    
    // Return unsubscribe function
    return () => {
      const index = this.messageListeners.indexOf(callback);
      if (index > -1) {
        this.messageListeners.splice(index, 1);
      }
    };
  }

  addConnectionListener(callback) {
    this.connectionListeners.push(callback);
    
    // Return unsubscribe function
    return () => {
      const index = this.connectionListeners.indexOf(callback);
      if (index > -1) {
        this.connectionListeners.splice(index, 1);
      }
    };
  }

  notifyMessageListeners(message) {
    this.messageListeners.forEach(callback => {
      try {
        callback(message);
      } catch (error) {
        console.error('Error in message listener:', error);
      }
    });
  }

  notifyConnectionListeners(isConnected) {
    this.connectionListeners.forEach(callback => {
      try {
        callback(isConnected);
      } catch (error) {
        console.error('Error in connection listener:', error);
      }
    });
  }

  // Utility methods
  isConnected() {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getConnectionState() {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'disconnecting';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }

  async getChatRooms() {
    const tokens = await secureStorage.getTokens();
    const token = tokens?.accessToken;
    const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/chat/rooms`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch chat rooms: ${response.status}`);
    }

    return response.json();
  }

  async getChatMessages(
    chatRoomId,
    skip = 0,
    limit = 50,
    markAsRead = true
  ) {
    const tokens = await secureStorage.getTokens();
    const token = tokens?.accessToken;
    const url = new URL(`${API_CONFIG.BASE_URL}/api/v1/chat/rooms/${chatRoomId}/messages`);
    url.searchParams.append('skip', skip.toString());
    url.searchParams.append('limit', limit.toString());
    url.searchParams.append('mark_as_read', markAsRead.toString());

    const response = await fetch(url.toString(), {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch messages: ${response.status}`);
    }

    const messages = await response.json();
    return messages.reverse(); // Reverse to show oldest first
  }

  async createChatRoom(sellerId, productId) {
    const tokens = await secureStorage.getTokens();
    const token = tokens?.accessToken;
    const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/chat/rooms`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        seller_id: sellerId,
        product_id: productId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create chat room: ${response.status}`);
    }

    return response.json();
  }

  async getOnlineUsers() {
    const tokens = await secureStorage.getTokens();
    const token = tokens?.accessToken;
    const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/chat/online-users`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch online users: ${response.status}`);
    }

    return response.json();
  }

  // Clean up resources
  cleanup() {
    this.disconnect();
    this.messageListeners = [];
    this.connectionListeners = [];
    
    // Clear all typing timeouts
    this.typingTimeouts.forEach(timeout => clearTimeout(timeout));
    this.typingTimeouts.clear();
  }
}

// Export singleton instance
export const chatService = new ChatService();