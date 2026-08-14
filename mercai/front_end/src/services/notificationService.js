import { Platform, Alert, Linking } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Note: Push notification packages need to be properly configured
// For now, using mock implementation to prevent compilation errors
const PushNotification = {
  configure: (config) => console.log('PushNotification configured'),
  createChannel: (config, callback) => callback(true),
  localNotification: (config) => console.log('Local notification:', config),
  cancelAllLocalNotifications: () => console.log('All notifications cancelled'),
  cancelLocalNotifications: (config) => console.log('Notification cancelled:', config),
};

const PushNotificationIOS = {
  requestPermissions: (config) => Promise.resolve(config),
  removeAllDeliveredNotifications: () => console.log('iOS notifications removed'),
  setApplicationIconBadgeNumber: (count) => console.log('Badge count:', count),
  checkPermissions: () => Promise.resolve({ alert: true, badge: true, sound: true }),
  finish: () => console.log('iOS notification finished'),
  FetchResult: {
    NoData: 'NoData',
  },
};

const Importance = {
  HIGH: 'high',
  DEFAULT: 'default',
  LOW: 'low',
};

class NotificationService {
  isInitialized = false;
  listeners = [];

  async initialize() {
    if (this.isInitialized) return;

    try {
      // Configure push notifications
      PushNotification.configure({
        // Called when Token is generated (iOS and Android)
        onRegister: (token) => {
          console.log('FCM Token:', token);
          this.saveFCMToken(token.token);
        },

        // Called when a remote is received or opened, or local notification is opened
        onNotification: (notification) => {
          console.log('Notification received:', notification);
          this.handleNotification(notification);

          // Required on iOS only
          if (Platform.OS === 'ios') {
            notification.finish(PushNotificationIOS.FetchResult.NoData);
          }
        },

        // Called when Registered Action is pressed and invokeApp is false, if true onNotification will be called
        onAction: (notification) => {
          console.log('Notification action:', notification.action);
        },

        // Should the initial notification be popped automatically
        popInitialNotification: true,

        // Permissions
        permissions: {
          alert: true,
          badge: true,
          sound: true,
        },

        // Should the registration be requested on launch
        requestPermissions: Platform.OS === 'ios',
      });

      // Create notification channels (Android)
      if (Platform.OS === 'android') {
        this.createNotificationChannels();
      }

      // Request permissions
      await this.requestPermissions();

      this.isInitialized = true;
      console.log('Notification service initialized');
    } catch (error) {
      console.error('Error initializing notification service:', error);
    }
  }

  createNotificationChannels() {
    // Chat messages channel
    PushNotification.createChannel(
      {
        channelId: 'chat-messages',
        channelName: 'Chat Messages',
        channelDescription: 'Notifications for new chat messages',
        importance: Importance.HIGH,
        vibrate: true,
        playSound: true,
        soundName: 'default',
      },
      (created) => console.log(`Chat channel created: ${created}`)
    );

    // Order updates channel
    PushNotification.createChannel(
      {
        channelId: 'order-updates',
        channelName: 'Order Updates',
        channelDescription: 'Notifications for order status changes',
        importance: Importance.HIGH,
        vibrate: true,
        playSound: true,
        soundName: 'default',
      },
      (created) => console.log(`Order channel created: ${created}`)
    );

    // General notifications channel
    PushNotification.createChannel(
      {
        channelId: 'general',
        channelName: 'General',
        channelDescription: 'General app notifications',
        importance: Importance.DEFAULT,
        vibrate: true,
        playSound: true,
      },
      (created) => console.log(`General channel created: ${created}`)
    );
  }

  async requestPermissions() {
    try {
      if (Platform.OS === 'ios') {
        const permissions = await PushNotificationIOS.requestPermissions({
          alert: true,
          badge: true,
          sound: true,
        });
        return permissions.alert && permissions.badge && permissions.sound;
      } else {
        // Android permissions are handled in the configure method
        return true;
      }
    } catch (error) {
      console.error('Error requesting notification permissions:', error);
      return false;
    }
  }

  async saveFCMToken(token) {
    try {
      await AsyncStorage.setItem('fcm_token', token);
      // TODO: Send token to backend server
    } catch (error) {
      console.error('Error saving FCM token:', error);
    }
  }

