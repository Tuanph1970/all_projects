import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Camera } from 'expo-camera';
import { Ionicons } from '@expo/vector-icons';
import { useDispatch } from 'react-redux';
import { useTheme } from '../../hooks/useTheme';
import { submitProblem } from '../../store/slices/problemSlice';

const CameraScreen = ({ navigation }) => {
  const [hasPermission, setHasPermission] = useState(null);
  const [isReady, setIsReady] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
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

  const takePicture = async () => {
    if (cameraRef.current && isReady && !isProcessing) {
      try {
        setIsProcessing(true);

        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.8,
          base64: false,
        });

        // Submit problem to backend with default category
        const resultAction = await dispatch(submitProblem({
          imageUri: photo.uri,
          category: 'General',
          description: 'Captured from camera'
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
              onPress: () => navigation.goBack()
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
        Alert.alert('Error', 'Failed to take picture');
      }
    }
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
            <View style={styles.placeholder} />
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
            <TouchableOpacity style={styles.galleryButton}>
              <Ionicons name="images" size={24} color="#FFFFFF" />
            </TouchableOpacity>
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
  });

export default CameraScreen;