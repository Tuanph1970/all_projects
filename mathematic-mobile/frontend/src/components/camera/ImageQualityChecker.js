import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

/**
 * ImageQualityChecker Component
 * Displays quality feedback for captured images
 */
const ImageQualityChecker = ({ quality, onRetake, onUseAnyway }) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);

  const getQualityInfo = () => {
    if (quality >= 0.8) {
      return {
        icon: 'checkmark-circle',
        title: 'Excellent Quality',
        message: 'Image is clear and ready to process',
        color: colors.success,
      };
    } else if (quality >= 0.6) {
      return {
        icon: 'information-circle',
        title: 'Good Quality',
        message: 'Image quality is acceptable',
        color: colors.warning,
      };
    } else {
      return {
        icon: 'warning',
        title: 'Poor Quality',
        message: 'Consider retaking for better results',
        color: colors.error,
      };
    }
  };

  const qualityInfo = getQualityInfo();

  return (
    <View style={styles.container}>
      <View style={[styles.qualityCard, { borderColor: qualityInfo.color }]}>
        <Ionicons
          name={qualityInfo.icon}
          size={48}
          color={qualityInfo.color}
        />
        
        <Text style={styles.title}>{qualityInfo.title}</Text>
        <Text style={styles.message}>{qualityInfo.message}</Text>
        
        <View style={styles.qualityBar}>
          <View
            style={[
              styles.qualityFill,
              {
                width: `${quality * 100}%`,
                backgroundColor: qualityInfo.color,
              },
            ]}
          />
        </View>
        
        <Text style={styles.qualityPercentage}>
          {Math.round(quality * 100)}% quality
        </Text>
        
        <View style={styles.actions}>
          {onRetake && (
            <TouchableOpacity
              style={[styles.button, styles.retakeButton]}
              onPress={onRetake}
            >
              <Ionicons name="refresh" size={20} color={colors.onPrimary} />
              <Text style={styles.buttonText}>Retake</Text>
            </TouchableOpacity>
          )}
          
          {onUseAnyway && (
            <TouchableOpacity
              style={[styles.button, styles.useButton]}
              onPress={onUseAnyway}
            >
              <Text style={styles.buttonText}>Use Anyway</Text>
              <Ionicons name="arrow-forward" size={20} color={colors.primary} />
            </TouchableOpacity>
          )}
        </View>
      </View>
      
      <View style={styles.tips}>
        <Text style={styles.tipsTitle}>Tips for better quality:</Text>
        <View style={styles.tipItem}>
          <Ionicons name="checkmark" size={16} color={colors.success} />
          <Text style={styles.tipText}>Ensure good lighting</Text>
        </View>
        <View style={styles.tipItem}>
          <Ionicons name="checkmark" size={16} color={colors.success} />
          <Text style={styles.tipText}>Keep the camera steady</Text>
        </View>
        <View style={styles.tipItem}>
          <Ionicons name="checkmark" size={16} color={colors.success} />
          <Text style={styles.tipText}>Fill the frame with the problem</Text>
        </View>
      </View>
    </View>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      padding: 16,
    },
    qualityCard: {
      backgroundColor: colors.surface,
      borderRadius: 16,
      padding: 24,
      alignItems: 'center',
      borderWidth: 2,
      marginBottom: 16,
    },
    title: {
      fontSize: 20,
      fontWeight: 'bold',
      color: colors.text,
      marginTop: 12,
      marginBottom: 4,
    },
    message: {
      fontSize: 14,
      color: colors.textSecondary,
      textAlign: 'center',
      marginBottom: 16,
    },
    qualityBar: {
      width: '100%',
      height: 8,
      backgroundColor: colors.surfaceVariant,
      borderRadius: 4,
      overflow: 'hidden',
      marginBottom: 8,
    },
    qualityFill: {
      height: '100%',
      borderRadius: 4,
    },
    qualityPercentage: {
      fontSize: 16,
      fontWeight: '600',
      color: colors.text,
      marginBottom: 20,
    },
    actions: {
      flexDirection: 'row',
      gap: 12,
    },
    button: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingHorizontal: 20,
      paddingVertical: 12,
      borderRadius: 8,
      gap: 8,
    },
    retakeButton: {
      backgroundColor: colors.error,
    },
    useButton: {
      backgroundColor: colors.surfaceVariant,
    },
    buttonText: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.onPrimary,
    },
    tips: {
      backgroundColor: colors.surfaceVariant,
      borderRadius: 12,
      padding: 16,
    },
    tipsTitle: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.text,
      marginBottom: 12,
    },
    tipItem: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 8,
    },
    tipText: {
      fontSize: 14,
      color: colors.textSecondary,
      marginLeft: 8,
      flex: 1,
    },
  });

export default ImageQualityChecker;
