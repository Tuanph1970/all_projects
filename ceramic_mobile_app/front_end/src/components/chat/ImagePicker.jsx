import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  Alert,
  Linking,
  Platform,
} from 'react-native';
import {
  Text,
  Button,
  Modal,
  Portal,
  IconButton,
  Surface,
} from 'react-native-paper';
import { colors, spacing, typography } from '../../constants/theme.js';

export const ImagePicker = ({
  visible,
  onDismiss,
  onImageSelected,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const requestCameraPermission = async () => {
    try {
      const permission = Platform.OS === 'ios' 
        ? 'ios.permission.CAMERA'
        : 'android.permission.CAMERA';
      
      const result = 'granted';
      
      if (result === 'granted') {
        return true;
      } else if (result === 'denied') {
        Alert.alert(
          'Camera Permission Required',
          'Please grant camera permission to take photos.',
          [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Open Settings', onPress: () => Linking.openSettings() },
          ]
        );
      }
      
      return false;
    } catch (error) {
      console.error('Error requesting camera permission:', error);
      return false;
    }
  };

  const requestGalleryPermission = async () => {
    try {
      const permission = Platform.OS === 'ios' 
        ? 'ios.permission.PHOTO_LIBRARY'
        : 'android.permission.READ_EXTERNAL_STORAGE';
      
      const result = 'granted';
      
      if (result === 'granted') {
        return true;
      } else if (result === 'denied') {
        Alert.alert(
          'Gallery Permission Required',
          'Please grant gallery permission to select photos.',
          [
            { text: 'Cancel', style: 'cancel' },
            { text: 'Open Settings', onPress: () => Linking.openSettings() },
          ]
        );
      }
      
      return false;
    } catch (error) {
      console.error('Error requesting gallery permission:', error);
      return false;
    }
  };

  const handleImagePicker = (response) => {
    setIsLoading(false);

    if (response.didCancel || response.errorCode) {
      return;
    }

    const asset = response.assets?.[0];
    if (asset?.uri) {
      const maxSize = 10 * 1024 * 1024;
      if (asset.fileSize && asset.fileSize > maxSize) {
        Alert.alert(
          'File Too Large',
          'Please select an image smaller than 10MB.'
        );
        return;
      }

      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
      if (asset.type && !validTypes.includes(asset.type)) {
        Alert.alert(
          'Invalid File Type',
          'Please select a JPEG, PNG, or GIF image.'
        );
        return;
      }

      onImageSelected(asset.uri, asset.type || 'image/jpeg');
      onDismiss();
    }
  };

  const takePhoto = async () => {
    const hasPermission = await requestCameraPermission();
    if (!hasPermission) return;

    setIsLoading(true);

    const options = {
      mediaType: 'photo',
      quality: 0.8,
      maxWidth: 1920,
      maxHeight: 1080,
      includeBase64: false,
    };

    try {
      const mockResponse = {
        assets: [{
          uri: 'mock://camera-photo.jpg',
          type: 'image/jpeg'
        }]
      };
      handleImagePicker(mockResponse);
    } catch (error) {
      console.error('Camera error:', error);
      setIsLoading(false);
    }
  };

  const selectFromGallery = async () => {
    const hasPermission = await requestGalleryPermission();
    if (!hasPermission) return;

    setIsLoading(true);

    const options = {
      mediaType: 'photo',
      quality: 0.8,
      maxWidth: 1920,
      maxHeight: 1080,
      includeBase64: false,
      selectionLimit: 1,
    };

    try {
      const mockResponse = {
        assets: [{
          uri: 'mock://gallery-photo.jpg',
          type: 'image/jpeg'
        }]
      };
      handleImagePicker(mockResponse);
    } catch (error) {
      console.error('Gallery error:', error);
      setIsLoading(false);
    }
  };

  return (
    <Portal>
      <Modal visible={visible} onDismiss={onDismiss} style={styles.modal}>
        <Surface style={styles.container}>
          <View style={styles.header}>
            <Text style={styles.title}>Add Photo</Text>
            <IconButton icon="close" onPress={onDismiss} style={styles.closeButton} />
          </View>

          <View style={styles.content}>
            <Text style={styles.subtitle}>
              Share a photo with your message
            </Text>

            <View style={styles.options}>
              <Button
                mode="contained"
                onPress={takePhoto}
                style={styles.option}
                contentStyle={styles.optionContent}
                disabled={isLoading}
              >
                Take Photo
              </Button>

              <Button
                mode="contained"
                onPress={selectFromGallery}
                style={styles.option}
                contentStyle={styles.optionContent}
                disabled={isLoading}
              >
                Choose from Gallery
              </Button>
            </View>

            {isLoading && (
              <View style={styles.loadingContainer}>
                <Text style={styles.loadingText}>Loading...</Text>
              </View>
            )}
          </View>
        </Surface>
      </Modal>
    </Portal>
  );
};

const styles = StyleSheet.create({
  modal: {
    justifyContent: 'flex-end',
  },
  container: {
    margin: spacing.md,
    borderRadius: 12,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline,
  },
  title: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  closeButton: {
    margin: 0,
  },
  content: {
    padding: spacing.md,
  },
  subtitle: {
    fontSize: typography.sizes.md,
    color: colors.onSurfaceVariant,
    marginBottom: spacing.lg,
    textAlign: 'center',
  },
  options: {
    gap: spacing.md,
  },
  option: {
    backgroundColor: colors.primary,
  },
  optionContent: {
    height: 48,
  },
  loadingContainer: {
    marginTop: spacing.md,
    alignItems: 'center',
  },
  loadingText: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
  },
});