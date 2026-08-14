/**
 * VideoPicker Component
 * Allows users to record video from camera or pick from gallery
 */
import React, { useState } from 'react';
import { View, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { Text, Button, ActivityIndicator } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import ImagePicker from 'react-native-image-crop-picker';
import { colors, spacing } from '../../constants/theme';
import { useTranslation } from '@i18n';

const VideoPicker = ({ onVideoSelect, maxDuration = 60 }) => {
  const t = useTranslation();
  const [isRecording, setIsRecording] = useState(false);

  /**
   * Record video from camera
   */
  const recordVideo = async () => {
    try {
      setIsRecording(true);
      
      const video = await ImagePicker.openCamera({
        mediaType: 'video',
        maxDuration: maxDuration,
        quality: 0.8,
        compressVideoPreset: 'MediumQuality',
      });

      if (video) {
        onVideoSelect(video);
      }
    } catch (error) {
      if (error.code !== 'E_PICKER_CANCELLED') {
        console.error('Error recording video:', error);
        
        // Handle permission errors
        if (error.code === 'E_PERMISSION_DENIED') {
          Alert.alert(
            t('video.permissionRequired'),
            t('video.cameraPermission'),
            [{ text: 'OK' }]
          );
        } else {
          Alert.alert(
            t('video.error'),
            t('video.recordingFailed')
          );
        }
      }
    } finally {
      setIsRecording(false);
    }
  };

  /**
   * Pick video from gallery
   */
  const pickFromGallery = async () => {
    try {
      const video = await ImagePicker.openPicker({
        mediaType: 'video',
        selectionLimit: 1,
        maxDuration: maxDuration,
      });

      if (video) {
        onVideoSelect(video);
      }
    } catch (error) {
      if (error.code !== 'E_PICKER_CANCELLED') {
        console.error('Error picking video:', error);
        Alert.alert(
          t('video.error'),
          t('video.pickFailed')
        );
      }
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{t('video.addVideo')}</Text>
      
      <View style={styles.buttonContainer}>
        <Button
          mode="outlined"
          onPress={recordVideo}
          disabled={isRecording}
          style={[styles.button, styles.recordButton]}
          contentStyle={styles.buttonContent}
          icon={({ size, color }) => (
            <Icon name="videocam" size={size} color={color} />
          )}
        >
          {isRecording ? (
            <ActivityIndicator size="small" color={colors.primary} />
          ) : (
            t('video.recordVideo')
          )}
        </Button>

        <Button
          mode="outlined"
          onPress={pickFromGallery}
          disabled={isRecording}
          style={[styles.button, styles.galleryButton]}
          contentStyle={styles.buttonContent}
          icon={({ size, color }) => (
            <Icon name="video-library" size={size} color={color} />
          )}
        >
          {t('video.chooseVideo')}
        </Button>
      </View>

      <Text style={styles.hint}>
        {t('video.maxDuration')}: {maxDuration}s | {t('video.maxSize')}: 50MB
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: spacing.medium,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: spacing.small,
    color: colors.text,
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: spacing.small,
    marginBottom: spacing.small,
  },
  button: {
    flex: 1,
    borderColor: colors.primary,
  },
  buttonContent: {
    paddingVertical: spacing.small,
  },
  recordButton: {
    backgroundColor: colors.primary + '10',
  },
  galleryButton: {
    backgroundColor: colors.secondary + '10',
  },
  hint: {
    fontSize: 12,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: spacing.xsmall,
  },
});

export default VideoPicker;
