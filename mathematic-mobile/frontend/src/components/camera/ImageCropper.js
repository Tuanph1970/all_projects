import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Text,
  Modal,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';
import * as ImageManipulator from 'expo-image-manipulator';

/**
 * ImageCropper Component
 * Allows users to crop and adjust captured images
 */
const ImageCropper = ({ imageUri, onCropComplete, onCancel }) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const [isProcessing, setIsProcessing] = useState(false);
  const [cropRegion, setCropRegion] = useState({
    originX: 0.1,
    originY: 0.1,
    width: 0.8,
    height: 0.8,
  });

  const handleApplyCrop = async () => {
    setIsProcessing(true);
    try {
      const manipulatedImage = await ImageManipulator.manipulateAsync(
        imageUri,
        [
          {
            crop: {
              originX: cropRegion.originX,
              originY: cropRegion.originY,
              width: cropRegion.width,
              height: cropRegion.height,
            },
          },
        ],
        {
          compress: 0.9,
          format: ImageManipulator.SaveFormat.JPEG,
        }
      );

      onCropComplete(manipulatedImage.uri);
    } catch (error) {
      console.error('Error cropping image:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleResetCrop = () => {
    setCropRegion({
      originX: 0.1,
      originY: 0.1,
      width: 0.8,
      height: 0.8,
    });
  };

  return (
    <Modal visible={true} animationType="slide" transparent={true}>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={onCancel} style={styles.headerButton}>
            <Ionicons name="close" size={24} color={colors.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Crop Image</Text>
          <TouchableOpacity
            onPress={handleApplyCrop}
            disabled={isProcessing}
            style={styles.headerButton}
          >
            {isProcessing ? (
              <ActivityIndicator size="small" color={colors.primary} />
            ) : (
              <Ionicons name="checkmark" size={24} color={colors.primary} />
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.cropArea}>
          {/* Image would be displayed here with crop overlay */}
          <View style={styles.cropOverlay}>
            <View style={styles.cropFrame}>
              <Text style={styles.cropInstruction}>
                Adjust crop area by dragging corners
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.controls}>
          <TouchableOpacity
            style={styles.controlButton}
            onPress={handleResetCrop}
          >
            <Ionicons name="refresh" size={20} color={colors.text} />
            <Text style={styles.controlButtonText}>Reset</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.controlButton}>
            <Ionicons name="crop" size={20} color={colors.text} />
            <Text style={styles.controlButtonText}>Free</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.controlButton}>
            <Ionicons name="square" size={20} color={colors.text} />
            <Text style={styles.controlButtonText}>1:1</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: '#000',
    },
    header: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingHorizontal: 16,
      paddingVertical: 12,
      backgroundColor: colors.surface,
    },
    headerButton: {
      padding: 8,
    },
    headerTitle: {
      fontSize: 18,
      fontWeight: '600',
      color: colors.text,
    },
    cropArea: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
    },
    cropOverlay: {
      width: '100%',
      height: '100%',
      backgroundColor: 'rgba(0, 0, 0, 0.6)',
      justifyContent: 'center',
      alignItems: 'center',
    },
    cropFrame: {
      width: 300,
      height: 400,
      borderWidth: 2,
      borderColor: '#FFF',
      borderStyle: 'dashed',
      justifyContent: 'center',
      alignItems: 'center',
    },
    cropInstruction: {
      color: '#FFF',
      fontSize: 14,
      textAlign: 'center',
    },
    controls: {
      flexDirection: 'row',
      justifyContent: 'space-around',
      paddingVertical: 16,
      backgroundColor: colors.surface,
    },
    controlButton: {
      alignItems: 'center',
      gap: 4,
    },
    controlButtonText: {
      fontSize: 12,
      color: colors.text,
      marginTop: 4,
    },
  });

export default ImageCropper;
