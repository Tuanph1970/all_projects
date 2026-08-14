/**
 * VideoUploadProgress Component
 * Displays upload progress with percentage and status
 */
import React from 'react';
import { View, StyleSheet, Animated } from 'react-native';
import { Text, ProgressBar, ActivityIndicator } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing } from '../../constants/theme';

const VideoUploadProgress = ({ progress, isUploading, error, success }) => {
  // progress: 0-100 number
  // isUploading: boolean
  // error: string | null
  // success: boolean

  const getStatusIcon = () => {
    if (isUploading) {
      return (
        <ActivityIndicator size="small" color={colors.primary} />
      );
    }
    if (error) {
      return (
        <Icon name="error" size={24} color={colors.error} />
      );
    }
    if (success) {
      return (
        <Icon name="check-circle" size={24} color={colors.success} />
      );
    }
    return null;
  };

  const getStatusText = () => {
    if (isUploading) {
      return `Uploading... ${Math.round(progress)}%`;
    }
    if (error) {
      return error;
    }
    if (success) {
      return 'Upload complete!';
    }
    return '';
  };

  const getStatusColor = () => {
    if (error) return colors.error;
    if (success) return colors.success;
    return colors.primary;
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.iconContainer}>
          {getStatusIcon()}
        </View>
        <Text style={[styles.statusText, { color: getStatusColor() }]}>
          {getStatusText()}
        </Text>
      </View>

      {isUploading && (
        <View style={styles.progressContainer}>
          <ProgressBar
            progress={progress / 100}
            color={colors.primary}
            style={styles.progressBar}
          />
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: spacing.medium,
    padding: spacing.medium,
    backgroundColor: colors.background,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.small,
  },
  iconContainer: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.white,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statusText: {
    flex: 1,
    fontSize: 14,
    fontWeight: '500',
  },
  progressContainer: {
    marginTop: spacing.small,
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.border,
  },
});

export default VideoUploadProgress;
