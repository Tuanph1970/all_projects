import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
  TextInput,
  TouchableOpacity,
} from 'react-native';
import {
  Text,
  Appbar,
  IconButton,
  Surface,
  Badge,
  Card,
} from 'react-native-paper';
import { useRoute, useFocusEffect } from '@react-navigation/native';
import { useSelector } from 'react-redux';
import { colors, spacing, typography } from '../../constants/theme.js';
import { chatService } from '../../services/chatService.js';
import { useTranslation } from '@i18n';

const MessageBubble = ({
  message,
  isCurrentUser,
  showSenderName = false,
}) => {
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <View style={[
      styles.messageBubble,
      isCurrentUser ? styles.currentUserBubble : styles.otherUserBubble
    ]}>
      {showSenderName && !isCurrentUser && (
        <Text style={styles.senderName}>{message.sender_name}</Text>
      )}
      
      {message.message_type === 'image' && message.image_url ? (
        <View style={styles.imageMessage}>
          <Text style={styles.imageMessageText}>📷 Image</Text>
          <Text style={[styles.messageContent, isCurrentUser ? styles.currentUserText : styles.otherUserText]}>
            {message.content}
          </Text>
        </View>
      ) : (
        <Text style={[styles.messageContent, isCurrentUser ? styles.currentUserText : styles.otherUserText]}>
          {message.content}
        </Text>
      )}

      <View style={styles.messageFooter}>
        <Text style={[styles.messageTime, isCurrentUser ? styles.currentUserTime : styles.otherUserTime]}>
          {formatTime(message.created_at)}
        </Text>
        {isCurrentUser && (
          <Text style={styles.messageStatus}>
            {message.is_read ? (
              <Text style={styles.readStatus}>✓✓</Text>
            ) : (
              <Text style={styles.deliveredStatus}>✓</Text>
            )}
          </Text>
        )}
      </View>
    </View>
  );
};

const TypingIndicator = ({ typingUsers, t }) => {
  if (typingUsers.length === 0) return null;

  return (
    <View style={styles.typingIndicator}>
      <Text style={styles.typingText}>
        {typingUsers.length === 1 ? t('chat.typing') : t('chat.peopleTyping', { count: typingUsers.length })}
      </Text>
    </View>
  );
};

