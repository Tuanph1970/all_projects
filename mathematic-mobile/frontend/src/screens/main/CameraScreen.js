import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
  ActivityIndicator,
  Image,
  ScrollView,
  Modal,
} from 'react-native';
import { Camera } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { useDispatch } from 'react-redux';
import { useTheme } from '../../hooks/useTheme';
import { submitProblem } from '../../store/slices/problemSlice';
import ImageQualityChecker from '../../components/camera/ImageQualityChecker';
import ImageCropper from '../../components/camera/ImageCropper';
import {
  compressImage,
  checkImageQuality,
  optimizeImageForUpload,
  formatFileSize,
} from '../../utils/imageCompression';

const CameraScreen = ({ navigation }) => {
  const [hasPermission, setHasPermission] = useState(null);
  const [isReady, setIsReady] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [capturedImages, setCapturedImages] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showQualityCheck, setShowQualityCheck] = useState(false);
  const [showCropper, setShowCropper] = useState(false);
  const [imageQuality, setImageQuality] = useState(0);
  const [category, setCategory] = useState('General');
  const cameraRef = useRef(null);
  const dispatch = useDispatch();
  const { colors } = useTheme();
  const styles = createStyles(colors);

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      setHasPermission(status === 'granted');
    })();
  }, []);

  /**
   * Take picture with quality check
   */
  const takePicture = async () => {
    if (cameraRef.current && isReady && !isProcessing) {
      try {
        setIsProcessing(true);

        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.9,
          base64: false,
          exif: true,
        });

        // Check image quality
        const qualityResult = await checkImageQuality(photo.uri);
        setImageQuality(qualityResult.quality);

        // Compress image
        const compressedImage = await optimizeImageForUpload(photo.uri);

        setCapturedImages([...capturedImages, compressedImage]);
        setSelectedImage(compressedImage);
        setShowPreview(true);
        setShowQualityCheck(true);
        setIsProcessing(false);
      } catch (error) {
        setIsProcessing(false);
        Alert.alert('Error', 'Failed to take picture');
      }
    }
  };

  /**
   * Pick image from gallery
   */
  const pickImageFromGallery = async () => {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      
      if (status !== 'granted') {
        Alert.alert(
          'Permission Required',
          'Please grant permission to access your photos'
        );
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [3, 4],
        quality: 0.9,
      });

      if (!result.canceled && result.assets && result.assets[0]) {
        const selectedImage = result.assets[0];
        
        // Check image quality
        const qualityResult = await checkImageQuality(selectedImage.uri);
        setImageQuality(qualityResult.quality);

        // Compress image
        const compressedImage = await optimizeImageForUpload(selectedImage.uri);

        setCapturedImages([...capturedImages, compressedImage]);
        setSelectedImage(compressedImage);
        setShowPreview(true);
        setShowQualityCheck(true);
      }
    } catch (error) {
      console.error('Error picking image:', error);
      Alert.alert('Error', 'Failed to pick image from gallery');
    }
  };

  /**
   * Use image despite quality issues
   */
  const handleUseImageAnyway = () => {
    setShowQualityCheck(false);
  };

  /**
   * Retake image
   */
  const handleRetake = () => {
    setCapturedImages([]);
    setSelectedImage(null);
    setShowPreview(false);
    setShowQualityCheck(false);
  };

  /**
   * Proceed to submit image
   */
  const handleSubmit = async () => {
    if (!selectedImage) return;

    try {
      setIsProcessing(true);
      setShowPreview(false);

      // Submit problem to backend
      const resultAction = await dispatch(submitProblem({
        imageUri: selectedImage.uri,
        category,
        description: 'Captured from camera or gallery',
      }));

      setIsProcessing(false);

      if (submitProblem.fulfilled.match(resultAction)) {
        const problem = resultAction.payload;

        Alert.alert(
          'Success!',
          'Your math problem is being processed',
          [{
            text: 'View Solution',
            onPress: () => {
              navigation.navigate('Solution', { problemId: problem.id });
            }
          }, {
            text: 'OK',
            onPress: () => {
              setCapturedImages([]);
              setSelectedImage(null);
              navigation.goBack();
            }
          }]
        );
      } else {
        Alert.alert(
          'Error',
          resultAction.error?.message || 'Failed to submit problem. Please try again.'
        );
      }
    } catch (error) {
      setIsProcessing(false);
      Alert.alert('Error', 'Failed to submit problem');
    }
  };

  /**
   * Open cropper
   */
  const handleCrop = () => {
    setShowCropper(true);
  };

  /**
   * Handle crop complete
   */
  const handleCropComplete = (croppedUri) => {
    setSelectedImage({ uri: croppedUri });
    setShowCropper(false);
  };

  if (hasPermission === null) {
    return (
      <View style={styles.container}>
        <Text style={styles.message}>Requesting camera permission...</Text>
      </View>
    );
  }

  if (hasPermission === false) {
    return (
      <View style={styles.container}>
        <Ionicons name="camera-off" size={64} color={colors.textSecondary} />
        <Text style={styles.message}>No access to camera</Text>
        <Text style={styles.submessage}>
          Please enable camera permissions in settings
        </Text>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.backButtonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Show image preview with quality check
  if (showPreview && selectedImage) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.previewContainer}>
          <View style={styles.previewHeader}>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={handleRetake}
            >
              <Ionicons name="close" size={24} color="#FFFFFF" />
            </TouchableOpacity>
            <Text style={styles.previewTitle}>Preview</Text>
            <TouchableOpacity
              style={styles.submitButton}
              onPress={handleSubmit}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <ActivityIndicator size="small" color="#FFFFFF" />
              ) : (
                <Text style={styles.submitButtonText}>Submit</Text>
              )}
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.previewContent} showsVerticalScrollIndicator={false}>
            <Image source={{ uri: selectedImage.uri }} style={styles.previewImage} />

            {showQualityCheck && (
              <ImageQualityChecker
                quality={imageQuality}
                onRetake={handleRetake}
                onUseAnyway={handleUseImageAnyway}
              />
            )}

            <View style={styles.imageInfo}>
              <View style={styles.infoRow}>
                <Ionicons name="folder" size={20} color={colors.textSecondary} />
                <Text style={styles.infoText}>
                  Size: {formatFileSize(selectedImage.width * selectedImage.height)}
                </Text>
              </View>
              <View style={styles.infoRow}>
                <Ionicons name="image" size={20} color={colors.textSecondary} />
                <Text style={styles.infoText}>
                  Dimensions: {selectedImage.width} x {selectedImage.height}
                </Text>
              </View>
            </View>

            <View style={styles.actions}>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={handleCrop}
              >
                <Ionicons name="crop" size={24} color={colors.primary} />
                <Text style={styles.actionButtonText}>Crop</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.actionButton}
                onPress={pickImageFromGallery}
              >
                <Ionicons name="images" size={24} color={colors.primary} />
                <Text style={styles.actionButtonText}>Gallery</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.actionButton}
                onPress={handleRetake}
              >
                <Ionicons name="refresh" size={24} color={colors.primary} />
                <Text style={styles.actionButtonText}>Retake</Text>
              </TouchableOpacity>
            </View>
          </ScrollView>
        </View>

        {showCropper && (
          <ImageCropper
            imageUri={selectedImage.uri}
            onCropComplete={handleCropComplete}
            onCancel={() => setShowCropper(false)}
          />
        )}
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <Camera
        ref={cameraRef}
        style={styles.camera}
        type={Camera.Constants.Type.back}
        onCameraReady={() => setIsReady(true)}
      >
        <View style={styles.overlay}>
          <View style={styles.header}>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => navigation.goBack()}
            >
              <Ionicons name="close" size={24} color="#FFFFFF" />
            </TouchableOpacity>
            <Text style={styles.title}>Scan Math Problem</Text>
            <View style={styles.placeholder} />
          </View>

          <View style={styles.scanArea}>
            <View style={styles.scanFrame} />
            <Text style={styles.instruction}>
              Position the math problem within the frame
            </Text>
          </View>

          <View style={styles.controls}>
            <TouchableOpacity
              style={styles.galleryButton}
              onPress={pickImageFromGallery}
            >
              <Ionicons name="images" size={24} color="#FFFFFF" />
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.captureButton,
                (!isReady || isProcessing) && styles.captureButtonDisabled
              ]}
              onPress={takePicture}
              disabled={!isReady || isProcessing}
            >
              {isProcessing ? (
                <ActivityIndicator size="large" color="#FFFFFF" />
              ) : (
                <View style={styles.captureButtonInner} />
              )}
            </TouchableOpacity>
            <View style={styles.placeholder} />
          </View>

          {isProcessing && (
            <View style={styles.processingOverlay}>
              <ActivityIndicator size="large" color="#FFFFFF" />
              <Text style={styles.processingText}>Processing your problem...</Text>
            </View>
          )}
        </View>
      </Camera>
    </SafeAreaView>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
      justifyContent: 'center',
      alignItems: 'center',
    },
    camera: {
      flex: 1,
      width: '100%',
    },
    overlay: {
      flex: 1,
      backgroundColor: 'rgba(0, 0, 0, 0.3)',
      justifyContent: 'space-between',
    },
    header: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingTop: 60,
      paddingHorizontal: 24,
    },
    closeButton: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      justifyContent: 'center',
      alignItems: 'center',
    },
    title: {
      fontSize: 18,
      fontWeight: '600',
      color: '#FFFFFF',
      textAlign: 'center',
    },
    placeholder: {
      width: 40,
    },
    scanArea: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      paddingHorizontal: 40,
    },
    scanFrame: {
      width: 280,
      height: 200,
      borderWidth: 2,
      borderColor: '#FFFFFF',
      borderRadius: 12,
      backgroundColor: 'transparent',
    },
    instruction: {
      color: '#FFFFFF',
      fontSize: 16,
      textAlign: 'center',
      marginTop: 20,
    },
    controls: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      paddingHorizontal: 40,
      paddingBottom: 40,
    },
    captureButton: {
      width: 70,
      height: 70,
      borderRadius: 35,
      backgroundColor: '#FFFFFF',
      justifyContent: 'center',
      alignItems: 'center',
    },
    captureButtonDisabled: {
      backgroundColor: 'rgba(255, 255, 255, 0.5)',
    },
    captureButtonInner: {
      width: 60,
      height: 60,
      borderRadius: 30,
      backgroundColor: colors.primary,
    },
    galleryButton: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: 'rgba(255, 255, 255, 0.3)',
      justifyContent: 'center',
      alignItems: 'center',
    },
    message: {
      fontSize: 18,
      color: colors.text,
      textAlign: 'center',
      marginBottom: 8,
    },
    submessage: {
      fontSize: 14,
      color: colors.textSecondary,
      textAlign: 'center',
      marginBottom: 24,
    },
    backButton: {
      backgroundColor: colors.primary,
      paddingHorizontal: 24,
      paddingVertical: 12,
      borderRadius: 8,
    },
    backButtonText: {
      color: '#FFFFFF',
      fontSize: 16,
      fontWeight: '600',
    },
    processingOverlay: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      justifyContent: 'center',
      alignItems: 'center',
    },
    processingText: {
      color: '#FFFFFF',
      fontSize: 16,
      fontWeight: '600',
      marginTop: 16,
    },
    // Preview styles
    previewContainer: {
      flex: 1,
      backgroundColor: '#000',
    },
    previewHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingHorizontal: 16,
      paddingVertical: 12,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
    },
    closeButton: {
      padding: 8,
    },
    previewTitle: {
      fontSize: 18,
      fontWeight: '600',
      color: '#FFFFFF',
    },
    submitButton: {
      backgroundColor: colors.primary,
      paddingHorizontal: 20,
      paddingVertical: 8,
      borderRadius: 8,
    },
    submitButtonText: {
      color: '#FFFFFF',
      fontSize: 14,
      fontWeight: '600',
    },
    previewContent: {
      flex: 1,
    },
    previewImage: {
      width: '100%',
      height: 400,
      resizeMode: 'contain',
      backgroundColor: '#000',
    },
    imageInfo: {
      padding: 16,
      backgroundColor: colors.surface,
    },
    infoRow: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 8,
    },
    infoText: {
      fontSize: 14,
      color: colors.textSecondary,
      marginLeft: 8,
    },
    actions: {
      flexDirection: 'row',
      justifyContent: 'space-around',
      padding: 16,
      backgroundColor: colors.surface,
      borderTopWidth: 1,
      borderTopColor: colors.outline,
    },
    actionButton: {
      alignItems: 'center',
      padding: 12,
      gap: 4,
    },
    actionButtonText: {
      fontSize: 12,
      color: colors.primary,
      fontWeight: '600',
      marginTop: 4,
    },
  });

export default CameraScreen;