/**
 * VideoPreview Component
 * Displays video preview with playback controls and remove option
 */
import React from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { Text } from 'react-native-paper';
import { ResizeMode, Video } from 'expo-av';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing } from '../../constants/theme';

const VideoPreview = ({ videoUri, duration, fileSize, onRemove }) => {
  const videoRef = React.useRef(null);

  const formatDuration = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (mb) => {
    if (!mb) return '';
    return `${mb.toFixed(1)} MB`;
  };

  return (
    <View style={styles.container}>
      <View style={styles.videoWrapper}>
        <Video
          ref={videoRef}
          source={{ uri: videoUri }}
          style={styles.video}
          useNativeControls
          resizeMode={ResizeMode.COVER}
          isLooping
          shouldPlay={false}
        />
        
        {/* Remove button overlay */}
        <TouchableOpacity 
          style={styles.removeButton} 
          onPress={onRemove}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Icon name="close-circle" size={32} color={colors.error} />
        </TouchableOpacity>
      </View>

      {/* Video info */}
      <View style={styles.infoContainer}>
        <View style={styles.infoRow}>
          <Icon name="access-time" size={16} color={colors.textSecondary} />
          <Text style={styles.infoText}>
            {formatDuration(duration)}
          </Text>
        </View>
        
        <View style={styles.infoRow}>
          <Icon name="folder" size={16} color={colors.textSecondary} />
          <Text style={styles.infoText}>
            {formatFileSize(fileSize)}
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: spacing.medium,
  },
  videoWrapper: {
    position: 'relative',
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: colors.background,
    aspectRatio: 16 / 9,
  },
  video: {
    width: '100%',
    height: '100%',
  },
  removeButton: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 20,
    padding: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 5,
  },
  infoContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.small,
    paddingHorizontal: spacing.xsmall,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xsmall,
  },
  infoText: {
    fontSize: 12,
    color: colors.textSecondary,
  },
});

export default VideoPreview;
