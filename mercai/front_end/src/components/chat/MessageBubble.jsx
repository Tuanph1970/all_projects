import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Image,
  Dimensions,
  Animated,
} from 'react-native';
import {
  Text,
  Modal,
  Portal,
  IconButton,
  Surface,
} from 'react-native-paper';
import { colors, spacing, typography } from '../../constants/theme.js';

const screenWidth = Dimensions.get('window').width;

export const MessageBubble = ({
  message,
  isCurrentUser,
  showSenderName = false,
  showTimeStamp = true,
  onImagePress,
  onLongPress,
}) => {
  const [imageModalVisible, setImageModalVisible] = useState(false);
  const [scaleAnim] = useState(new Animated.Value(1));

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 24 * 60 * 60 * 1000) {
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      });
    }
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleImagePress = () => {
    if (message.image_url) {
      if (onImagePress) {
        onImagePress(message.image_url);
      } else {
        setImageModalVisible(true);
      }
    }
  };

  const handleLongPress = () => {
    Animated.sequence([
      Animated.timing(scaleAnim, {
        toValue: 0.95,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 1,
        duration: 100,
        useNativeDriver: true,
      }),
    ]).start();

    onLongPress?.(message);
  };

  const getMessageStatus = () => {
    if (!isCurrentUser) return null;
    
    if (message.is_read) {
      return (
        <Text style={styles.readStatus}>
          ✓✓
        </Text>
      );
    } else if (message.id) {
      return (
        <Text style={styles.deliveredStatus}>
          ✓
        </Text>
      );
    } else {
      return (
        <Text style={styles.sendingStatus}>
          ●
        </Text>
      );
    }
  };

  const isSystemMessage = message.message_type === 'system';

  if (isSystemMessage) {
    return (
      <View style={styles.systemMessageContainer}>
        <Text style={styles.systemMessageText}>{message.content}</Text>
        {showTimeStamp && (
          <Text style={styles.systemMessageTime}>
            {formatTime(message.created_at)}
          </Text>
        )}
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Animated.View style={[{ transform: [{ scale: scaleAnim }] }]}>
        <TouchableOpacity
          style={[
            styles.messageBubble,
            isCurrentUser ? styles.currentUserBubble : styles.otherUserBubble,
          ]}
          onLongPress={handleLongPress}
          delayLongPress={500}
          activeOpacity={0.7}
        >
          {showSenderName && !isCurrentUser && (
            <Text style={styles.senderName}>
              {message.sender_name || 'Unknown User'}
            </Text>
          )}

          {message.message_type === 'image' && message.image_url ? (
            <View style={styles.imageMessageContainer}>
              <TouchableOpacity onPress={handleImagePress}>
                <Image
                  source={{ uri: message.image_url }}
                  style={styles.messageImage}
                  resizeMode="cover"
                />
                <View style={styles.imageOverlay}>
                  <Text style={styles.imageOverlayText}>📷</Text>
                </View>
              </TouchableOpacity>
              {message.content && message.content !== 'Shared an image' && (
                <Text style={[
                  styles.messageContent,
                  isCurrentUser ? styles.currentUserText : styles.otherUserText,
                ]}>
                  {message.content}
                </Text>
              )}
            </View>
          ) : (
            <Text style={[
              styles.messageContent,
              isCurrentUser ? styles.currentUserText : styles.otherUserText,
            ]}>
              {message.content}
            </Text>
          )}

          {showTimeStamp && (
            <View style={styles.messageFooter}>
              <Text style={[
                styles.messageTime,
                isCurrentUser ? styles.currentUserTime : styles.otherUserTime,
              ]}>
                {formatTime(message.created_at)}
              </Text>
              <View style={styles.messageStatus}>
                {getMessageStatus()}
              </View>
            </View>
          )}
        </TouchableOpacity>
      </Animated.View>

      <Portal>
        <Modal
          visible={imageModalVisible}
          onDismiss={() => setImageModalVisible(false)}
          contentContainerStyle={styles.imageModal}
        >
          <View style={styles.imageModalContainer}>
            <View style={styles.imageModalHeader}>
              <Text style={styles.imageModalTitle}>
                {message.sender_name || 'Image'}
              </Text>
              <Text style={styles.imageModalDate}>
                {formatDate(message.created_at)}
              </Text>
              <IconButton
                icon="close"
                onPress={() => setImageModalVisible(false)}
                style={styles.closeButton}
              />
            </View>
            {message.image_url && (
              <Image
                source={{ uri: message.image_url }}
                style={styles.fullScreenImage}
                resizeMode="contain"
              />
            )}
            {message.content && message.content !== 'Shared an image' && (
              <View style={styles.imageCaption}>
                <Text style={styles.imageCaptionText}>
                  {message.content}
                </Text>
              </View>
            )}
          </View>
        </Modal>
      </Portal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: spacing.xs,
  },
  messageBubble: {
    marginVertical: spacing.xs,
    padding: spacing.md,
    borderRadius: 16,
  },
  currentUserBubble: {
    backgroundColor: colors.primary,
    marginLeft: screenWidth * 0.2,
    alignSelf: 'flex-end',
  },
  otherUserBubble: {
    backgroundColor: colors.surface,
    marginRight: screenWidth * 0.2,
    borderWidth: 1,
    borderColor: colors.outline,
    alignSelf: 'flex-start',
  },
  systemMessageContainer: {
    marginVertical: spacing.sm,
    paddingHorizontal: spacing.xl,
  },
  systemMessageText: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    textAlign: 'center',
    fontStyle: 'italic',
    backgroundColor: colors.surfaceVariant,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 16,
    overflow: 'hidden',
  },
  systemMessageTime: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    textAlign: 'center',
    marginTop: spacing.xs,
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
  imageMessageContainer: {
    overflow: 'hidden',
  },
  messageImage: {
    width: 200,
    height: 150,
    borderRadius: 12,
    backgroundColor: colors.surfaceVariant,
  },
  imageOverlay: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    borderRadius: 12,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  imageOverlayText: {
    color: colors.onPrimary,
    fontSize: typography.sizes.sm,
  },
  messageFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.sm,
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
    minWidth: 20,
    alignItems: 'flex-end',
  },
  readStatus: {
    color: colors.primary,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.bold,
  },
  deliveredStatus: {
    color: colors.outline,
    opacity: 0.8,
    fontSize: typography.sizes.xs,
  },
  sendingStatus: {
    color: colors.outline,
    opacity: 0.6,
    fontSize: typography.sizes.xs,
  },
  imageModal: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
  },
  imageModalContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  imageModalHeader: {
    position: 'absolute',
    top: 50,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    zIndex: 1,
  },
  imageModalTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onPrimary,
    flex: 1,
  },
  imageModalDate: {
    fontSize: typography.sizes.sm,
    color: colors.onPrimary,
    opacity: 0.8,
    marginRight: spacing.md,
  },
  closeButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  fullScreenImage: {
    width: screenWidth,
    height: 300,
    backgroundColor: colors.surface,
  },
  imageCaption: {
    position: 'absolute',
    bottom: 50,
    left: spacing.md,
    right: spacing.md,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    borderRadius: 12,
    padding: spacing.md,
  },
  imageCaptionText: {
    fontSize: typography.sizes.md,
    color: colors.onPrimary,
    textAlign: 'center',
  },
});