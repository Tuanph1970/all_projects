import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  TouchableOpacity,
  Image,
} from 'react-native';
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
import * as ImagePicker from 'expo-image-picker';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerService from '../../services/sellerService.js';
import { CategorySelectorField } from '../../components/seller/CategorySelector.jsx';

export const AddProductScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();

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
  });

  // Selected category (object with id, name, etc.)
  const [selectedCategory, setSelectedCategory] = useState(null);
  
  // Media state
  const [images, setImages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [loadingProduct, setLoadingProduct] = useState(false);

  // Form errors
  const [errors, setErrors] = useState({});

  useEffect(() => {
    requestPermissions();
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
      });

      // Set category if available
      if (product.seller_category_id) {
        setSelectedCategory({
          id: product.seller_category_id,
          name: product.seller_category?.name || 'Selected Category',
        });
      }

      // Load existing images
      if (product.images && product.images.length > 0) {
        setImages(product.images.map(img => ({
          uri: img.image_url,
          id: img.id,
          existing: true,
        })));
      }
    } catch (error) {
      console.error('Failed to load product:', error);
      Alert.alert('Error', 'Failed to load product data');
      navigation.goBack();
    } finally {
      setLoadingProduct(false);
    }
  };

  const requestPermissions = async () => {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert(
          'Permission Required',
          'Sorry, we need camera roll permissions to upload images.'
        );
      }
    } catch (error) {
      console.error('Error requesting permissions:', error);
    }
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

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled && result.assets.length > 0) {
        setImages(prev => [...prev, result.assets[0]]);
      }
    } catch (error) {
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

      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert(
          'Permission Required',
          'Camera permission is required to take photos.'
        );
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled && result.assets.length > 0) {
        setImages(prev => [...prev, result.assets[0]]);
      }
    } catch (error) {
      console.error('Error taking photo:', error);
      Alert.alert('Error', 'Failed to capture photo. Please try again.');
    }
  };

  const removeImage = (index) => {
    setImages(prev => prev.filter((_, i) => i !== index));
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
        </Card>

        {/* Submit Button */}
        <View style={styles.buttonContainer} testID="add-product-button-container">
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
  imageContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  imageWrapper: {
    position: 'relative',
  },
  image: {
    width: 80,
    height: 80,
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
    width: 80,
    height: 80,
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
    marginBottom: spacing.xl,
  },
  submitButton: {
    backgroundColor: colors.primary,
  },
});