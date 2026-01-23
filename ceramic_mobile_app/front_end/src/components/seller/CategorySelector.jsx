/**
 * CategorySelector Component
 * A modal-based category picker with tree navigation for seller product forms
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  Modal,
  TouchableOpacity,
  FlatList,
  SafeAreaView,
} from 'react-native';
import {
  Text,
  TextInput,
  Button,
  ActivityIndicator,
  IconButton,
  Chip,
  Surface,
  Divider,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerCategoryService from '../../services/sellerCategoryService.js';

/**
 * CategorySelector - Modal picker for hierarchical categories
 *
 * @param {Object} props
 * @param {boolean} props.visible - Modal visibility
 * @param {Function} props.onClose - Close handler
 * @param {Function} props.onSelect - Selection handler (category) => void
 * @param {Object|null} props.selectedCategory - Currently selected category
 * @param {string} props.placeholder - Placeholder text for trigger
 * @param {boolean} props.showTrigger - Show built-in trigger button
 * @param {boolean} props.allowEmpty - Allow clearing selection
 */
export const CategorySelector = ({
  visible,
  onClose,
  onSelect,
  selectedCategory = null,
  placeholder = 'Select Category',
  showTrigger = false,
  allowEmpty = false,
}) => {
  const [isVisible, setIsVisible] = useState(visible);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [navigationStack, setNavigationStack] = useState([]); // [{id, name}, ...]
  const [currentParentId, setCurrentParentId] = useState(null);
  const [expandedIds, setExpandedIds] = useState(new Set());

  // Sync visibility with prop
  useEffect(() => {
    setIsVisible(visible);
    if (visible) {
      loadCategories();
    }
  }, [visible]);

  const loadCategories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await sellerCategoryService.getCategoryTree(false);
      setCategories(response.categories || []);
    } catch (err) {
      console.error('Failed to load categories:', err);
      setError('Failed to load categories');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleClose = () => {
    setIsVisible(false);
    setSearchQuery('');
    setNavigationStack([]);
    setCurrentParentId(null);
    onClose?.();
  };

  const handleSelect = (category) => {
    onSelect?.(category);
    handleClose();
  };

  const handleClear = () => {
    onSelect?.(null);
    handleClose();
  };

  const navigateToCategory = (category) => {
    if (category.children && category.children.length > 0) {
      setNavigationStack(prev => [...prev, { id: category.id, name: category.name }]);
      setCurrentParentId(category.id);
    }
  };

  const navigateBack = () => {
    if (navigationStack.length > 0) {
      const newStack = [...navigationStack];
      newStack.pop();
      setNavigationStack(newStack);
      setCurrentParentId(newStack.length > 0 ? newStack[newStack.length - 1].id : null);
    }
  };

  const navigateToRoot = () => {
    setNavigationStack([]);
    setCurrentParentId(null);
  };

  const toggleExpand = (categoryId) => {
    setExpandedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(categoryId)) {
        newSet.delete(categoryId);
      } else {
        newSet.add(categoryId);
      }
      return newSet;
    });
  };

  // Get current level categories based on navigation
  const getCurrentCategories = () => {
    if (searchQuery.trim()) {
      // Search mode - flatten and filter
      return flattenAndFilter(categories, searchQuery.toLowerCase());
    }

    if (currentParentId === null) {
      return categories;
    }

    // Find children of current parent
    return findChildren(categories, currentParentId);
  };

  const flattenAndFilter = (cats, query) => {
    const results = [];
    const flatten = (items, path = []) => {
      for (const cat of items) {
        const fullPath = [...path, cat.name];
        if (cat.name.toLowerCase().includes(query)) {
          results.push({ ...cat, fullPathName: fullPath.join(' > ') });
        }
        if (cat.children && cat.children.length > 0) {
          flatten(cat.children, fullPath);
        }
      }
    };
    flatten(cats);
    return results;
  };

  const findChildren = (cats, parentId) => {
    for (const cat of cats) {
      if (cat.id === parentId) {
        return cat.children || [];
      }
      if (cat.children && cat.children.length > 0) {
        const found = findChildren(cat.children, parentId);
        if (found.length > 0 || cat.children.some(c => c.id === parentId)) {
          return found.length > 0 ? found : cat.children.find(c => c.id === parentId)?.children || [];
        }
      }
    }
    return [];
  };

  const renderBreadcrumb = () => {
    if (navigationStack.length === 0) return null;

    return (
      <View style={styles.breadcrumb}>
        <TouchableOpacity onPress={navigateToRoot} style={styles.breadcrumbItem}>
          <Icon name="home" size={16} color={colors.primary} />
        </TouchableOpacity>
        {navigationStack.map((item, index) => (
          <React.Fragment key={item.id}>
            <Icon name="chevron-right" size={16} color={colors.textSecondary} />
            <TouchableOpacity
              onPress={() => {
                const newStack = navigationStack.slice(0, index + 1);
                setNavigationStack(newStack);
                setCurrentParentId(item.id);
              }}
              style={styles.breadcrumbItem}
            >
              <Text style={[
                styles.breadcrumbText,
                index === navigationStack.length - 1 && styles.breadcrumbTextActive
              ]}>
                {item.name}
              </Text>
            </TouchableOpacity>
          </React.Fragment>
        ))}
      </View>
    );
  };

  const renderCategoryItem = ({ item }) => {
    const hasChildren = item.children && item.children.length > 0;
    const isSelected = selectedCategory?.id === item.id;
    const levelIndicator = '  '.repeat((item.level || 1) - 1);

    return (
      <TouchableOpacity
        style={[styles.categoryItem, isSelected && styles.categoryItemSelected]}
        onPress={() => handleSelect(item)}
        activeOpacity={0.7}
      >
        <View style={styles.categoryItemContent}>
          {item.icon_url ? (
            <Image source={{ uri: item.icon_url }} style={styles.categoryIcon} />
          ) : (
            <View style={[styles.categoryIconPlaceholder, { backgroundColor: colors.primaryLight }]}>
              <Icon name="folder" size={20} color={colors.primary} />
            </View>
          )}
          <View style={styles.categoryInfo}>
            <Text style={[styles.categoryName, isSelected && styles.categoryNameSelected]}>
              {item.name}
            </Text>
            {item.fullPathName && (
              <Text style={styles.categoryPath} numberOfLines={1}>
                {item.fullPathName}
              </Text>
            )}
            {item.description && !item.fullPathName && (
              <Text style={styles.categoryDescription} numberOfLines={1}>
                {item.description}
              </Text>
            )}
          </View>
          {hasChildren && (
            <TouchableOpacity
              style={styles.expandButton}
              onPress={() => navigateToCategory(item)}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Icon name="chevron-right" size={24} color={colors.textSecondary} />
            </TouchableOpacity>
          )}
        </View>
        {item.level && (
          <View style={styles.levelBadge}>
            <Text style={styles.levelBadgeText}>L{item.level}</Text>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  const currentCategories = getCurrentCategories();

  // Trigger button (optional)
  const TriggerButton = () => (
    <TouchableOpacity
      style={styles.trigger}
      onPress={() => setIsVisible(true)}
      activeOpacity={0.7}
    >
      <View style={styles.triggerContent}>
        {selectedCategory ? (
          <>
            <Icon name="folder" size={20} color={colors.primary} style={styles.triggerIcon} />
            <Text style={styles.triggerText} numberOfLines={1}>
              {selectedCategory.full_path_name || selectedCategory.name}
            </Text>
          </>
        ) : (
          <>
            <Icon name="folder-open" size={20} color={colors.textSecondary} style={styles.triggerIcon} />
            <Text style={styles.triggerPlaceholder}>{placeholder}</Text>
          </>
        )}
      </View>
      <Icon name="arrow-drop-down" size={24} color={colors.textSecondary} />
    </TouchableOpacity>
  );

  return (
    <>
      {showTrigger && <TriggerButton />}

      <Modal
        visible={isVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={handleClose}
      >
        <SafeAreaView style={styles.modalContainer}>
          {/* Header */}
          <View style={styles.header}>
            <IconButton icon="close" onPress={handleClose} />
            <Text style={styles.headerTitle}>Select Category</Text>
            {allowEmpty && selectedCategory && (
              <Button mode="text" onPress={handleClear}>Clear</Button>
            )}
            {!allowEmpty && <View style={{ width: 48 }} />}
          </View>

          {/* Search */}
          <View style={styles.searchContainer}>
            <TextInput
              placeholder="Search categories..."
              value={searchQuery}
              onChangeText={setSearchQuery}
              mode="outlined"
              style={styles.searchInput}
              left={<TextInput.Icon icon="magnify" />}
              right={searchQuery ? (
                <TextInput.Icon icon="close" onPress={() => setSearchQuery('')} />
              ) : null}
            />
          </View>

          {/* Breadcrumb Navigation */}
          {!searchQuery && renderBreadcrumb()}

          {/* Back button for navigation */}
          {!searchQuery && navigationStack.length > 0 && (
            <TouchableOpacity style={styles.backButton} onPress={navigateBack}>
              <Icon name="arrow-back" size={20} color={colors.primary} />
              <Text style={styles.backButtonText}>Back</Text>
            </TouchableOpacity>
          )}

          <Divider />

          {/* Category List */}
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={colors.primary} />
              <Text style={styles.loadingText}>Loading categories...</Text>
            </View>
          ) : error ? (
            <View style={styles.errorContainer}>
              <Icon name="error-outline" size={48} color={colors.error} />
              <Text style={styles.errorText}>{error}</Text>
              <Button mode="outlined" onPress={loadCategories}>Retry</Button>
            </View>
          ) : currentCategories.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Icon name="folder-off" size={48} color={colors.textSecondary} />
              <Text style={styles.emptyText}>
                {searchQuery ? 'No categories found' : 'No categories yet'}
              </Text>
              {!searchQuery && (
                <Text style={styles.emptySubtext}>
                  Create categories in Category Management
                </Text>
              )}
            </View>
          ) : (
            <FlatList
              data={currentCategories}
              keyExtractor={(item) => item.id.toString()}
              renderItem={renderCategoryItem}
              style={styles.list}
              contentContainerStyle={styles.listContent}
              ItemSeparatorComponent={() => <Divider style={styles.separator} />}
            />
          )}

          {/* Selected Category Preview */}
          {selectedCategory && (
            <Surface style={styles.selectedPreview}>
              <Text style={styles.selectedLabel}>Selected:</Text>
              <Chip
                icon="folder"
                onClose={allowEmpty ? handleClear : undefined}
                style={styles.selectedChip}
              >
                {selectedCategory.full_path_name || selectedCategory.name}
              </Chip>
            </Surface>
          )}
        </SafeAreaView>
      </Modal>
    </>
  );
};

/**
 * CategorySelectorField - Form field wrapper for CategorySelector
 * Use this directly in forms
 */
export const CategorySelectorField = ({
  value,
  onChange,
  error,
  errorMessage,
  label = 'Category *',
  placeholder = 'Tap to select category',
}) => {
  const [modalVisible, setModalVisible] = useState(false);

  return (
    <View style={styles.fieldContainer}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TouchableOpacity
        style={[styles.fieldTrigger, error && styles.fieldTriggerError]}
        onPress={() => setModalVisible(true)}
        activeOpacity={0.7}
      >
        <View style={styles.fieldTriggerContent}>
          {value ? (
            <>
              <Icon name="folder" size={20} color={colors.primary} />
              <Text style={styles.fieldValue} numberOfLines={1}>
                {value.full_path_name || value.name}
              </Text>
            </>
          ) : (
            <>
              <Icon name="folder-open" size={20} color={colors.textSecondary} />
              <Text style={styles.fieldPlaceholder}>{placeholder}</Text>
            </>
          )}
        </View>
        <Icon name="arrow-drop-down" size={24} color={colors.textSecondary} />
      </TouchableOpacity>
      {error && errorMessage && (
        <Text style={styles.fieldError}>{errorMessage}</Text>
      )}

      <CategorySelector
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onSelect={onChange}
        selectedCategory={value}
        allowEmpty={true}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  // Modal
  modalContainer: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },

  // Search
  searchContainer: {
    padding: spacing.md,
    paddingTop: spacing.sm,
  },
  searchInput: {
    backgroundColor: colors.surface,
  },

  // Breadcrumb
  breadcrumb: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surfaceVariant,
    flexWrap: 'wrap',
  },
  breadcrumbItem: {
    paddingHorizontal: spacing.xs,
    paddingVertical: spacing.xs,
  },
  breadcrumbText: {
    fontSize: typography.sizes.sm,
    color: colors.primary,
  },
  breadcrumbTextActive: {
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },

  // Back button
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    backgroundColor: colors.surfaceVariant,
  },
  backButtonText: {
    marginLeft: spacing.sm,
    fontSize: typography.sizes.base,
    color: colors.primary,
    fontWeight: typography.weights.medium,
  },

  // List
  list: {
    flex: 1,
  },
  listContent: {
    paddingBottom: spacing.xl,
  },
  separator: {
    marginLeft: spacing.md + 40, // Align with text after icon
  },

  // Category Item
  categoryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.surface,
  },
  categoryItemSelected: {
    backgroundColor: colors.primaryLight,
  },
  categoryItemContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  categoryIcon: {
    width: 40,
    height: 40,
    borderRadius: 8,
  },
  categoryIconPlaceholder: {
    width: 40,
    height: 40,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  categoryInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  categoryName: {
    fontSize: typography.sizes.base,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
  },
  categoryNameSelected: {
    color: colors.primary,
    fontWeight: typography.weights.semibold,
  },
  categoryPath: {
    fontSize: typography.sizes.xs,
    color: colors.textSecondary,
    marginTop: 2,
  },
  categoryDescription: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginTop: 2,
  },
  expandButton: {
    padding: spacing.xs,
  },
  levelBadge: {
    backgroundColor: colors.surfaceVariant,
    paddingHorizontal: spacing.xs,
    paddingVertical: 2,
    borderRadius: 4,
    marginLeft: spacing.sm,
  },
  levelBadgeText: {
    fontSize: typography.sizes.xs,
    color: colors.textSecondary,
  },

  // Loading
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.textSecondary,
  },

  // Error
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  errorText: {
    marginTop: spacing.md,
    marginBottom: spacing.lg,
    color: colors.error,
    textAlign: 'center',
  },

  // Empty
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  emptyText: {
    marginTop: spacing.md,
    fontSize: typography.sizes.base,
    color: colors.textSecondary,
  },
  emptySubtext: {
    marginTop: spacing.sm,
    fontSize: typography.sizes.sm,
    color: colors.textTertiary,
    textAlign: 'center',
  },

  // Selected Preview
  selectedPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
  },
  selectedLabel: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginRight: spacing.sm,
  },
  selectedChip: {
    flex: 1,
  },

  // Trigger Button (optional built-in)
  trigger: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    backgroundColor: colors.surface,
  },
  triggerContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  triggerIcon: {
    marginRight: spacing.sm,
  },
  triggerText: {
    flex: 1,
    fontSize: typography.sizes.base,
    color: colors.onSurface,
  },
  triggerPlaceholder: {
    flex: 1,
    fontSize: typography.sizes.base,
    color: colors.textSecondary,
  },

  // Field wrapper
  fieldContainer: {
    marginBottom: spacing.md,
  },
  fieldLabel: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  fieldTrigger: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 4,
    backgroundColor: colors.surface,
  },
  fieldTriggerError: {
    borderColor: colors.error,
  },
  fieldTriggerContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  fieldValue: {
    flex: 1,
    fontSize: typography.sizes.base,
    color: colors.onSurface,
  },
  fieldPlaceholder: {
    flex: 1,
    fontSize: typography.sizes.base,
    color: colors.textSecondary,
  },
  fieldError: {
    color: colors.error,
    fontSize: typography.sizes.sm,
    marginTop: spacing.xs,
  },
});

export default CategorySelector;
