/**
 * CategoryFormScreen
 * Add/Edit category form for sellers
 * Used for both AddCategory and EditCategory routes
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import {
  Text,
  Appbar,
  TextInput,
  Button,
  Card,
  Switch,
  ActivityIndicator,
  HelperText,
  Divider,
  Chip,
} from 'react-native-paper';
import { useNavigation, useRoute } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerCategoryService from '../../services/sellerCategoryService.js';
import { CategorySelectorField } from '../../components/seller/CategorySelector.jsx';

const MAX_DEPTH = 4;

export const CategoryFormScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();

  // Determine if editing or creating
  const editCategory = route.params?.category;
  const parentCategory = route.params?.parentCategory;
  const isEditing = !!editCategory;

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    description: '',
    icon_url: '',
    image_url: '',
    is_active: true,
    display_order: 0,
  });
  const [selectedParent, setSelectedParent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});

  // Initialize form data
  useEffect(() => {
    if (isEditing && editCategory) {
      setFormData({
        name: editCategory.name || '',
        slug: editCategory.slug || '',
        description: editCategory.description || '',
        icon_url: editCategory.icon_url || '',
        image_url: editCategory.image_url || '',
        is_active: editCategory.is_active ?? true,
        display_order: editCategory.display_order || 0,
      });
      // Load parent info if editing
      if (editCategory.parent_id) {
        loadParentCategory(editCategory.parent_id);
      }
    } else if (parentCategory) {
      setSelectedParent(parentCategory);
    }
  }, [isEditing, editCategory, parentCategory]);

  const loadParentCategory = async (parentId) => {
    try {
      const parent = await sellerCategoryService.getCategory(parentId, false);
      setSelectedParent(parent);
    } catch (err) {
      console.error('Failed to load parent category:', err);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));

    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: '',
      }));
    }

    // Auto-generate slug from name
    if (field === 'name' && !isEditing) {
      const slug = value
        .toLowerCase()
        .trim()
        .replace(/[^\w\s-]/g, '')
        .replace(/[-\s]+/g, '-')
        .substring(0, 120);
      setFormData(prev => ({ ...prev, slug }));
    }
  };

  const handleParentChange = (parent) => {
    setSelectedParent(parent);
    if (errors.parent) {
      setErrors(prev => ({ ...prev, parent: '' }));
    }
  };

  const calculateNewLevel = () => {
    if (selectedParent) {
      return selectedParent.level + 1;
    }
    return 1;
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Category name is required';
    } else if (formData.name.trim().length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    } else if (formData.name.trim().length > 100) {
      newErrors.name = 'Name must be less than 100 characters';
    }

    // Check level constraint
    const newLevel = calculateNewLevel();
    if (newLevel > MAX_DEPTH) {
      newErrors.parent = `Cannot create category at level ${newLevel}. Maximum depth is ${MAX_DEPTH}.`;
    }

    // When editing, prevent moving to own descendant
    if (isEditing && selectedParent) {
      if (selectedParent.path && editCategory.path) {
        if (selectedParent.path.startsWith(`${editCategory.path}/`) || selectedParent.id === editCategory.id) {
          newErrors.parent = 'Cannot move category to its own descendant';
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setSaving(true);

    try {
      const categoryData = {
        name: formData.name.trim(),
        slug: formData.slug.trim() || null,
        description: formData.description.trim() || null,
        icon_url: formData.icon_url.trim() || null,
        image_url: formData.image_url.trim() || null,
        is_active: formData.is_active,
        display_order: parseInt(formData.display_order) || 0,
      };

      if (isEditing) {
        // Include parent_id only if changed
        if (selectedParent?.id !== editCategory.parent_id) {
          categoryData.parent_id = selectedParent?.id || null;
        }
        await sellerCategoryService.updateCategory(editCategory.id, categoryData);
        Alert.alert('Success', 'Category updated successfully', [
          { text: 'OK', onPress: () => navigation.goBack() }
        ]);
      } else {
        categoryData.parent_id = selectedParent?.id || null;
        await sellerCategoryService.createCategory(categoryData);
        Alert.alert('Success', 'Category created successfully', [
          { text: 'Add Another', onPress: resetForm },
          { text: 'Done', onPress: () => navigation.goBack() }
        ]);
      }
    } catch (err) {
      console.error('Failed to save category:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to save category';
      Alert.alert('Error', errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      slug: '',
      description: '',
      icon_url: '',
      image_url: '',
      is_active: true,
      display_order: 0,
    });
    if (!parentCategory) {
      setSelectedParent(null);
    }
    setErrors({});
  };

  const newLevel = calculateNewLevel();

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={isEditing ? 'Edit Category' : 'Add Category'} />
      </Appbar.Header>

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
          {/* Level Indicator */}
          <Card style={styles.levelCard}>
            <View style={styles.levelContent}>
              <Icon name="layers" size={24} color={colors.primary} />
              <View style={styles.levelInfo}>
                <Text style={styles.levelLabel}>Category Level</Text>
                <View style={styles.levelIndicator}>
                  {[1, 2, 3, 4].map(level => (
                    <View
                      key={level}
                      style={[
                        styles.levelDot,
                        level <= newLevel ? styles.levelDotActive : styles.levelDotInactive,
                        level === newLevel && styles.levelDotCurrent,
                      ]}
                    >
                      <Text style={[
                        styles.levelDotText,
                        level <= newLevel && styles.levelDotTextActive,
                      ]}>
                        {level}
                      </Text>
                    </View>
                  ))}
                </View>
              </View>
              <Chip style={styles.levelChip}>Level {newLevel}</Chip>
            </View>
            {newLevel >= MAX_DEPTH && (
              <Text style={styles.levelWarning}>
                This is the maximum depth. Cannot add subcategories.
              </Text>
            )}
          </Card>

          {/* Parent Category */}
          <Card style={styles.section}>
            <Text style={styles.sectionTitle}>Parent Category</Text>
            <CategorySelectorField
              value={selectedParent}
              onChange={handleParentChange}
              error={!!errors.parent}
              errorMessage={errors.parent}
              label="Parent Category (optional)"
              placeholder="Select parent (leave empty for root)"
            />
            <HelperText type="info" visible={!errors.parent}>
              Leave empty to create a root-level category
            </HelperText>
          </Card>

          {/* Category Details */}
          <Card style={styles.section}>
            <Text style={styles.sectionTitle}>Category Details</Text>

            <TextInput
              label="Category Name *"
              value={formData.name}
              onChangeText={(text) => handleInputChange('name', text)}
              style={styles.input}
              mode="outlined"
              error={!!errors.name}
              maxLength={100}
            />
            <HelperText type="error" visible={!!errors.name}>
              {errors.name}
            </HelperText>

            <TextInput
              label="URL Slug"
              value={formData.slug}
              onChangeText={(text) => handleInputChange('slug', text)}
              style={styles.input}
              mode="outlined"
              placeholder="auto-generated-from-name"
              maxLength={120}
            />
            <HelperText type="info">
              URL-friendly identifier. Auto-generated from name if left empty.
            </HelperText>

            <TextInput
              label="Description"
              value={formData.description}
              onChangeText={(text) => handleInputChange('description', text)}
              style={styles.input}
              mode="outlined"
              multiline
              numberOfLines={3}
            />
          </Card>

          {/* Images */}
          <Card style={styles.section}>
            <Text style={styles.sectionTitle}>Images (Optional)</Text>

            <TextInput
              label="Icon URL"
              value={formData.icon_url}
              onChangeText={(text) => handleInputChange('icon_url', text)}
              style={styles.input}
              mode="outlined"
              placeholder="https://example.com/icon.png"
              autoCapitalize="none"
            />

            <TextInput
              label="Image URL"
              value={formData.image_url}
              onChangeText={(text) => handleInputChange('image_url', text)}
              style={styles.input}
              mode="outlined"
              placeholder="https://example.com/image.jpg"
              autoCapitalize="none"
            />
          </Card>

          {/* Settings */}
          <Card style={styles.section}>
            <Text style={styles.sectionTitle}>Settings</Text>

            <View style={styles.switchRow}>
              <View style={styles.switchInfo}>
                <Text style={styles.switchLabel}>Active</Text>
                <Text style={styles.switchDescription}>
                  Inactive categories won't be shown in product forms
                </Text>
              </View>
              <Switch
                value={formData.is_active}
                onValueChange={(value) => handleInputChange('is_active', value)}
                color={colors.primary}
              />
            </View>

            <Divider style={styles.divider} />

            <TextInput
              label="Display Order"
              value={formData.display_order.toString()}
              onChangeText={(text) => {
                const num = parseInt(text) || 0;
                handleInputChange('display_order', num);
              }}
              style={styles.input}
              mode="outlined"
              keyboardType="numeric"
            />
            <HelperText type="info">
              Lower numbers appear first. Categories with same order are sorted alphabetically.
            </HelperText>
          </Card>

          {/* Submit Button */}
          <View style={styles.buttonContainer}>
            <Button
              mode="contained"
              onPress={handleSubmit}
              loading={saving}
              disabled={saving}
              style={styles.submitButton}
              contentStyle={styles.submitButtonContent}
            >
              {saving
                ? (isEditing ? 'Updating...' : 'Creating...')
                : (isEditing ? 'Update Category' : 'Create Category')
              }
            </Button>

            <Button
              mode="outlined"
              onPress={() => navigation.goBack()}
              style={styles.cancelButton}
              disabled={saving}
            >
              Cancel
            </Button>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
};

