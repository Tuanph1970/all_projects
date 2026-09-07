import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, FlatList, Alert, RefreshControl, Modal, TextInput as RNTextInput } from 'react-native';
import {
  Text,
  Appbar,
  Searchbar,
  FAB,
  Menu,
  Divider,
  Checkbox,
  Button,
  Surface,
  Chip,
  IconButton,
  Card,
  ActivityIndicator,
  Snackbar,
  Portal,
  TextInput
} from 'react-native-paper';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerService from '../../services/sellerService.js';
import intelService from '../../services/intelService.js';
import { useTranslation } from '@i18n';

export const ProductManagementScreen = () => {
  const navigation = useNavigation();
  const t = useTranslation();
  const [products, setProducts] = useState([]);
  const [priceIntelAvailable, setPriceIntelAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProducts, setSelectedProducts] = useState(new Set());
  const [bulkMenuVisible, setBulkMenuVisible] = useState(false);
  const [filterMenuVisible, setFilterMenuVisible] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [snackbarVisible, setSnackbarVisible] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  // Price update modal
  const [priceModalVisible, setPriceModalVisible] = useState(false);
  const [priceUpdateType, setPriceUpdateType] = useState('fixed'); // 'fixed' or 'percentage'
  const [priceUpdateValue, setPriceUpdateValue] = useState('');

  // Filters
  const [statusFilter, setStatusFilter] = useState('active');
  const [stockFilter, setStockFilter] = useState('all');

  useEffect(() => {
    loadProducts(true);
  }, [searchQuery, statusFilter, stockFilter]);

  // Hide the price-insights control entirely when the feature is off for this
  // seller -- better than a button that 404s when tapped. Never throws.
  useEffect(() => {
    let cancelled = false;
    intelService.isPriceIntelAvailable().then((ok) => {
      if (!cancelled) setPriceIntelAvailable(ok);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  // Reload products when screen comes into focus (e.g., after adding/editing a product)
  useFocusEffect(
    useCallback(() => {
      loadProducts(true);
    }, [])
  );

  const loadProducts = async (reset = false) => {
    try {
      if (reset) {
        setLoading(true);
        setCurrentPage(1);
      }

      const page = reset ? 1 : currentPage;
      const response = await sellerService.getProductsForManagement({
        page: page,
        per_page: 20,
        search: searchQuery,
        status: statusFilter,
        stock_status: stockFilter,
        sort_by: 'created_at',
        sort_order: 'desc',
        low_stock_threshold: 10
      });

      if (reset) {
        setProducts(response.products || []);
      } else {
        setProducts(prev => [...prev, ...(response.products || [])]);
      }

      setHasMore(response.pagination?.has_next || false);
      setSelectedProducts(new Set());
    } catch (error) {
      console.error('Failed to load products:', error);
      showSnackbar(t('productManagement.loadError'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadMore = () => {
    if (hasMore && !loading) {
      setCurrentPage(prev => prev + 1);
      loadProducts(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadProducts(true);
  };

  const showSnackbar = (message) => {
    setSnackbarMessage(message);
    setSnackbarVisible(true);
  };

  const toggleProductSelection = (productId) => {
    const newSelection = new Set(selectedProducts);
    if (newSelection.has(productId)) {
      newSelection.delete(productId);
    } else {
      newSelection.add(productId);
    }
    setSelectedProducts(newSelection);
  };

  const selectAllVisible = () => {
    const allVisible = new Set(products.map(p => p.id));
    setSelectedProducts(allVisible);
  };

  const clearSelection = () => {
    setSelectedProducts(new Set());
  };

  const handleBulkAction = async (action) => {
    const selectedIds = Array.from(selectedProducts);
    if (selectedIds.length === 0) {
      showSnackbar(t('productManagement.selectProductsFirst'));
      return;
    }

    try {
      setBulkMenuVisible(false);
      
      switch (action) {
        case 'activate':
          await sellerService.bulkUpdateStatus(selectedIds, true);
          showSnackbar(t('productManagement.activatedProducts', { count: selectedIds.length }));
          break;
        case 'deactivate':
          await sellerService.bulkUpdateStatus(selectedIds, false);
          showSnackbar(t('productManagement.deactivatedProducts', { count: selectedIds.length }));
          break;
        case 'feature':
          await sellerService.bulkUpdateFeatured(selectedIds, true);
          showSnackbar(t('productManagement.featuredProducts', { count: selectedIds.length }));
          break;
        case 'unfeature':
          await sellerService.bulkUpdateFeatured(selectedIds, false);
          showSnackbar(t('productManagement.unfeaturedProducts', { count: selectedIds.length }));
          break;
        case 'updatePrice':
          setPriceModalVisible(true);
          return;
        case 'delete':
          Alert.alert(
            t('productManagement.deleteProducts'),
            t('productManagement.deleteConfirm', { count: selectedIds.length }),
            [
              { text: t('common.cancel'), style: 'cancel' },
              {
                text: t('common.delete'),
                style: 'destructive',
                onPress: async () => {
                  try {
                    for (const id of selectedIds) {
                      await sellerService.deleteProduct(id);
                    }
                    showSnackbar(t('productManagement.deletedProducts', { count: selectedIds.length }));
                    loadProducts(true);
                  } catch (error) {
                    console.error('Delete failed:', error);
                    showSnackbar(t('productManagement.failedDeleteProducts'));
                  }
                }
              }
            ]
          );
          return;
        default:
          return;
      }

      loadProducts(true);
    } catch (error) {
      console.error('Bulk action failed:', error);
      showSnackbar(t('productManagement.bulkActionFailed'));
    }
  };

  const handlePriceUpdate = async () => {
    const selectedIds = Array.from(selectedProducts);
    const value = parseFloat(priceUpdateValue);

    console.log('[DEBUG] handlePriceUpdate called');
    console.log('[DEBUG] selectedIds:', selectedIds);
    console.log('[DEBUG] priceUpdateType:', priceUpdateType);
    console.log('[DEBUG] priceUpdateValue:', priceUpdateValue);
    console.log('[DEBUG] parsed value:', value);

    if (isNaN(value) || (priceUpdateType === 'fixed' && value <= 0)) {
      console.log('[DEBUG] Invalid value, showing error');
      showSnackbar('Please enter a valid price value');
      return;
    }

    try {
      setPriceModalVisible(false);

      // Build updates array for bulk operation
      const updates = [];
      for (const productId of selectedIds) {
        const product = products.find(p => p.id === productId);
        console.log('[DEBUG] Processing product:', productId, product?.name, 'current price:', product?.price);
        if (product) {
          let newPrice;
          if (priceUpdateType === 'fixed') {
            newPrice = value;
          } else {
            // Percentage: positive = increase, negative = decrease
            newPrice = product.price * (1 + value / 100);
          }
          newPrice = Math.max(0.01, Math.round(newPrice * 100) / 100); // Ensure min price and round to 2 decimals

          console.log('[DEBUG] New price calculated:', newPrice);
          updates.push({
            product_id: productId,
            price: newPrice
          });
        }
      }

      console.log('[DEBUG] Updates array:', JSON.stringify(updates));
      console.log('[DEBUG] Calling sellerService.bulkUpdatePrices...');

      // Use bulk update API
      const response = await sellerService.bulkUpdatePrices(updates);
      console.log('[DEBUG] bulkUpdatePrices response:', JSON.stringify(response));

      showSnackbar(`Updated prices for ${selectedIds.length} product(s)`);
      setPriceUpdateValue('');
      loadProducts(true);
    } catch (error) {
      console.error('[DEBUG] Price update failed:', error);
      console.error('[DEBUG] Error message:', error.message);
      console.error('[DEBUG] Error response:', error.response?.data);
      console.error('[DEBUG] Error status:', error.response?.status);
      showSnackbar('Failed to update prices');
    }
  };

  const getStatusColor = (product) => {
    if (!product.is_active) return colors.outline;
    if (product.stock_status === 'out_of_stock') return colors.error;
    if (product.stock_status === 'low_stock') return colors.warning || '#FF9800';
    return colors.success || '#4CAF50';
  };

  const getStatusText = (product) => {
    if (!product.is_active) return t('productManagement.inactive');
    if (product.stock_status === 'out_of_stock') return t('productManagement.outOfStock');
    if (product.stock_status === 'low_stock') return t('productManagement.lowStock');
    return t('productManagement.inStock');
  };

  const renderProduct = ({ item }) => (
    <Card style={styles.productCard} testID={`seller-product-${item.id}`}>
      <View style={styles.productHeader}>
        <Checkbox
          status={selectedProducts.has(item.id) ? 'checked' : 'unchecked'}
          onPress={() => toggleProductSelection(item.id)}
          testID={`seller-product-checkbox-${item.id}`}
        />
        <View style={styles.productInfo}>
          <View style={styles.productTitleRow}>
            <Text style={styles.productName} testID={`seller-product-name-${item.id}`}>{item.name}</Text>
            {item.is_featured && (
              <Chip style={styles.featuredChip} mode="flat">
                {t('productManagement.featured')}
              </Chip>
            )}
          </View>
          <Text style={styles.productSku}>{item.sku ? t('productManagement.sku', { sku: item.sku }) : t('productManagement.skuNA')}</Text>
          <Text style={styles.productPrice}>${item.price?.toFixed(2) || '0.00'}</Text>
        </View>
        {/* Rendered only when the feature is on for this seller, so a
            disabled feature hides its control rather than 404-ing on tap. */}
        {priceIntelAvailable && (
          <IconButton
            icon="chart-line"
            onPress={() => {
              navigation.navigate('PricePosition', { productId: item.id });
            }}
            testID={`product-price-insights-${item.id}`}
          />
        )}
        <IconButton
          icon="pencil"
          onPress={() => {
            navigation.navigate('AddProduct', { productId: item.id });
          }}
          testID={`seller-product-edit-${item.id}`}
        />
      </View>
      
      <View style={styles.productDetails}>
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>{t('productManagement.categoryLabel')}</Text>
          <Text style={[
            styles.detailValue,
            !item.seller_category_id && styles.noCategoryText
          ]}>
            {item.seller_category?.name ||
             (item.seller_category_id ? `Category #${item.seller_category_id}` : t('productManagement.noCategory'))}
          </Text>
        </View>

        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>{t('productManagement.statusLabel')}</Text>
          <Chip
            style={[styles.statusChip, { backgroundColor: getStatusColor(item) }]}
            textStyle={styles.statusText}
            testID={`seller-product-status-${item.id}`}
          >
            {getStatusText(item)}
          </Chip>
        </View>

        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>{t('productManagement.stockLabel')}</Text>
          <Text style={styles.detailValue} testID={`seller-product-stock-${item.id}`}>{t('productManagement.units', { count: item.quantity_available || 0 })}</Text>
        </View>

        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>{t('productManagement.sales')}</Text>
          <Text style={styles.detailValue}>
            {t('productManagement.salesInfo', { orders: item.sales?.orders || 0, revenue: item.sales?.revenue?.toFixed(0) || 0 })}
          </Text>
        </View>

        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>{t('productManagement.reviewsLabel')}</Text>
          <Text style={styles.detailValue}>
            ⭐ {t('productManagement.reviewsInfo', { rating: item.reviews?.avg_rating?.toFixed(1) || '0.0', count: item.reviews?.count || 0 })}
          </Text>
        </View>
      </View>
    </Card>
  );

  return (
    <View style={styles.container} testID="product-management-screen">
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation?.goBack()} testID="product-management-back-button" />
        <Appbar.Content title={t('productManagement.title')} />
        <Menu
          visible={filterMenuVisible}
          onDismiss={() => setFilterMenuVisible(false)}
          anchor={
            <IconButton
              testID="product-management-filter-button"
              icon="filter"
              onPress={() => setFilterMenuVisible(true)}
            />
          }
        >
          <Menu.Item onPress={() => {}} title={t('productManagement.status')} />
          <Menu.Item onPress={() => setStatusFilter('all')} title={t('productManagement.all')} />
          <Menu.Item onPress={() => setStatusFilter('active')} title={t('productManagement.active')} />
          <Menu.Item onPress={() => setStatusFilter('inactive')} title={t('productManagement.inactive')} />
          <Divider />
          <Menu.Item onPress={() => {}} title={t('productManagement.stock')} />
          <Menu.Item onPress={() => setStockFilter('all')} title={t('productManagement.allStock')} />
          <Menu.Item onPress={() => setStockFilter('in_stock')} title={t('productManagement.inStock')} />
          <Menu.Item onPress={() => setStockFilter('low_stock')} title={t('productManagement.lowStock')} />
          <Menu.Item onPress={() => setStockFilter('out_of_stock')} title={t('productManagement.outOfStock')} />
        </Menu>
      </Appbar.Header>

      <View style={styles.content} testID="product-management-content">
        <Searchbar
          testID="product-management-search"
          placeholder={t('productManagement.searchProducts')}
          value={searchQuery}
          onChangeText={setSearchQuery}
          style={styles.searchbar}
          elevation={0}
        />

        {selectedProducts.size > 0 && (
          <Surface style={styles.selectionBar} testID="product-management-selection-bar">
            <Text style={styles.selectionText} testID="product-management-selection-count">
              {t('productManagement.productsSelected', { count: selectedProducts.size })}
            </Text>
            <View style={styles.selectionActions}>
              <Button mode="text" onPress={selectAllVisible} testID="product-management-select-all">
                All
              </Button>
              <Button mode="text" onPress={clearSelection} testID="product-management-clear-selection">
                Clear
              </Button>
              <Button
                mode="contained"
                onPress={() => setBulkMenuVisible(true)}
                testID="product-management-bulk-actions"
                buttonColor="#2196F3"
                textColor="#FFFFFF"
              >
                Actions
              </Button>
            </View>
          </Surface>
        )}

        {/* Bulk Actions Menu Modal */}
        {bulkMenuVisible && (
          <Surface style={styles.bulkActionsMenu}>
            <Text style={styles.bulkActionsTitle}>Bulk Actions</Text>
            <Button mode="text" onPress={() => handleBulkAction('activate')} icon="check" testID="bulk-action-activate">
              Activate
            </Button>
            <Button mode="text" onPress={() => handleBulkAction('deactivate')} icon="close" testID="bulk-action-deactivate">
              Deactivate
            </Button>
            <Button mode="text" onPress={() => handleBulkAction('feature')} icon="star">
              Feature
            </Button>
            <Button mode="text" onPress={() => handleBulkAction('unfeature')} icon="star-outline">
              Unfeature
            </Button>
            <Divider style={{ marginVertical: 8 }} />
            <Button mode="text" onPress={() => handleBulkAction('updatePrice')} icon="currency-usd" textColor="#4CAF50">
              Update Price
            </Button>
            <Divider style={{ marginVertical: 8 }} />
            <Button mode="text" onPress={() => handleBulkAction('delete')} icon="delete" textColor="#E53935" testID="bulk-action-delete">
              Delete
            </Button>
            <Button mode="outlined" onPress={() => setBulkMenuVisible(false)} style={{ marginTop: 8 }}>
              Cancel
            </Button>
          </Surface>
        )}

        {/* Price Update Modal */}
        <Modal
          visible={priceModalVisible}
          transparent={true}
          animationType="fade"
          onRequestClose={() => setPriceModalVisible(false)}
        >
          <View style={styles.modalOverlay}>
            <Surface style={styles.priceModal}>
              <Text style={styles.priceModalTitle}>Update Price</Text>
              <Text style={styles.priceModalSubtitle}>
                {selectedProducts.size} product(s) selected
              </Text>

              <View style={styles.priceTypeSelector}>
                <Button
                  mode={priceUpdateType === 'fixed' ? 'contained' : 'outlined'}
                  onPress={() => setPriceUpdateType('fixed')}
                  style={styles.priceTypeButton}
                  compact
                >
                  Fixed Price
                </Button>
                <Button
                  mode={priceUpdateType === 'percentage' ? 'contained' : 'outlined'}
                  onPress={() => setPriceUpdateType('percentage')}
                  style={styles.priceTypeButton}
                  compact
                >
                  Percentage
                </Button>
              </View>

              <TextInput
                label={priceUpdateType === 'fixed' ? 'New Price ($)' : 'Change (%)'}
                value={priceUpdateValue}
                onChangeText={setPriceUpdateValue}
                keyboardType="numeric"
                mode="outlined"
                style={styles.priceInput}
                placeholder={priceUpdateType === 'fixed' ? 'e.g. 29.99' : 'e.g. 10 or -10'}
              />

              {priceUpdateType === 'percentage' && (
                <Text style={styles.priceHint}>
                  Positive = increase, Negative = decrease
                </Text>
              )}

              <View style={styles.priceModalButtons}>
                <Button
                  mode="outlined"
                  onPress={() => {
                    setPriceModalVisible(false);
                    setPriceUpdateValue('');
                  }}
                  style={styles.priceModalButton}
                >
                  Cancel
                </Button>
                <Button
                  mode="contained"
                  onPress={handlePriceUpdate}
                  style={styles.priceModalButton}
                  buttonColor="#4CAF50"
                >
                  Apply
                </Button>
              </View>
            </Surface>
          </View>
        </Modal>

        {loading && products.length === 0 ? (
          <View style={styles.loadingContainer} testID="product-management-loading">
            <ActivityIndicator size="large" color={colors.primary} testID="product-management-loading-indicator" />
            <Text style={styles.loadingText}>{t('productManagement.loadingProducts')}</Text>
          </View>
        ) : products.length === 0 ? (
          <View style={styles.emptyContainer} testID="product-management-empty">
            <Text style={styles.emptyText} testID="product-management-empty-text">{t('productManagement.noProductsFound')}</Text>
            <Text style={styles.emptySubtext}>
              {searchQuery ? t('productManagement.adjustSearchTerms') : t('productManagement.addFirstProduct')}
            </Text>
          </View>
        ) : (
          <FlatList
            testID="product-management-list"
            data={products}
            renderItem={renderProduct}
            keyExtractor={(item) => item.id.toString()}
            onEndReached={loadMore}
            onEndReachedThreshold={0.1}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                colors={[colors.primary]}
                testID="product-management-refresh"
              />
            }
            contentContainerStyle={styles.list}
            showsVerticalScrollIndicator={false}
          />
        )}
      </View>

      <FAB
        testID="product-management-fab-add"
        style={styles.fab}
        icon="plus"
        onPress={() => {
          navigation.navigate('AddProduct');
        }}
      />

      <Snackbar
        visible={snackbarVisible}
        onDismiss={() => setSnackbarVisible(false)}
        duration={3000}
      >
        {snackbarMessage}
      </Snackbar>
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
  content: {
    flex: 1,
    padding: spacing.md,
  },
  searchbar: {
    marginBottom: spacing.md,
    elevation: 0,
    backgroundColor: colors.surfaceVariant,
  },
  selectionBar: {
    flexDirection: 'column',
    padding: spacing.md,
    marginHorizontal: spacing.sm,
    marginBottom: spacing.md,
    borderRadius: 8,
    elevation: 2,
  },
  selectionText: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  selectionActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: spacing.sm,
  },
  list: {
    paddingBottom: 100,
  },
  productCard: {
    marginBottom: spacing.md,
    elevation: 2,
    backgroundColor: colors.surface,
  },
  productHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  productInfo: {
    flex: 1,
    marginLeft: spacing.sm,
  },
  productTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.xs,
  },
  productName: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    flex: 1,
  },
  featuredChip: {
    marginLeft: spacing.sm,
  },
  productSku: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginBottom: spacing.xs,
  },
  productPrice: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
  },
  productDetails: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.md,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  detailLabel: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    fontWeight: typography.weights.medium,
  },
  detailValue: {
    fontSize: typography.sizes.sm,
    color: colors.onSurface,
  },
  noCategoryText: {
    color: '#FF9800',
    fontStyle: 'italic',
  },
  statusChip: {
    alignSelf: 'flex-start',
  },
  statusText: {
    color: colors.onPrimary,
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.medium,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.onSurface,
    marginLeft: spacing.sm,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  emptyText: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  emptySubtext: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
  },
  fab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
    backgroundColor: colors.primary,
  },
  bulkActionsMenu: {
    padding: spacing.md,
    marginHorizontal: spacing.sm,
    marginBottom: spacing.md,
    borderRadius: 8,
    elevation: 4,
    backgroundColor: colors.surface,
  },
  bulkActionsTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  priceModal: {
    width: '100%',
    maxWidth: 400,
    padding: spacing.lg,
    borderRadius: 12,
    elevation: 8,
    backgroundColor: colors.surface,
  },
  priceModalTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    textAlign: 'center',
    marginBottom: spacing.xs,
  },
  priceModalSubtitle: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  priceTypeSelector: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  priceTypeButton: {
    flex: 1,
  },
  priceInput: {
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
  },
  priceHint: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    textAlign: 'center',
    marginBottom: spacing.md,
    fontStyle: 'italic',
  },
  priceModalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.md,
    marginTop: spacing.md,
  },
  priceModalButton: {
    flex: 1,
  },
});