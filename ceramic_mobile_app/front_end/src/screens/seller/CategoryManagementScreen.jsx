/**
 * CategoryManagementScreen
 * Seller's product category management with tree view
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import {
  Text,
  Appbar,
  FAB,
  Card,
  IconButton,
  Menu,
  Divider,
  Button,
  ActivityIndicator,
  Chip,
  Surface,
  Snackbar,
} from 'react-native-paper';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerCategoryService from '../../services/sellerCategoryService.js';

const MAX_DEPTH = 4;

export const CategoryManagementScreen = () => {
  const navigation = useNavigation();

  // State
  const [categories, setCategories] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [expandedIds, setExpandedIds] = useState(new Set());
  const [menuVisible, setMenuVisible] = useState(null); // category id with open menu
  const [snackbar, setSnackbar] = useState({ visible: false, message: '' });

  // Load data on focus
  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [])
  );

  const loadData = async () => {
    try {
      setError(null);
      const [treeResponse, statsResponse] = await Promise.all([
        sellerCategoryService.getCategoryTree(true), // Include inactive
        sellerCategoryService.getCategoryStats(),
      ]);
      setCategories(treeResponse.categories || []);
      setStats(statsResponse);
    } catch (err) {
      console.error('Failed to load categories:', err);
      setError('Failed to load categories');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
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

  const expandAll = () => {
    const allIds = new Set();
    const collectIds = (cats) => {
      for (const cat of cats) {
        if (cat.children && cat.children.length > 0) {
          allIds.add(cat.id);
          collectIds(cat.children);
        }
      }
    };
    collectIds(categories);
    setExpandedIds(allIds);
  };

  const collapseAll = () => {
    setExpandedIds(new Set());
  };

  const handleAddCategory = (parentCategory = null) => {
    setMenuVisible(null);
    navigation.navigate('AddCategory', { parentCategory });
  };

  const handleEditCategory = (category) => {
    setMenuVisible(null);
    navigation.navigate('EditCategory', { category });
  };

  const handleDeleteCategory = (category) => {
    setMenuVisible(null);

    const hasChildren = category.children && category.children.length > 0;

    Alert.alert(
      'Delete Category',
      hasChildren
        ? `"${category.name}" has ${category.children.length} subcategories. Do you want to delete all of them?`
        : `Are you sure you want to delete "${category.name}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        ...(hasChildren ? [{
          text: 'Delete All',
          style: 'destructive',
          onPress: () => deleteCategory(category.id, true),
        }] : []),
        {
          text: hasChildren ? 'Delete Only This' : 'Delete',
          style: 'destructive',
          onPress: () => deleteCategory(category.id, false),
        },
      ]
    );
  };

  const deleteCategory = async (categoryId, cascade) => {
    try {
      await sellerCategoryService.deleteCategory(categoryId, cascade);
      setSnackbar({ visible: true, message: 'Category deleted successfully' });
      loadData();
    } catch (err) {
      console.error('Failed to delete category:', err);
      Alert.alert('Error', err.message || 'Failed to delete category');
    }
  };

  const handleToggleActive = async (category) => {
    setMenuVisible(null);
    try {
      await sellerCategoryService.updateCategory(category.id, {
        is_active: !category.is_active,
      });
      setSnackbar({
        visible: true,
        message: `Category ${category.is_active ? 'deactivated' : 'activated'}`,
      });
      loadData();
    } catch (err) {
      console.error('Failed to toggle category status:', err);
      Alert.alert('Error', 'Failed to update category status');
    }
  };

  const handleDuplicate = async (category) => {
    setMenuVisible(null);
    try {
      await sellerCategoryService.duplicateCategory(category.id, false);
      setSnackbar({ visible: true, message: 'Category duplicated' });
      loadData();
    } catch (err) {
      console.error('Failed to duplicate category:', err);
      Alert.alert('Error', 'Failed to duplicate category');
    }
  };

  const renderStatsCard = () => {
    if (!stats) return null;

    return (
      <Card style={styles.statsCard}>
        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{stats.total_categories}</Text>
            <Text style={styles.statLabel}>Total</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{stats.active_categories}</Text>
            <Text style={styles.statLabel}>Active</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{stats.root_categories}</Text>
            <Text style={styles.statLabel}>Root</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{stats.max_depth_used}/{MAX_DEPTH}</Text>
            <Text style={styles.statLabel}>Depth</Text>
          </View>
        </View>
      </Card>
    );
  };

  const renderCategoryItem = (category, depth = 0) => {
    const hasChildren = category.children && category.children.length > 0;
    const isExpanded = expandedIds.has(category.id);
    const canAddChild = category.level < MAX_DEPTH;

    return (
      <View key={category.id}>
        <TouchableOpacity
          style={[
            styles.categoryItem,
            { marginLeft: depth * 20 },
            !category.is_active && styles.categoryItemInactive,
          ]}
          onPress={() => hasChildren && toggleExpand(category.id)}
          onLongPress={() => setMenuVisible(category.id)}
          activeOpacity={0.7}
        >
          {/* Expand/Collapse Icon */}
          <View style={styles.expandIconContainer}>
            {hasChildren ? (
              <Icon
                name={isExpanded ? 'expand-more' : 'chevron-right'}
                size={24}
                color={colors.textSecondary}
              />
            ) : (
              <View style={styles.expandIconPlaceholder} />
            )}
          </View>

          {/* Category Icon */}
          <View style={[
            styles.categoryIcon,
            { backgroundColor: category.is_active ? colors.primaryLight : colors.surfaceVariant }
          ]}>
            <Icon
              name="folder"
              size={20}
              color={category.is_active ? colors.primary : colors.textSecondary}
            />
          </View>

          {/* Category Info */}
          <View style={styles.categoryInfo}>
            <View style={styles.categoryHeader}>
              <Text style={[
                styles.categoryName,
                !category.is_active && styles.categoryNameInactive
              ]}>
                {category.name}
              </Text>
              <Chip
                style={[styles.levelChip, !category.is_active && styles.levelChipInactive]}
                textStyle={styles.levelChipText}
              >
                L{category.level}
              </Chip>
            </View>
            {category.description && (
              <Text style={styles.categoryDescription} numberOfLines={1}>
                {category.description}
              </Text>
            )}
            <View style={styles.categoryMeta}>
              {!category.is_active && (
                <Chip
                  style={styles.inactiveChip}
                  textStyle={styles.inactiveChipText}
                  icon="eye-off"
                >
                  Inactive
                </Chip>
              )}
              {hasChildren && (
                <Text style={styles.childCount}>
                  {category.children.length} subcategories
                </Text>
              )}
            </View>
          </View>

          {/* Actions Menu */}
          <Menu
            visible={menuVisible === category.id}
            onDismiss={() => setMenuVisible(null)}
            anchor={
              <IconButton
                icon="dots-vertical"
                size={20}
                onPress={() => setMenuVisible(category.id)}
              />
            }
          >
            <Menu.Item
              leadingIcon="pencil"
              onPress={() => handleEditCategory(category)}
              title="Edit"
            />
            {canAddChild && (
              <Menu.Item
                leadingIcon="folder-plus"
                onPress={() => handleAddCategory(category)}
                title="Add Subcategory"
              />
            )}
            <Menu.Item
              leadingIcon="content-copy"
              onPress={() => handleDuplicate(category)}
              title="Duplicate"
            />
            <Menu.Item
              leadingIcon={category.is_active ? 'eye-off' : 'eye'}
              onPress={() => handleToggleActive(category)}
              title={category.is_active ? 'Deactivate' : 'Activate'}
            />
            <Divider />
            <Menu.Item
              leadingIcon="delete"
              onPress={() => handleDeleteCategory(category)}
              title="Delete"
              titleStyle={{ color: colors.error }}
            />
          </Menu>
        </TouchableOpacity>

        {/* Children */}
        {hasChildren && isExpanded && (
          <View style={styles.childrenContainer}>
            {category.children.map(child => renderCategoryItem(child, depth + 1))}
          </View>
        )}
      </View>
    );
  };

  const renderEmptyState = () => (
    <View style={styles.emptyContainer}>
      <Icon name="folder-open" size={64} color={colors.textSecondary} />
      <Text style={styles.emptyTitle}>No Categories Yet</Text>
      <Text style={styles.emptySubtitle}>
        Create categories to organize your products
      </Text>
      <Button
        mode="contained"
        icon="plus"
        onPress={() => handleAddCategory()}
        style={styles.emptyButton}
      >
        Create First Category
      </Button>
    </View>
  );

  const renderContent = () => {
    if (loading) {
      return (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading categories...</Text>
        </View>
      );
    }

    if (error) {
      return (
        <View style={styles.errorContainer}>
          <Icon name="error-outline" size={48} color={colors.error} />
          <Text style={styles.errorText}>{error}</Text>
          <Button mode="outlined" onPress={loadData}>Retry</Button>
        </View>
      );
    }

    if (categories.length === 0) {
      return renderEmptyState();
    }

    return (
      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
          />
        }
      >
        {renderStatsCard()}

        {/* Expand/Collapse Controls */}
        <View style={styles.expandControls}>
          <Button
            mode="text"
            icon="unfold-more-horizontal"
            onPress={expandAll}
            compact
          >
            Expand All
          </Button>
          <Button
            mode="text"
            icon="unfold-less-horizontal"
            onPress={collapseAll}
            compact
          >
            Collapse All
          </Button>
        </View>

        {/* Category Tree */}
        <Card style={styles.treeCard}>
          {categories.map(category => renderCategoryItem(category))}
        </Card>

        {/* Bottom spacing for FAB */}
        <View style={{ height: 80 }} />
      </ScrollView>
    );
  };

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="Categories" subtitle={`${stats?.total_categories || 0} total`} />
        <Appbar.Action icon="refresh" onPress={handleRefresh} />
      </Appbar.Header>

      {renderContent()}

      <FAB
        icon="plus"
        style={styles.fab}
        onPress={() => handleAddCategory()}
        label="Add Category"
      />

      <Snackbar
        visible={snackbar.visible}
        onDismiss={() => setSnackbar({ visible: false, message: '' })}
        duration={3000}
        action={{
          label: 'OK',
          onPress: () => setSnackbar({ visible: false, message: '' }),
        }}
      >
        {snackbar.message}
      </Snackbar>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    elevation: 2,
  },
  scrollView: {
    flex: 1,
  },

  // Stats Card
  statsCard: {
    margin: spacing.md,
    padding: spacing.md,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.bold,
    color: colors.primary,
  },
  statLabel: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 40,
    backgroundColor: colors.border,
  },

  // Expand Controls
  expandControls: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    paddingHorizontal: spacing.md,
    marginBottom: spacing.sm,
  },

  // Tree Card
  treeCard: {
    marginHorizontal: spacing.md,
    marginBottom: spacing.md,
    paddingVertical: spacing.sm,
  },

  // Category Item
  categoryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.surface,
  },
  categoryItemInactive: {
    opacity: 0.7,
  },
  expandIconContainer: {
    width: 24,
    alignItems: 'center',
  },
  expandIconPlaceholder: {
    width: 24,
  },
  categoryIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: spacing.sm,
  },
  categoryInfo: {
    flex: 1,
  },
  categoryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  categoryName: {
    fontSize: typography.sizes.base,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    flex: 1,
  },
  categoryNameInactive: {
    color: colors.textSecondary,
  },
  levelChip: {
    height: 20,
    backgroundColor: colors.primaryLight,
  },
  levelChipInactive: {
    backgroundColor: colors.surfaceVariant,
  },
  levelChipText: {
    fontSize: 10,
    marginHorizontal: 4,
    marginVertical: 0,
  },
  categoryDescription: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginTop: 2,
  },
  categoryMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
    gap: spacing.sm,
  },
  inactiveChip: {
    height: 20,
    backgroundColor: colors.warningLight,
  },
  inactiveChipText: {
    fontSize: 10,
    color: colors.warning,
  },
  childCount: {
    fontSize: typography.sizes.xs,
    color: colors.textSecondary,
  },
  childrenContainer: {
    borderLeftWidth: 1,
    borderLeftColor: colors.border,
    marginLeft: 32,
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
  emptyTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginTop: spacing.lg,
  },
  emptySubtitle: {
    fontSize: typography.sizes.base,
    color: colors.textSecondary,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  emptyButton: {
    marginTop: spacing.xl,
  },

  // FAB
  fab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
    backgroundColor: colors.primary,
  },
});

export default CategoryManagementScreen;
