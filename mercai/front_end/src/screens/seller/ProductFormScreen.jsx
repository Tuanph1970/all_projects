import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Image,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Video } from 'expo-av';
import {
  Text,
  Appbar,
  TextInput,
  Button,
  Card,
  ActivityIndicator,
  Snackbar,
  Surface,
} from 'react-native-paper';
import { useNavigation, useRoute } from '@react-navigation/native';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerService from '../../services/sellerService.js';

export const ProductFormScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { capturedImage, mediaType } = route.params || {};
  
  const [loading, setLoading] = useState(false);
  const [snackbarVisible, setSnackbarVisible] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '',
    quantity_available: '',
    category_id: 1, // Default category - you might want to load categories
    dimensions: '',
    weight: '',
    material: '',
    color: '',
    technique: '',
    tags: '',
    minimum_order_quantity: '1',
  });

  const [errors, setErrors] = useState({});

  const showSnackbar = (message) => {
    setSnackbarMessage(message);
    setSnackbarVisible(true);
  };

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Product name is required';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }

    if (!formData.price.trim()) {
      newErrors.price = 'Price is required';
    } else if (isNaN(parseFloat(formData.price)) || parseFloat(formData.price) <= 0) {
      newErrors.price = 'Please enter a valid price';
    }

    if (!formData.quantity_available.trim()) {
      newErrors.quantity_available = 'Quantity is required';
    } else if (isNaN(parseInt(formData.quantity_available)) || parseInt(formData.quantity_available) < 0) {
      newErrors.quantity_available = 'Please enter a valid quantity';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      showSnackbar('Please fix the errors in the form');
      return;
    }

    try {
      setLoading(true);

      // First, upload the image
      let imageUrl = capturedImage;
      
      // If it's a local file URI, upload it to the server
      if (capturedImage && capturedImage.startsWith('file')) {
        try {
          // Create FormData for media upload
          const formDataForUpload = new FormData();
          const fileName = mediaType === 'photo' ? 'product-image.jpg' : 'product-video.mp4';
          const mimeType = mediaType === 'photo' ? 'image/jpeg' : 'video/mp4';
          
          formDataForUpload.append('file', {
            uri: capturedImage,
            type: mimeType,
            name: fileName,
          });

          const uploadResponse = await sellerService.uploadImage(formDataForUpload);
          imageUrl = uploadResponse.url;
        } catch (uploadError) {
          console.error('Error uploading image:', uploadError);
          showSnackbar('Failed to upload image. Using local image.');
          // Continue with local image URL
        }
      }

      // Prepare product data
      const productData = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        price: parseFloat(formData.price),
        quantity_available: parseInt(formData.quantity_available),
        category_id: parseInt(formData.category_id),
        dimensions: formData.dimensions.trim() || null,
        weight: formData.weight ? parseFloat(formData.weight) : null,
        material: formData.material.trim() || null,
        color: formData.color.trim() || null,
        technique: formData.technique.trim() || null,
        tags: formData.tags.trim() || null,
        minimum_order_quantity: parseInt(formData.minimum_order_quantity),
        images: [
          {
            url: imageUrl,
            alt_text: formData.name.trim(),
            is_primary: true,
            order_index: 0,
          }
        ],
      };

      // Create the product
      await sellerService.createProduct(productData);

      Alert.alert(
        'Success',
        'Product added successfully!',
        [
          {
            text: 'OK',
            onPress: () => {
              // Navigate back to product list
              navigation.navigate('MainTabs');
            },
          },
        ]
      );
    } catch (error) {
      console.error('Error creating product:', error);
      showSnackbar('Failed to create product. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="Add Product" />
      </Appbar.Header>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Product Media */}
        <Card style={styles.imageCard}>
          <Text style={styles.sectionTitle}>
            Product {mediaType === 'photo' ? 'Image' : 'Video'}
          </Text>
          <View style={styles.imageContainer}>
            {mediaType === 'photo' ? (
              <Image 
                source={{ uri: capturedImage }} 
                style={styles.productImage}
                resizeMode="cover"
              />
            ) : (
              <Video
                source={{ uri: capturedImage }}
                style={styles.productImage}
                shouldPlay={false}
                isLooping={false}
                resizeMode="cover"
              />
            )}
          </View>
        </Card>

        {/* Basic Information */}
        <Card style={styles.formCard}>
          <Text style={styles.sectionTitle}>Basic Information</Text>
          
          <TextInput
            label="Product Name *"
            value={formData.name}
            onChangeText={(text) => updateField('name', text)}
            style={styles.input}
            error={!!errors.name}
            mode="outlined"
            placeholder="Enter product name"
          />
          {errors.name && <Text style={styles.errorText}>{errors.name}</Text>}

          <TextInput
            label="Description *"
            value={formData.description}
            onChangeText={(text) => updateField('description', text)}
            style={styles.input}
            error={!!errors.description}
            mode="outlined"
            multiline
            numberOfLines={3}
            placeholder="Describe your product"
          />
          {errors.description && <Text style={styles.errorText}>{errors.description}</Text>}

          <View style={styles.row}>
            <TextInput
              label="Price ($) *"
              value={formData.price}
              onChangeText={(text) => updateField('price', text)}
              style={[styles.input, styles.halfInput]}
              error={!!errors.price}
              mode="outlined"
              keyboardType="decimal-pad"
              placeholder="0.00"
            />
            <TextInput
              label="Quantity *"
              value={formData.quantity_available}
              onChangeText={(text) => updateField('quantity_available', text)}
              style={[styles.input, styles.halfInput]}
              error={!!errors.quantity_available}
              mode="outlined"
              keyboardType="number-pad"
              placeholder="1"
            />
          </View>
          
          {errors.price && <Text style={styles.errorText}>{errors.price}</Text>}
          {errors.quantity_available && <Text style={styles.errorText}>{errors.quantity_available}</Text>}
        </Card>

        {/* Product Details */}
        <Card style={styles.formCard}>
          <Text style={styles.sectionTitle}>Product Details (Optional)</Text>

          <View style={styles.row}>
            <TextInput
              label="Dimensions"
              value={formData.dimensions}
              onChangeText={(text) => updateField('dimensions', text)}
              style={[styles.input, styles.halfInput]}
              mode="outlined"
              placeholder="e.g. 10x15x8 cm"
            />
            <TextInput
              label="Weight (kg)"
              value={formData.weight}
              onChangeText={(text) => updateField('weight', text)}
              style={[styles.input, styles.halfInput]}
              mode="outlined"
              keyboardType="decimal-pad"
              placeholder="0.5"
            />
          </View>

          <View style={styles.row}>
            <TextInput
              label="Material"
              value={formData.material}
              onChangeText={(text) => updateField('material', text)}
              style={[styles.input, styles.halfInput]}
              mode="outlined"
              placeholder="e.g. Ceramic"
            />
            <TextInput
              label="Color"
              value={formData.color}
              onChangeText={(text) => updateField('color', text)}
              style={[styles.input, styles.halfInput]}
              mode="outlined"
              placeholder="e.g. Blue"
            />
          </View>

          <TextInput
            label="Technique"
            value={formData.technique}
            onChangeText={(text) => updateField('technique', text)}
            style={styles.input}
            mode="outlined"
            placeholder="e.g. Hand-thrown, Glazed"
          />

          <TextInput
            label="Tags"
            value={formData.tags}
            onChangeText={(text) => updateField('tags', text)}
            style={styles.input}
            mode="outlined"
            placeholder="e.g. handmade, unique, ceramic"
            helper="Separate tags with commas"
          />

          <TextInput
            label="Minimum Order Quantity"
            value={formData.minimum_order_quantity}
            onChangeText={(text) => updateField('minimum_order_quantity', text)}
            style={styles.input}
            mode="outlined"
            keyboardType="number-pad"
            placeholder="1"
          />
        </Card>

        {/* Finish Button */}
        <Button
          mode="contained"
          onPress={handleSubmit}
          loading={loading}
          disabled={loading}
          style={styles.finishButton}
          contentStyle={styles.finishButtonContent}
        >
          {loading ? 'Creating Product...' : 'Finish'}
        </Button>

        <View style={styles.bottomPadding} />
      </ScrollView>

      <Snackbar
        visible={snackbarVisible}
        onDismiss={() => setSnackbarVisible(false)}
        duration={3000}
      >
        {snackbarMessage}
      </Snackbar>
    </KeyboardAvoidingView>
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
  content: {
    flex: 1,
    padding: spacing.md,
  },
  imageCard: {
    marginBottom: spacing.md,
    elevation: 2,
    backgroundColor: colors.surface,
  },
  formCard: {
    marginTop: spacing.md,
    padding: spacing.md,
    elevation: 2,
    backgroundColor: colors.surface,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  imageContainer: {
    borderRadius: 8,
    overflow: 'hidden',
    elevation: 1,
  },
  productImage: {
    width: '100%',
    height: 200,
    resizeMode: 'cover',
  },
  input: {
    marginBottom: spacing.md,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  halfInput: {
    flex: 0.48,
  },
  errorText: {
    color: colors.error,
    fontSize: typography.sizes.sm,
    marginBottom: spacing.sm,
    marginTop: -spacing.sm,
  },
  finishButton: {
    marginTop: spacing.lg,
    backgroundColor: colors.primary,
  },
  finishButtonContent: {
    height: 48,
  },
  bottomPadding: {
    height: spacing.xl,
  },
});