export const ChatScreen = () => {
  const route = useRoute();
  const t = useTranslation();
  const { sellerId, productId, conversationId, recipientName } = route.params || {};
  const currentUser = useSelector((state) => state.auth.user);

  // State
  const [messages, setMessages] = useState([]);
  const [chatRoom, setChatRoom] = useState(null);
  const [roomId, setRoomId] = useState(conversationId);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [typingUsers, setTypingUsers] = useState([]);
  const [isTyping, setIsTyping] = useState(false);

  // Refs
  const flatListRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  const unsubscribeMessageListener = useRef(null);
  const unsubscribeConnectionListener = useRef(null);

  // Initialize chat and connect to WebSocket
  const initializeChat = useCallback(async () => {
    if (!currentUser) return;

    try {
      setIsLoading(true);

      // Connect to WebSocket
      await chatService.connect(currentUser.id);

      let actualRoomId = roomId;

      // If sellerId and productId provided, create or get the chat room first
      if (sellerId && productId && !roomId) {
        const room = await chatService.createOrGetRoom(sellerId, productId);
        actualRoomId = room.id;
        setRoomId(room.id);
        setChatRoom(room);
      }

      if (actualRoomId) {
        // Load chat messages
        const loadedMessages = await chatService.getChatMessages(actualRoomId);
        setMessages(loadedMessages);

        // Load chat room info if not already set
        if (!chatRoom) {
          const rooms = await chatService.getChatRooms();
          const currentRoom = rooms.find(room => room.id === actualRoomId);
          setChatRoom(currentRoom || null);
        }
      }

    } catch (error) {
      console.error('Error initializing chat:', error);
      Alert.alert(t('common.error'), t('chat.loadMessagesError'));
    } finally {
      setIsLoading(false);
    }
  }, [sellerId, productId, roomId, currentUser, chatRoom]);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((wsMessage) => {
    switch (wsMessage.type) {
      case 'new_message':
        const newMessage = wsMessage.data;
        if (newMessage.chat_room_id === roomId) {
          setMessages(prev => {
            // Avoid duplicates
            const exists = prev.some(msg => msg.id === newMessage.id);
            if (exists) return prev;
            return [...prev, newMessage];
          });
          
          // Auto-scroll to bottom
          setTimeout(() => {
            flatListRef.current?.scrollToEnd({ animated: true });
          }, 100);
          
          // Mark if from other user
          if (newMessage.sender_id !== currentUser?.id) {
            setTimeout(() => {
              chatService.markMessagesAsRead(roomId, [newMessage.id]);
            }, 1000);
          }
        }
        break;
        
      case 'messages_read':
        const readData = wsMessage.data;
        if (readData.chat_room_id === roomId) {
          setMessages(prev => prev.map(msg => 
            readData.message_ids.includes(msg.id) 
              ? { ...msg, is_read: true, read_at: readData.read_at } : msg
          ));
        }
        break;
        
      case 'user_typing':
        const typingData = wsMessage.data;
        if (typingData.chat_room_id === roomId) {
          setTypingUsers(prev => {
            const filtered = prev.filter(id => id !== typingData.user_id);
            return typingData.is_typing 
              ? [...filtered, typingData.user_id]
              : filtered;
          });
        }
        break;
    }
  }, [roomId, currentUser]);

  // Setup WebSocket listeners
  useEffect(() => {
    if (!currentUser) return;

    // Setup message listener
    unsubscribeMessageListener.current = chatService.addMessageListener(handleWebSocketMessage);
    
    // Setup connection listener
    unsubscribeConnectionListener.current = chatService.addConnectionListener(setIsConnected);
    
    // Initialize chat
    initializeChat();

    return () => {
      if (unsubscribeMessageListener.current) {
        unsubscribeMessageListener.current();
      }
      if (unsubscribeConnectionListener.current) {
        unsubscribeConnectionListener.current();
      }
    };
  }, [currentUser, handleWebSocketMessage, initializeChat]);

  // Handle focus effect
  useFocusEffect(
    useCallback(() => {
      // Mark messages when screen is focused
      const unreadMessages = messages
        .filter(msg => !msg.is_read && msg.receiver_id === currentUser?.id)
        .map(msg => msg.id)
        .filter(id => id !== undefined);
      
      if (unreadMessages.length > 0) {
        chatService.markMessagesAsRead(roomId, unreadMessages);
      }
    }, [messages, roomId, currentUser])
  );

  // Send message
  const sendMessage = useCallback(() => {
    if (!inputText.trim() || !chatRoom || !currentUser) return;

    const receiverId = chatRoom.customer_id === currentUser.id 
      ? chatRoom.seller_id
      : chatRoom.customer_id;
      
    const clientMessageId = `client_${Date.now()}_${Math.random()}`;
    
    // Optimistic update
    const optimisticMessage = {
      id: clientMessageId, // Temporary ID
      chat_room_id: roomId,
      sender_id: currentUser.id,
      receiver_id: receiverId,
      content: inputText,
      message_type: 'text',
      is_read: false,
      created_at: new Date().toISOString(),
      sender_name: currentUser.name,
      client_message_id: clientMessageId
    };
    
    setMessages(prev => [...prev, optimisticMessage]);
    setInputText('');
    
    // Send via WebSocket
    chatService.sendChatMessage(
      roomId,
      receiverId,
      inputText,
      'text',
      undefined,
      clientMessageId
    );
    
    // Auto-scroll to bottom
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, [inputText, chatRoom, currentUser, roomId]);

  // Handle typing
  const handleTyping = useCallback((text) => {
    setInputText(text);
    
    // Send typing indicator
    if (text.length > 0 && !isTyping) {
      setIsTyping(true);
      chatService.sendTypingIndicator(roomId, true);
    }
    
    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    // Set timeout to stop typing indicator
    typingTimeoutRef.current = setTimeout(() => {
      if (isTyping) {
        setIsTyping(false);
        chatService.sendTypingIndicator(roomId, false);
      }
    }, 2000);
  }, [roomId, isTyping]);

  // Render message item
  const renderMessage = ({ item }) => {
    const isCurrentUser = item.sender_id === currentUser?.id;
    return (
      <MessageBubble
        message={item}
        isCurrentUser={isCurrentUser}
        showSenderName={false}
      />
    );
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>{t('chat.loadingMessages')}</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* Header */}
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => {}} />
        <Appbar.Content
          title={recipientName}
          subtitle={
            <View style={styles.headerSubtitle}>
              <View style={[styles.connectionDot, isConnected ? styles.connectedDot : styles.disconnectedDot]} />
              <Text style={styles.connectionText}>
                {isConnected ? t('chat.online') : t('chat.offline')}
              </Text>
            </View>
          }
        />
        <Appbar.Action icon="dots-vertical" onPress={() => {}} />
      </Appbar.Header>

      {/* Messages List */}
      <View style={styles.messagesContainer}>
        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={(item) => item.client_message_id || item.id?.toString() || Math.random().toString()}
          style={styles.messagesList}
          contentContainerStyle={styles.messagesContent}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        />

        {/* Typing Indicator */}
        <TypingIndicator typingUsers={typingUsers} t={t} />
      </View>

      {/* Input Area */}
      <Surface style={styles.inputContainer}>
        <View style={styles.inputRow}>
          <TextInput
            style={styles.textInput}
            value={inputText}
            onChangeText={handleTyping}
            placeholder={t('chat.typeMessage')}
            multiline
            maxLength={1000}
          />
          <TouchableOpacity
            style={[
              styles.sendButton,
              inputText.trim() ? styles.sendButtonActive : styles.sendButtonInactive
            ]}
            onPress={sendMessage}
            disabled={!inputText.trim()}
          >
            <Text style={[
              styles.sendButtonText,
              inputText.trim() ? styles.sendButtonTextActive : styles.sendButtonTextInactive
            ]}>
              {t('chat.send')}
            </Text>
          </TouchableOpacity>
        </View>
      </Surface>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.surface,
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.onSurface,
  },
  header: {
    elevation: 2,
  },
  headerSubtitle: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  connectionDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: spacing.xs,
  },
  connectedDot: {
    backgroundColor: colors.success,
  },
  disconnectedDot: {
    backgroundColor: colors.error,
  },
  connectionText: {
    fontSize: 12,
    color: colors.onSurface,
  },
  messagesContainer: {
    flex: 1,
  },
  messagesList: {
    flex: 1,
    paddingHorizontal: spacing.md,
  },
  messagesContent: {
    paddingBottom: spacing.lg,
  },
  messageBubble: {
    marginVertical: spacing.xs,
    padding: spacing.md,
    borderRadius: 12,
    maxWidth: '80%',
  },
  currentUserBubble: {
    backgroundColor: colors.primary,
    alignSelf: 'flex-end',
    marginLeft: '20%',
  },
  otherUserBubble: {
    backgroundColor: colors.surfaceVariant,
    alignSelf: 'flex-start',
    marginRight: '20%',
    borderWidth: 1,
    borderColor: colors.outline,
  },
  senderName: {
    fontSize: typography.sizes.sm,
    color: colors.primary,
    marginBottom: spacing.xs,
    fontWeight: typography.weights.medium,
  },
  messageContent: {
    fontSize: typography.sizes.md,
    lineHeight: 20,
  },
  currentUserText: {
    color: colors.onPrimary,
  },
  otherUserText: {
    color: colors.onSurface,
  },
  imageMessage: {
    marginBottom: spacing.xs,
  },
  imageMessageText: {
    fontStyle: 'italic',
    marginBottom: spacing.xs,
  },
  messageFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.xs,
  },
  messageTime: {
    fontSize: typography.sizes.xs,
  },
  currentUserTime: {
    color: colors.onPrimary,
    opacity: 0.8,
  },
  otherUserTime: {
    color: colors.outline,
  },
  messageStatus: {
    marginLeft: spacing.sm,
  },
  readStatus: {
    color: colors.success,
    fontSize: typography.sizes.xs,
  },
  deliveredStatus: {
    color: colors.onPrimary,
    opacity: 0.6,
    fontSize: typography.sizes.xs,
  },
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  typingText: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    fontStyle: 'italic',
  },
  inputContainer: {
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.outline,
    elevation: 8,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: spacing.md,
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.outline,
    borderRadius: 20,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    marginRight: spacing.sm,
    maxHeight: 100,
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    backgroundColor: colors.surface,
  },
  sendButton: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 20,
    minWidth: 60,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonActive: {
    backgroundColor: colors.primary,
  },
  sendButtonInactive: {
    backgroundColor: colors.outline,
  },
  sendButtonText: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
  },
  sendButtonTextActive: {
    color: colors.onPrimary,
  },
  sendButtonTextInactive: {
    color: colors.surface,
  },
});