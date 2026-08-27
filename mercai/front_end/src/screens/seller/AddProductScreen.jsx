import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  TouchableOpacity,
  Image,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  Text,
  Appbar,
  TextInput,
  Button,
  Card,
  Chip,
  ActivityIndicator,
  Surface,
} from 'react-native-paper';
import { useNavigation, useRoute } from '@react-navigation/native';
import ImageCropPicker from 'react-native-image-crop-picker';
import { colors, spacing, typography } from '../../constants/theme.js';
import { API_BASE_URL } from '../../constants/config.js';
import sellerService from '../../services/sellerService.js';
import sellerCategoryService from '../../services/sellerCategoryService.js';
import { CategorySelectorField } from '../../components/seller/CategorySelector.jsx';
import VideoPicker from '../../components/seller/VideoPicker.jsx';
import VideoPreview from '../../components/seller/VideoPreview.jsx';
import VideoUploadProgress from '../../components/seller/VideoUploadProgress.jsx';
import { useTranslation } from '@i18n';

export const AddProductScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const insets = useSafeAreaInsets();
  const t = useTranslation();

  // Check if editing existing product
  const productId = route.params?.productId;
  const isEditMode = !!productId;

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    price: '',
    tags: '',
    stock_quantity: '',
    condition: 'new',
    // Buyers filter on these, and the listing optimizer proposes them, so the
    // form has to be able to hold them.
    material: '',
    color: '',
    technique: '',
    dimensions: '',
  });

  // Listing optimizer state

  // Selected category (object with id, name, etc.)
  const [selectedCategory, setSelectedCategory] = useState(null);

  // Media state
  const [images, setImages] = useState([]);
  const [video, setVideo] = useState(null); // { uri, duration, size, fileName, mime }
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [loadingProduct, setLoadingProduct] = useState(false);
  
  // Video upload state
  const [videoUploadProgress, setVideoUploadProgress] = useState(0);
  const [isVideoUploading, setIsVideoUploading] = useState(false);
  const [videoUploadError, setVideoUploadError] = useState(null);
  const [videoUploadSuccess, setVideoUploadSuccess] = useState(false);
  const [uploadedVideoData, setUploadedVideoData] = useState(null); // { url, thumbnail_url, duration, etc. }

  // Form errors
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (isEditMode) {
      loadProductData();
    }
  }, [productId]);

  // Load product data for editing
  const loadProductData = async () => {
    try {
      setLoadingProduct(true);
      const product = await sellerService.getProduct(productId);

      setFormData({
        title: product.name || '',
        description: product.description || '',
        price: product.price?.toString() || '',
        tags: product.tags || '',
        stock_quantity: product.quantity_available?.toString() || '',
        condition: 'new',
        material: product.material || '',
        color: product.color || '',
        technique: product.technique || '',
        dimensions: product.dimensions || '',
      });

      // Set category if available - fetch category details
      if (product.seller_category_id) {
        console.log('[EditProduct] Loading category for seller_category_id:', product.seller_category_id);
        try {
          const categoryResponse = await sellerCategoryService.getCategoryTree(false);
          console.log('[EditProduct] Category tree response:', JSON.stringify(categoryResponse, null, 2));

          // Find the category in the tree recursively
          const findCategory = (categories, targetId) => {
            for (const cat of categories) {
              if (cat.id === targetId) {
                return cat;
              }
              if (cat.children && cat.children.length > 0) {
                const found = findCategory(cat.children, targetId);
                if (found) return found;
              }
            }
            return null;
          };

          const categories = categoryResponse?.categories || categoryResponse || [];
          console.log('[EditProduct] Searching in categories:', categories.length);

          const category = findCategory(categories, product.seller_category_id);
          console.log('[EditProduct] Found category:', category);

          if (category) {
            const selectedCat = {
              id: category.id,
              name: category.name,
              full_path_name: category.full_path_name || category.name,
            };
            console.log('[EditProduct] Setting selectedCategory:', selectedCat);
            setSelectedCategory(selectedCat);
          } else {
            // Fallback if category not found in tree
            console.warn('[EditProduct] Category not found in tree, using fallback');
            setSelectedCategory({
              id: product.seller_category_id,
              name: product.seller_category?.name || `Category #${product.seller_category_id}`,
            });
          }
        } catch (categoryError) {
          console.error('[EditProduct] Failed to fetch category details:', categoryError);
          // Fallback to basic info from product
          setSelectedCategory({
            id: product.seller_category_id,
            name: product.seller_category?.name || `Category #${product.seller_category_id}`,
          });
        }
      } else {
        console.log('[EditProduct] No seller_category_id on product');
      }

      // Load existing images - prepend base URL for relative paths
      if (product.images && product.images.length > 0) {
        setImages(product.images.map(img => {
          const rawUrl = img.image_url || img.url || img.src || null;
          let imageUri = null;
          if (rawUrl) {
            imageUri = rawUrl.startsWith('http') ? rawUrl : `${API_BASE_URL}${rawUrl}`;
          }
          console.log('[AddProduct] Existing image URI:', imageUri);
          return {
            uri: imageUri,
            id: img.id,
            existing: true,
          };
        }));
      }
    } catch (error) {
      console.error('Failed to load product:', error);
      Alert.alert('Error', 'Failed to load product data');
      navigation.goBack();
    } finally {
      setLoadingProduct(false);
    }
  };

  // Cropper configuration for highly visible CROP button
  const cropperConfig = {
    width: 800,
    height: 600,
    cropping: true,
    // Bright orange toolbar for high visibility of CROP button
    cropperToolbarColor: '#FF6B00',
    // White text/icons on toolbar for maximum contrast
    cropperToolbarWidgetColor: '#FFFFFF',
    // Orange accent for active elements
    cropperActiveWidgetColor: '#FF6B00',
    cropperStatusBarColor: '#E55D00',
    cropperToolbarTitle: 'Crop Image',
    // Show helpful guidelines
    showCropGuidelines: true,
    showCropFrame: true,
    enableRotationGesture: true,
    freeStyleCropEnabled: false,
    // iOS-specific: Make Done/Cancel buttons visible
    cropperChooseText: 'CROP',
    cropperCancelText: 'Cancel',
    cropperChooseColor: '#FFFFFF',
    cropperCancelColor: '#FFFFFF',
    // Image quality
    compressImageQuality: 0.8,
    mediaType: 'photo',
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  const pickImage = async () => {
    try {
      if (images.length >= 5) {
        Alert.alert('Limit Reached', 'You can only upload up to 5 images.');
        return;
      }

      const image = await ImageCropPicker.openPicker({
        ...cropperConfig,
      });

      if (image && image.path) {
        setImages(prev => [...prev, {
          uri: image.path,
          width: image.width,
          height: image.height,
          mimeType: image.mime,
          fileName: image.path.split('/').pop(),
        }]);
      }
    } catch (error) {
      // User cancelled - not an error
      if (error.code === 'E_PICKER_CANCELLED') {
        return;
      }
      console.error('Error picking image:', error);
      Alert.alert('Error', 'Failed to pick image. Please try again.');
    }
  };

  const takePhoto = async () => {
    try {
      if (images.length >= 5) {
        Alert.alert('Limit Reached', 'You can only upload up to 5 images.');
        return;
      }

      const image = await ImageCropPicker.openCamera({
        ...cropperConfig,
      });

      if (image && image.path) {
        setImages(prev => [...prev, {
          uri: image.path,
          width: image.width,
          height: image.height,
          mimeType: image.mime,
          fileName: image.path.split('/').pop(),
        }]);
      }
    } catch (error) {
      // User cancelled - not an error
      if (error.code === 'E_PICKER_CANCELLED') {
        return;
      }
      console.error('Error taking photo:', error);
      Alert.alert('Error', 'Failed to capture photo. Please try again.');
    }
  };

  const removeImage = (index) => {
    setImages(prev => prev.filter((_, i) => i !== index));
  };

  /**
   * Handle video selection from VideoPicker
   */
  const handleVideoSelect = async (selectedVideo) => {
    if (video) {
      Alert.alert(
        t('addProduct.videoLimitReached'),
        t('addProduct.confirmRemove'),
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Replace',
            onPress: () => setVideoData(selectedVideo),
          },
        ]
      );
      return;
    }
    setVideoData(selectedVideo);
  };

  /**
   * Set video data and reset upload state
   */
  const setVideoData = (selectedVideo) => {
    setVideo({
      uri: selectedVideo.path,
      duration: selectedVideo.duration,
      size: selectedVideo.size,
      fileName: selectedVideo.filename || selectedVideo.path.split('/').pop(),
      mime: selectedVideo.mime,
    });
    setVideoUploadProgress(0);
    setVideoUploadError(null);
    setVideoUploadSuccess(false);
    setUploadedVideoData(null);
  };

  /**
   * Remove selected video
   */
  const removeVideo = () => {
    Alert.alert(
      t('addProduct.removeVideo'),
      t('addProduct.confirmRemove'),
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: () => {
            setVideo(null);
            setVideoUploadProgress(0);
            setVideoUploadError(null);
            setVideoUploadSuccess(false);
            setUploadedVideoData(null);
          },
        },
      ]
    );
  };

  /**
   * Upload video to server
   */
  const uploadVideo = async () => {
    if (!video) return null;

    setIsVideoUploading(true);
    setVideoUploadProgress(0);
    setVideoUploadError(null);
    setVideoUploadSuccess(false);

    try {
      const videoFormData = new FormData();
      videoFormData.append('file', {
        uri: video.uri,
        type: video.mime || 'video/mp4',
        name: video.fileName,
      });

      const response = await sellerService.uploadVideo(
        videoFormData,
        (progress) => {
          setVideoUploadProgress(progress);
        }
      );

      setVideoUploadSuccess(true);
      setUploadedVideoData(response);
      
      return response;
    } catch (error) {
      console.error('Error uploading video:', error);
      setVideoUploadError(error.response?.data?.detail || t('addProduct.uploadError'));
      throw error;
    } finally {
      setIsVideoUploading(false);
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }
    if (!formData.price.trim()) {
      newErrors.price = 'Price is required';
    } else if (isNaN(parseFloat(formData.price)) || parseFloat(formData.price) <= 0) {
      newErrors.price = 'Price must be a valid positive number';
    }
    if (!selectedCategory) {
      newErrors.category = 'Category is required';
    }
    if (!formData.stock_quantity.trim()) {
      newErrors.stock_quantity = 'Stock quantity is required';
    } else if (isNaN(parseInt(formData.stock_quantity)) || parseInt(formData.stock_quantity) < 0) {
      newErrors.stock_quantity = 'Stock quantity must be a valid positive number';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      Alert.alert('Validation Error', 'Please fix the errors before submitting.');
      return;
    }

    setIsLoading(true);

    try {
      // Use selected category ID directly
      const categoryId = selectedCategory?.id;

      if (!categoryId) {
        Alert.alert('Error', 'Please select a category');
        return;
      }

      // Prepare form data - map form fields to API expected fields
      const productData = {
        name: formData.title,
        description: formData.description,
        price: parseFloat(formData.price),
        seller_category_id: categoryId,  // Use seller_category_id for seller-specific categories
        quantity_available: parseInt(formData.stock_quantity),
        tags: formData.tags ? formData.tags.trim() : null,
        material: formData.material?.trim() || null,
        color: formData.color?.trim() || null,
        technique: formData.technique?.trim() || null,
        dimensions: formData.dimensions?.trim() || null,
      };

      // Create or update product
      let product;
      if (isEditMode) {
        product = await sellerService.updateProduct(productId, productData);
        product.id = productId; // Ensure we have the ID for image uploads
      } else {
        product = await sellerService.createProduct(productData);
      }

      // Upload new images only (skip existing ones in edit mode)
      const newImages = images.filter(img => !img.existing);
      if (newImages.length > 0 && product?.id) {
        setIsUploading(true);
        console.log(`Uploading ${newImages.length} new images for product ${product.id}`);

        for (let i = 0; i < newImages.length; i++) {
          const image = newImages[i];
          try {
            // Create FormData for image upload
            const imageFormData = new FormData();
            imageFormData.append('file', {
              uri: image.uri,
              type: image.mimeType || 'image/jpeg',
              name: image.fileName || `product_${product.id}_${i}.jpg`,
            });

            // Upload image to get URL
            const uploadResult = await sellerService.uploadImage(imageFormData);
            console.log('Image uploaded:', uploadResult);

            // Add image to product if we got a URL back
            if (uploadResult?.image_url || uploadResult?.url) {
              const imageUrl = uploadResult.image_url || uploadResult.url;
              await sellerService.addProductImage(product.id, {
                image_url: imageUrl,
                is_primary: i === 0, // First image is primary
                order_index: i,
              });
              console.log(`Image ${i + 1} added to product`);
            }
          } catch (uploadError) {
            console.error(`Failed to upload image ${i + 1}:`, uploadError);
            // Continue with other images even if one fails
          }
        }
        setIsUploading(false);
      }

      // Upload video if exists
      if (video && product?.id) {
        try {
          console.log(`Uploading video for product ${product.id}`);
          const videoResponse = await uploadVideo();
          
          if (videoResponse) {
            // Add video to product
            await sellerService.addVideoToProduct(product.id, {
              video_url: videoResponse.url,
              thumbnail_url: videoResponse.thumbnail_url,
              duration_seconds: videoResponse.duration?.toString(),
              file_size_mb: videoResponse.file_size_mb?.toString(),
              resolution: videoResponse.resolution,
              alt_text: 'Product video',
            });
            console.log('Video added to product');
          }
        } catch (videoError) {
          console.error('Failed to upload video:', videoError);
          // Continue even if video upload fails
        }
      }

      if (isEditMode) {
        Alert.alert(
          'Success',
          'Product updated successfully!',
          [
            {
              text: 'OK',
              onPress: () => navigation.goBack()
            }
          ]
        );
      } else {
        Alert.alert(
          'Success',
          'Product created successfully!',
          [
            {
              text: 'Add Another',
              onPress: resetForm
            },
            {
              text: 'View Product',
              onPress: () => navigation.navigate('ProductDetails', { productId: product.id })
            }
          ]
        );
      }

    } catch (error) {
      console.error('Error saving product:', error);
      Alert.alert('Error', error.message || `Failed to ${isEditMode ? 'update' : 'create'} product. Please try again.`);
    } finally {
      setIsLoading(false);
      setIsUploading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      price: '',
      tags: '',
      stock_quantity: '',
      condition: 'new',
    });
    setSelectedCategory(null);
    setImages([]);
    setErrors({});
  };

  const showImageOptions = () => {
    Alert.alert(
      'Add Image',
      'Choose an option',
      [
        { text: 'Camera', onPress: takePhoto },
        { text: 'Gallery', onPress: pickImage },
        { text: 'Cancel', style: 'cancel' }
      ]
    );
  };

  return (
    <View style={styles.container} testID="add-product-screen">
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="add-product-back-button" />
        <Appbar.Content title={isEditMode ? "Edit Product" : "Add Product"} />
      </Appbar.Header>

      {loadingProduct ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading product...</Text>
        </View>
      ) : (
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false} testID="add-product-scroll">
        {/* Product Images */}
        <Card style={styles.section} testID="add-product-images-section">
          <Text style={styles.sectionTitle}>Product Images</Text>

          {/* Large primary image preview */}
          {images.length > 0 && images[0].uri && (
            <Image
              source={{ uri: images[0].uri }}
              style={styles.primaryImagePreview}
              resizeMode="cover"
              onError={(e) => console.warn('[AddProduct] Primary image load error:', e.nativeEvent.error, 'URI:', images[0].uri)}
            />
          )}

          <View style={styles.imageContainer} testID="add-product-images-container">
            {images.map((image, index) => (
              <View key={index} style={styles.imageWrapper}>
                <Image source={{ uri: image.uri }} style={styles.image} />
                <TouchableOpacity
                  style={styles.removeButton}
                  onPress={() => removeImage(index)}
                >
                  <Text style={styles.removeButtonText}>×</Text>
                </TouchableOpacity>
              </View>
            ))}
            {images.length < 5 && (
              <TouchableOpacity style={styles.addImageButton} onPress={showImageOptions} testID="add-product-add-image-button">
                <Text style={styles.addImageText}>+</Text>
              </TouchableOpacity>
            )}
          </View>
        </Card>

        {/* Product Video */}
        <Card style={styles.section} testID="add-product-video-section">
          <Text style={styles.sectionTitle}>Product Video (Optional)</Text>
          
          {video ? (
            <>
              <VideoPreview
                videoUri={video.uri}
                duration={video.duration}
                fileSize={video.size ? video.size / (1024 * 1024) : 0}
                onRemove={removeVideo}
              />
              <VideoUploadProgress
                progress={videoUploadProgress}
                isUploading={isVideoUploading}
                error={videoUploadError}
                success={videoUploadSuccess}
              />
            </>
          ) : (
            <VideoPicker
              onVideoSelect={handleVideoSelect}
              maxDuration={60}
            />
          )}
        </Card>

        {/* Product Details */}
        <Card style={styles.section} testID="add-product-details-section">
          <Text style={styles.sectionTitle}>Product Details</Text>

          <TextInput
            label="Title *"
            value={formData.title}
            onChangeText={(text) => handleInputChange('title', text)}
            style={styles.input}
            error={!!errors.title}
            mode="outlined"
            testID="add-product-title-input"
          />
          {errors.title && <Text style={styles.errorText} testID="add-product-title-error">{errors.title}</Text>}

          <TextInput
            label="Description *"
            value={formData.description}
            onChangeText={(text) => handleInputChange('description', text)}
            style={styles.input}
            error={!!errors.description}
            mode="outlined"
            multiline
            numberOfLines={4}
            testID="add-product-description-input"
          />
          {errors.description && <Text style={styles.errorText} testID="add-product-description-error">{errors.description}</Text>}

          <TextInput
            label="Price *"
            value={formData.price}
            onChangeText={(text) => handleInputChange('price', text)}
            style={styles.input}
            error={!!errors.price}
            mode="outlined"
            keyboardType="decimal-pad"
            left={<TextInput.Affix text="$" />}
            testID="add-product-price-input"
          />
          {errors.price && <Text style={styles.errorText} testID="add-product-price-error">{errors.price}</Text>}

          <CategorySelectorField
            value={selectedCategory}
            onChange={(category) => {
              setSelectedCategory(category);
              if (errors.category) {
                setErrors(prev => ({ ...prev, category: '' }));
              }
            }}
            error={!!errors.category}
            errorMessage={errors.category}
            label="Category *"
            placeholder="Tap to select a category"
          />

          <TextInput
            label="Stock Quantity *"
            value={formData.stock_quantity}
            onChangeText={(text) => handleInputChange('stock_quantity', text)}
            style={styles.input}
            error={!!errors.stock_quantity}
            mode="outlined"
            keyboardType="numeric"
            testID="add-product-stock-input"
          />
          {errors.stock_quantity && <Text style={styles.errorText} testID="add-product-stock-error">{errors.stock_quantity}</Text>}

          <TextInput
            label="Tags (comma-separated)"
            value={formData.tags}
            onChangeText={(text) => handleInputChange('tags', text)}
            style={styles.input}
            mode="outlined"
            placeholder="ceramic, handmade, pottery"
            testID="add-product-tags-input"
          />

          {/* Buyers filter on these, so they are worth filling in. */}
          <TextInput
            label="Material"
            value={formData.material}
            onChangeText={(text) => handleInputChange('material', text)}
            style={styles.input}
            mode="outlined"
            placeholder="stoneware, porcelain, earthenware"
            testID="add-product-material-input"
          />

          <TextInput
            label="Colour"
            value={formData.color}
            onChangeText={(text) => handleInputChange('color', text)}
            style={styles.input}
            mode="outlined"
            testID="add-product-color-input"
          />

          <TextInput
            label="Technique"
            value={formData.technique}
            onChangeText={(text) => handleInputChange('technique', text)}
            style={styles.input}
            mode="outlined"
            placeholder="wheel-thrown, hand-built, slip-cast"
            testID="add-product-technique-input"
          />

          <TextInput
            label="Dimensions"
            value={formData.dimensions}
            onChangeText={(text) => handleInputChange('dimensions', text)}
            style={styles.input}
            mode="outlined"
            placeholder="24cm tall"
            testID="add-product-dimensions-input"
          />

        </Card>

        {/* Submit Button */}
        <View style={[styles.buttonContainer, { paddingBottom: Math.max(insets.bottom, spacing.xl) }]} testID="add-product-button-container">
          <Button
            mode="contained"
            onPress={handleSubmit}
            loading={isLoading || isUploading}
            disabled={isLoading || isUploading}
            style={styles.submitButton}
            contentStyle={{ height: 48 }}
            testID="add-product-submit-button"
          >
            {isUploading ? 'Uploading Images...' : isLoading ? (isEditMode ? 'Updating...' : 'Creating...') : (isEditMode ? 'Update Product' : 'Create Product')}
          </Button>
        </View>
      </ScrollView>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  header: {
    elevation: 2,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: spacing.md,
    fontSize: typography.sizes.md,
    color: colors.onSurfaceVariant,
  },
  content: {
    flex: 1,
    padding: spacing.md,
  },
  section: {
    marginBottom: spacing.lg,
    padding: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  input: {
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
  },
  errorText: {
    color: colors.error,
    fontSize: typography.sizes.sm,
    marginBottom: spacing.sm,
    marginTop: -spacing.xs,
  },
  primaryImagePreview: {
    width: '100%',
    height: 240,
    borderRadius: 8,
    marginBottom: spacing.md,
  },
  imageContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  imageWrapper: {
    position: 'relative',
  },
  image: {
    width: 110,
    height: 110,
    borderRadius: 8,
  },
  removeButton: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: colors.error,
    borderRadius: 12,
    width: 24,
    height: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  removeButtonText: {
    color: colors.onError,
    fontSize: 16,
    fontWeight: 'bold',
  },
  addImageButton: {
    width: 110,
    height: 110,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: colors.primary,
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#E3F2FD',
  },
  addImageText: {
    fontSize: 32,
    color: colors.primary,
    fontWeight: 'bold',
  },
  buttonContainer: {
    marginTop: spacing.lg,
  },
  submitButton: {
    backgroundColor: colors.primary,
  },
});