  async getFCMToken() {
    try {
      return await AsyncStorage.getItem('fcm_token');
    } catch (error) {
      console.error('Error getting FCM token:', error);
      return null;
    }
  }

  handleNotification(notification) {
    // Notify listeners
    this.listeners.forEach(listener => {
      try {
        listener(notification);
      } catch (error) {
        console.error('Error in notification listener:', error);
      }
    });
  }

  // Show local notification for new chat message
  showChatNotification(chatNotification) {
    if (!this.isInitialized) {
      console.warn('Notification service not initialized');
      return;
    }

    const title = chatNotification.senderName || 'New Message';
    const message = chatNotification.productTitle 
      ? `${chatNotification.content} (${chatNotification.productTitle})`
      : chatNotification.content;

    PushNotification.localNotification({
      channelId: 'chat-messages',
      title,
      message,
      userInfo: {
        chatRoomId: chatNotification.chatRoomId,
        senderId: chatNotification.senderId,
      },
      actions: ['Reply', 'Mark as Read'],
      invokeApp: false,
      priority: 'high',
      importance: Importance.HIGH,
      vibrate: true,
      playSound: true,
      soundName: 'default',
    });
  }

  // Show local notification for order updates
  showOrderNotification(title, message, orderId) {
    if (!this.isInitialized) {
      console.warn('Notification service not initialized');
      return;
    }

    PushNotification.localNotification({
      channelId: 'order-updates',
      title,
      message,
      userInfo: {
        orderId,
      },
      invokeApp: true,
      priority: 'high',
      importance: Importance.HIGH,
      vibrate: true,
      playSound: true,
      soundName: 'default',
    });
  }

  // Show general notification
  showGeneralNotification(title, message, data = null) {
    if (!this.isInitialized) {
      console.warn('Notification service not initialized');
      return;
    }

    PushNotification.localNotification({
      channelId: 'general',
      title,
      message,
      userInfo: {
        ...data,
      },
      invokeApp: true,
      priority: 'default',
      importance: Importance.DEFAULT,
      vibrate: true,
      playSound: true,
    });
  }

  // Clear all notifications
  clearAllNotifications() {
    PushNotification.cancelAllLocalNotifications();
    
    if (Platform.OS === 'ios') {
      PushNotificationIOS.removeAllDeliveredNotifications();
      PushNotificationIOS.setApplicationIconBadgeNumber(0);
    }
  }

  // Clear specific notification
  clearNotification(notificationId) {
    PushNotification.cancelLocalNotifications({ id: notificationId });
  }

  // Set badge count (iOS only)
  setBadgeCount(count) {
    if (Platform.OS === 'ios') {
      PushNotificationIOS.setApplicationIconBadgeNumber(count);
    }
  }

  // Add notification listener
  addNotificationListener(callback) {
    this.listeners.push(callback);
    
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(callback);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  // Check notification permissions
  async checkPermissions() {
    if (Platform.OS === 'ios') {
      return await PushNotificationIOS.checkPermissions();
    } else {
      // For Android, assume permissions are granted if service is initialized
      return {
        alert: true,
        badge: true,
        sound: true,
      };
    }
  }

  // Request permissions with user-friendly dialog
  async requestPermissionsWithDialog() {
    try {
      const permissions = await this.checkPermissions();
      
      if (!permissions.alert || !permissions.badge || !permissions.sound) {
        Alert.alert(
          'Enable Notifications',
          'Turn on notifications to stay updated with new messages and order updates.',
          [
            { text: 'Not Now', style: 'cancel' },
            {
              text: 'Enable',
              onPress: async () => {
                if (Platform.OS === 'ios') {
                  await this.requestPermissions();
                } else {
                  Linking.openSettings();
                }
              },
            },
          ]
        );
        return false;
      }
      
      return true;
    } catch (error) {
      console.error('Error checking permissions:', error);
      return false;
    }
  }

  // Check if notifications are enabled
  async areNotificationsEnabled() {
    try {
      const permissions = await this.checkPermissions();
      return permissions.alert && permissions.badge;
    } catch (error) {
      console.error('Error checking notification status:', error);
      return false;
    }
  }

  // Cleanup
  cleanup() {
    this.listeners = [];
    this.clearAllNotifications();
  }
}

// Export singleton instance
export const notificationService = new NotificationService();