// Export aliases for navigation
export const AddCategoryScreen = CategoryFormScreen;
export const EditCategoryScreen = CategoryFormScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    elevation: 2,
  },
  keyboardView: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
    padding: spacing.md,
  },

  // Level Card
  levelCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  levelContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  levelInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  levelLabel: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
  },
  levelIndicator: {
    flexDirection: 'row',
    marginTop: spacing.xs,
    gap: spacing.sm,
  },
  levelDot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  levelDotInactive: {
    backgroundColor: colors.surfaceVariant,
  },
  levelDotActive: {
    backgroundColor: colors.primaryLight,
  },
  levelDotCurrent: {
    backgroundColor: colors.primary,
  },
  levelDotText: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.textSecondary,
  },
  levelDotTextActive: {
    color: colors.primary,
  },
  levelChip: {
    backgroundColor: colors.primaryLight,
  },
  levelWarning: {
    marginTop: spacing.sm,
    fontSize: typography.sizes.sm,
    color: colors.warning,
    fontStyle: 'italic',
  },

  // Section
  section: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.base,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },

  // Input
  input: {
    marginBottom: spacing.xs,
    backgroundColor: colors.surface,
  },

  // Switch Row
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  switchInfo: {
    flex: 1,
    marginRight: spacing.md,
  },
  switchLabel: {
    fontSize: typography.sizes.base,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
  },
  switchDescription: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginTop: 2,
  },
  divider: {
    marginVertical: spacing.md,
  },

  // Buttons
  buttonContainer: {
    marginTop: spacing.lg,
    marginBottom: spacing.xl,
  },
  submitButton: {
    backgroundColor: colors.primary,
  },
  submitButtonContent: {
    height: 48,
  },
  cancelButton: {
    marginTop: spacing.sm,
  },
});

export default CategoryFormScreen;
