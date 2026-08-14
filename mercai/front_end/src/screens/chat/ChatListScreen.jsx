import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  Alert,
  ScrollView,
} from 'react-native';
import {
  Text,
  Appbar,
  Badge,
  Avatar,
  Surface,
  ActivityIndicator,
  Card,
} from 'react-native-paper';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { useSelector } from 'react-redux';
import { colors, spacing, typography } from '../../constants/theme.js';
import { chatService } from '../../services/chatService.js';
import { useTranslation } from '@i18n';

// Online User Item Component
const OnlineUserItem = ({ user, onPress }) => {
  return (
    <TouchableOpacity style={styles.onlineUserItem} onPress={() => onPress(user)}>
      <View style={styles.onlineUserAvatarContainer}>
        <Avatar.Text
          size={48}
          label={user.username?.charAt(0)?.toUpperCase() || 'U'}
          style={styles.onlineUserAvatar}
        />
        <View style={styles.onlineUserDot} />
      </View>
      <Text style={styles.onlineUserName} numberOfLines={1}>
        {user.username || 'User'}
      </Text>
    </TouchableOpacity>
  );
};

const ChatRoomItem = ({ room, currentUserId, onPress, t }) => {
  const isCustomer = room.customer_id === currentUserId;
  const otherUserName = isCustomer ? room.seller_name : room.customer_name;
  const otherUserId = isCustomer ? room.seller_id : room.customer_id;

  const formatLastMessageTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) return t('chat.justNow');
    if (diff < 3600000) return t('chat.minutesAgo', { count: Math.floor(diff / 60000) });
    if (diff < 86400000) return t('chat.hoursAgo', { count: Math.floor(diff / 3600000) });

    return date.toLocaleDateString();
  };

  return (
    <Card style={styles.chatRoomItem}>
      <TouchableOpacity onPress={() => onPress(room)}>
        <View style={styles.chatRoomContent}>
          {/* Avatar */}
          <View style={styles.avatarContainer}>
            <Avatar.Text size={48} label={otherUserName?.charAt(0) || 'U'} style={styles.avatar} />
            {room.is_online && (
              <View style={styles.onlineIndicator} />
            )}
          </View>

          {/* Chat Info */}
          <View style={styles.chatInfo}>
            <View style={styles.chatHeader}>
              <Text style={styles.chatTitle}>
                {otherUserName || t('chat.unknownUser')}
              </Text>
              {room.last_message_at && (
                <Text style={styles.lastMessageTime}>
                  {formatLastMessageTime(room.last_message_at)}
                </Text>
              )}
            </View>
            <View style={styles.chatSubtitle}>
              <Text style={styles.lastMessage}>
                {room.last_message || t('chat.noMessagesYet')}
              </Text>
              {room.product_title && (
                <Text style={styles.productTitle}>
                  📦 {room.product_title}
                </Text>
              )}
            </View>
          </View>

          {/* Unread Badge */}
          {room.unread_count > 0 && (
            <View style={styles.unreadBadgeContainer}>
              <Badge style={styles.unreadBadge}>
                {room.unread_count > 99 ? '99+' : room.unread_count}
              </Badge>
            </View>
          )}
        </View>
      </TouchableOpacity>
    </Card>
  );
};

