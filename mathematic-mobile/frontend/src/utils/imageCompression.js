import * as ImageManipulator from 'expo-image-manipulator';
import * as FileSystem from 'expo-file-system';

/**
 * Image Compression Utility
 * Compresses images to reduce file size while maintaining quality
 */

export const compressImage = async (uri, options = {}) => {
  const {
    maxWidth = 1920,
    maxHeight = 1920,
    quality = 0.8,
    format = ImageManipulator.SaveFormat.JPEG,
  } = options;

  try {
    const manipulatedImage = await ImageManipulator.manipulateAsync(
      uri,
      [
        {
          resize: {
            width: maxWidth,
            height: maxHeight,
          },
        },
      ],
      {
        compress: quality,
        format,
      }
    );

    return {
      uri: manipulatedImage.uri,
      width: manipulatedImage.width,
      height: manipulatedImage.height,
    };
  } catch (error) {
    console.error('Error compressing image:', error);
    throw error;
  }
};

/**
 * Calculate image file size
 */
export const getImageFileSize = async (uri) => {
  try {
    const fileInfo = await FileSystem.getInfoAsync(uri);
    return fileInfo.size || 0;
  } catch (error) {
    console.error('Error getting file size:', error);
    return 0;
  }
};

/**
 * Format file size to human-readable format
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Check if image meets quality requirements
 */
export const checkImageQuality = async (uri) => {
  try {
    const fileInfo = await FileSystem.getInfoAsync(uri);
    const fileSize = fileInfo.size || 0;

    // Check file size (max 10MB)
    if (fileSize > 10 * 1024 * 1024) {
      return {
        passed: false,
        quality: 0.3,
        issues: ['File size too large (> 10MB)'],
      };
    }

    // Check if file size is reasonable (at least 100KB for good quality)
    if (fileSize < 100 * 1024) {
      return {
        passed: false,
        quality: 0.4,
        issues: ['File size too small, image may be blurry'],
      };
    }

    // If file size is good, assume quality is acceptable
    const quality = Math.min(1.0, fileSize / (5 * 1024 * 1024));

    return {
      passed: quality >= 0.6,
      quality,
      issues: [],
    };
  } catch (error) {
    console.error('Error checking image quality:', error);
    return {
      passed: false,
      quality: 0,
      issues: ['Failed to check image quality'],
    };
  }
};

/**
 * Optimize image for upload
 */
export const optimizeImageForUpload = async (uri) => {
  try {
    const fileSize = await getImageFileSize(uri);

    // If file is larger than 2MB, compress it
    if (fileSize > 2 * 1024 * 1024) {
      const compressed = await compressImage(uri, {
        maxWidth: 1920,
        maxHeight: 1920,
        quality: 0.7,
      });
      return compressed;
    }

    // If file is between 1MB and 2MB, lightly compress
    if (fileSize > 1 * 1024 * 1024) {
      const compressed = await compressImage(uri, {
        maxWidth: 1920,
        maxHeight: 1920,
        quality: 0.85,
      });
      return compressed;
    }

    // File is already small enough, just ensure dimensions are reasonable
    const compressed = await compressImage(uri, {
      maxWidth: 1920,
      maxHeight: 1920,
      quality: 0.9,
    });
    return compressed;
  } catch (error) {
    console.error('Error optimizing image:', error);
    throw error;
  }
};

/**
 * Convert image to base64
 */
export const imageToBase64 = async (uri) => {
  try {
    const response = await fetch(uri);
    const blob = await response.blob();

    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch (error) {
    console.error('Error converting image to base64:', error);
    throw error;
  }
};

export default {
  compressImage,
  getImageFileSize,
  formatFileSize,
  checkImageQuality,
  optimizeImageForUpload,
  imageToBase64,
};