export const ChatListScreen = () => {
  const navigation = useNavigation();
  const t = useTranslation();
  const currentUser = useSelector((state) => state.auth.user);
  
  // State
  const [chatRooms, setChatRooms] = useState([]);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  
  // Load online users
  const loadOnlineUsers = useCallback(async () => {
    if (!currentUser) return;

    try {
      const data = await chatService.getOnlineUsers();
      // Filter out current user from online users list
      const filteredUsers = (data.online_users || []).filter(
        user => user.user_id !== currentUser.id
      );
      setOnlineUsers(filteredUsers);
    } catch (error) {
      console.log('Error loading online users:', error);
      // Silently fail - online users is not critical
    }
  }, [currentUser]);

  // Load chat rooms
  const loadChatRooms = useCallback(async (showRefreshing = false) => {
    if (!currentUser) return;

    try {
      if (showRefreshing) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }

      const [rooms] = await Promise.all([
        chatService.getChatRooms(),
        loadOnlineUsers(),
      ]);
      setChatRooms(rooms);

    } catch (error) {
      console.error('Error loading chat rooms', error);
      Alert.alert(t('common.error'), t('chat.loadError'));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [currentUser, loadOnlineUsers]);
  
  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((wsMessage) => {
    switch (wsMessage.type) {
      case 'new_message':
        // Update chat room list when new message arrives
        const newMessage = wsMessage.data;
        setChatRooms(prev => prev.map(room => {
          if (room.id === newMessage.chat_room_id) {
            return {
              ...room,
              last_message: newMessage.message,
              last_message_at: newMessage.created_at,
              unread_count: newMessage.sender_id !== currentUser?.id 
                ? room.unread_count + 1 : room.unread_count
            };
          }
          return room;
        }));
        break;
        
      case 'messages_read':
        // Update read status
        const readData = wsMessage.data;
        if (readData.reader_id === currentUser?.id) {
          setChatRooms(prev => prev.map(room => 
            room.id === readData.chat_room_id 
              ? { ...room, unread_count: 0 } : room
          ));
        }
        break;
    }
  }, [currentUser]);
  
  // Initialize connection and load data
  useEffect(() => {
    if (!currentUser) return;
    
    const initialize = async () => {
      try {
        // Connect to WebSocket
        await chatService.connect(currentUser.id);
        
        // Setup listeners
        const unsubscribeMessage = chatService.addMessageListener(handleWebSocketMessage);
        const unsubscribeConnection = chatService.addConnectionListener(setIsConnected);
        
        // Load initial data
        await loadChatRooms();
        
        // Cleanup function
        return () => {
          unsubscribeMessage();
          unsubscribeConnection();
        };
      } catch (error) {
        console.error('Error initializing chat list', error);
        setIsLoading(false);
      }
    };
    
    initialize();
  }, [currentUser, handleWebSocketMessage, loadChatRooms]);
  
  // Refresh data when screen is focused
  useFocusEffect(
    useCallback(() => {
      if (currentUser) {
        loadChatRooms();
      }
    }, [currentUser, loadChatRooms])
  );
  
  // Handle chat room press
  const handleChatRoomPress = useCallback((room) => {
    const isCustomer = room.customer_id === currentUser?.id;
    const otherUserName = isCustomer ? room.seller_name : room.customer_name;
    const otherUserId = isCustomer ? room.seller_id : room.customer_id;

    navigation.navigate('ChatScreen', {
      conversationId: room.id,
      recipientName: otherUserName,
      recipientId: otherUserId,
    });
  }, [navigation, currentUser]);

  // Handle online user press
  const handleOnlineUserPress = useCallback((user) => {
    // Check if there's an existing chat room with this user
    const existingRoom = chatRooms.find(room =>
      room.customer_id === user.user_id || room.seller_id === user.user_id
    );

    if (existingRoom) {
      handleChatRoomPress(existingRoom);
    } else {
      // Navigate to chat with this user (will create room if needed)
      navigation.navigate('ChatScreen', {
        recipientId: user.user_id,
        recipientName: user.username,
      });
    }
  }, [chatRooms, handleChatRoomPress, navigation]);

  // Pull to refresh
  const handleRefresh = useCallback(() => {
    loadChatRooms(true);
  }, [loadChatRooms]);
  
  // Render chat room item
  const renderChatRoom = ({ item }) => (
    <ChatRoomItem
      room={item}
      currentUserId={currentUser?.id}
      onPress={handleChatRoomPress}
      t={t}
    />
  );
  
  // Calculate total unread count
  const totalUnreadCount = chatRooms.reduce((sum, room) => sum + room.unread_count, 0);
  
  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>{t('chat.loadingConversations')}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.Content
          title={t('chat.messages')}
          subtitle={
            <View style={styles.headerSubtitle}>
              <View style={[styles.connectionDot, isConnected ? styles.connectedDot : styles.disconnectedDot]} />
              <Text style={styles.connectionText}>
                {isConnected ? t('chat.connected') : t('chat.reconnecting')}
              </Text>
            </View>
          }
        />
        {totalUnreadCount > 0 && (
          <Appbar.Action
            icon={() => (
              <Badge style={styles.headerBadge}>
                {totalUnreadCount > 99 ? '99+' : totalUnreadCount}
              </Badge>
            )}
            onPress={() => {}}
          />
        )}
      </Appbar.Header>

      <View style={styles.content}>
        {/* Online Users Section */}
        {onlineUsers.length > 0 && (
          <View style={styles.onlineUsersSection}>
            <Text style={styles.onlineUsersSectionTitle}>
              {t('chat.onlineNow') || 'Online Now'} ({onlineUsers.length})
            </Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.onlineUsersScroll}
            >
              {onlineUsers.map(user => (
                <OnlineUserItem
                  key={user.user_id}
                  user={user}
                  onPress={handleOnlineUserPress}
                />
              ))}
            </ScrollView>
          </View>
        )}

        {chatRooms.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyTitle}>{t('chat.noConversations')}</Text>
            <Text style={styles.emptySubtitle}>
              {t('chat.noConversationsMessage')}
            </Text>
          </View>
        ) : (
          <FlatList
            data={chatRooms}
            renderItem={renderChatRoom}
            keyExtractor={item => item.id.toString()}
            refreshControl={
              <RefreshControl
                refreshing={isRefreshing}
                onRefresh={handleRefresh}
              />
            }
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.listContent}
          />
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
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
  headerBadge: {
    backgroundColor: colors.primary,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.onSurface,
  },
  content: {
    flex: 1,
  },
  listContent: {
    paddingBottom: spacing.lg,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  emptyTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    lineHeight: 20,
  },
  chatRoomItem: {
    marginHorizontal: spacing.md,
    marginBottom: spacing.sm,
    borderRadius: 8,
    elevation: 1,
  },
  chatRoomContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
  },
  avatarContainer: {
    position: 'relative',
  },
  avatar: {
    backgroundColor: colors.primaryContainer,
  },
  onlineIndicator: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.success,
    borderWidth: 2,
    borderColor: colors.surface,
  },
  chatInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  chatHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  chatTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    flex: 1,
    marginRight: spacing.sm,
  },
  lastMessageTime: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  chatSubtitle: {
    marginBottom: spacing.xs,
  },
  lastMessage: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    lineHeight: 18,
  },
  productTitle: {
    fontSize: typography.sizes.xs,
    color: colors.primary,
    fontStyle: 'italic',
  },
  unreadBadgeContainer: {
    marginLeft: spacing.sm,
  },
  unreadBadge: {
    backgroundColor: colors.primary,
  },
  // Online Users Section Styles
  onlineUsersSection: {
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline + '30',
  },
  onlineUsersSectionTitle: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginLeft: spacing.md,
    marginBottom: spacing.sm,
  },
  onlineUsersScroll: {
    paddingHorizontal: spacing.md,
  },
  onlineUserItem: {
    alignItems: 'center',
    marginRight: spacing.md,
    width: 64,
  },
  onlineUserAvatarContainer: {
    position: 'relative',
  },
  onlineUserAvatar: {
    backgroundColor: colors.primaryContainer,
  },
  onlineUserDot: {
    position: 'absolute',
    bottom: 2,
    right: 2,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.success,
    borderWidth: 2,
    borderColor: colors.surface,
  },
  onlineUserName: {
    fontSize: typography.sizes.xs,
    color: colors.onSurface,
    marginTop: spacing.xs,
    textAlign: 'center',
  },
});