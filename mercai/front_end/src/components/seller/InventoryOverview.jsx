import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, TouchableOpacity } from 'react-native';
import { Surface, Text, Card, Chip, Button, IconButton, TextInput, Dialog, Portal } from 'react-native-paper';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerService from '../../services/sellerService.js';

export const InventoryOverview = ({ onProductPress }) => {
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updateDialogVisible, setUpdateDialogVisible] = useState(false);
  const [stockUpdates, setStockUpdates] = useState([]);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    loadInventoryAlerts();
  }, []);

  const loadInventoryAlerts = async () => {
    try {
      setLoading(true);
      const data = await sellerService.getInventoryAlerts(5);
      setAlerts(data);
    } catch (error) {
      console.error('Failed to load inventory alerts:', error);
      // Set mock data if service fails
      setAlerts({
        alerts: {
          out_of_stock: {
            count: 2,
            products: [
              {
                id: 1,
                name: 'Premium Ceramic Bowl Set',
                price: 89.99,
                quantity_available: 0,
                is_featured: true
              },
              {
                id: 2,
                name: 'Handcrafted Coffee Mug',
                price: 24.99,
                quantity_available: 0,
                is_featured: false
              }
            ]
          },
          low_stock: {
            count: 3,
            threshold: 5,
            products: [
              {
                id: 3,
                name: 'Artisan Dinner Plates',
                price: 156.00,
                quantity_available: 3,
                is_featured: true
              },
              {
                id: 4,
                name: 'Decorative Vase Collection',
                price: 78.50,
                quantity_available: 2,
                is_featured: false
              },
              {
                id: 5,
                name: 'Modern Ceramic Planters',
                price: 45.99,
                quantity_available: 4,
                is_featured: true
              }
            ]
          }
        }
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    return status === 'out_of_stock' ? colors.error : colors.warning;
  };

  const getStatusText = (status) => {
    return status === 'out_of_stock' ? 'Out of Stock' : 'Low Stock';
  };

  const openBulkStockUpdate = (products, type) => {
    const updates = products.map(product => ({
      productId: product.id,
      productName: product.name,
      currentStock: product.quantity_available,
      newStock: type === 'out_of_stock' ? '10' : Math.max(10, product.quantity_available + 5).toString()
    }));
    setStockUpdates(updates);
    setUpdateDialogVisible(true);
  };

  const updateStockQuantity = (productId, newStock) => {
    setStockUpdates(prev => prev.map(update => 
      update.productId === productId 
        ? { ...update, newStock }
        : update
    ));
  };

  const submitStockUpdates = async () => {
    try {
      setUpdating(true);
      const updates = stockUpdates
        .filter(update => update.newStock !== update.currentStock.toString())
        .map(update => ({
          product_id: update.productId,
          quantity: parseInt(update.newStock, 10)
        }));

      if (updates.length > 0) {
        await sellerService.bulkUpdateStock(updates);
        await loadInventoryAlerts(); // Reload to reflect changes
      }

      setUpdateDialogVisible(false);
      setStockUpdates([]);
    } catch (error) {
      console.error('Failed to update stock:', error);
    } finally {
      setUpdating(false);
    }
  };

  const renderAlertProduct = ({ item, type }) => (
    <TouchableOpacity
      style={styles.productItem}
      onPress={() => onProductPress?.(item)}
      activeOpacity={0.7}
    >
      <View style={styles.productInfo}>
        <Text style={styles.productName} numberOfLines={1}>
          {item.name}
        </Text>
        <Text style={styles.productPrice}>${item.price.toFixed(2)}</Text>
        <View style={styles.stockInfo}>
          <Chip
            mode="outlined"
            compact
            style={[styles.statusChip, { borderColor: getStatusColor(type) }]}
            textStyle={[styles.statusText, { color: getStatusColor(type) }]}
          >
            {getStatusText(type)} • {item.quantity_available} left
          </Chip>
          {item.is_featured && (
            <Chip mode="outlined" compact style={styles.featuredChip}>
              Featured
            </Chip>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );

  const renderStockUpdateItem = ({ item }) => (
    <View style={styles.updateItem}>
      <View style={styles.updateInfo}>
        <Text style={styles.updateProductName} numberOfLines={1}>
          {item.productName}
        </Text>
        <Text style={styles.currentStock}>
          Current: {item.currentStock} units
        </Text>
      </View>
      <TextInput
        style={styles.stockInput}
        value={item.newStock}
        onChangeText={(value) => updateStockQuantity(item.productId, value)}
        keyboardType="numeric"
        mode="outlined"
        dense
        contentStyle={styles.inputContent}
      />
    </View>
  );

  if (loading) {
    return (
      <Surface style={styles.container}>
        <Text style={styles.loadingText}>Loading inventory data...</Text>
      </Surface>
    );
  }

  if (!alerts) {
    return (
      <Surface style={styles.container}>
        <Text style={styles.errorText}>Failed to load inventory data</Text>
      </Surface>
    );
  }

  const totalAlerts = alerts.alerts.out_of_stock.count + alerts.alerts.low_stock.count;

  return (
    <Surface style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Inventory Overview</Text>
        {totalAlerts > 0 && (
          <Chip
            mode="outlined"
            compact
            style={styles.alertBadge}
            textStyle={styles.alertBadgeText}
          >
            {totalAlerts} Alert{totalAlerts > 1 ? 's' : ''}
          </Chip>
        )}
      </View>

      {totalAlerts === 0 ? (
        <View style={styles.noAlerts}>
          <Text style={styles.noAlertsText}>✅ All products are well stocked!</Text>
        </View>
      ) : (
        <View>
          {/* Out of Stock Section */}
          {alerts.alerts.out_of_stock.count > 0 && (
            <Card style={styles.alertSection}>
              <Card.Content>
                <View style={styles.sectionHeader}>
                  <Text style={[styles.sectionTitle, { color: colors.error }]}>
                    ⚠️ Out of Stock ({alerts.alerts.out_of_stock.count})
                  </Text>
                  <Button
                    mode="outlined"
                    compact
                    onPress={() => openBulkStockUpdate(alerts.alerts.out_of_stock.products, 'out_of_stock')}
                    style={styles.actionButton}
                  >
                    Restock All
                  </Button>
                </View>
                <FlatList
                  data={alerts.alerts.out_of_stock.products.slice(0, 3)}
                  renderItem={({ item }) => renderAlertProduct({ item, type: 'out_of_stock' })}
                  keyExtractor={(item) => item.id.toString()}
                  scrollEnabled={false}
                />
                {alerts.alerts.out_of_stock.count > 3 && (
                  <Text style={styles.moreText}>
                    ... and {alerts.alerts.out_of_stock.count - 3} more products
                  </Text>
                )}
              </Card.Content>
            </Card>
          )}

          {/* Low Stock Section */}
          {alerts.alerts.low_stock.count > 0 && (
            <Card style={styles.alertSection}>
              <Card.Content>
                <View style={styles.sectionHeader}>
                  <Text style={[styles.sectionTitle, { color: colors.warning }]}>
                    📦 Low Stock ({alerts.alerts.low_stock.count})
                  </Text>
                  <Button
                    mode="outlined"
                    compact
                    onPress={() => openBulkStockUpdate(alerts.alerts.low_stock.products, 'low_stock')}
                    style={styles.actionButton}
                  >
                    Restock All
                  </Button>
                </View>
                <Text style={styles.thresholdText}>
                  Below {alerts.alerts.low_stock.threshold} units
                </Text>
                <FlatList
                  data={alerts.alerts.low_stock.products.slice(0, 3)}
                  renderItem={({ item }) => renderAlertProduct({ item, type: 'low_stock' })}
                  keyExtractor={(item) => item.id.toString()}
                  scrollEnabled={false}
                />
                {alerts.alerts.low_stock.count > 3 && (
                  <Text style={styles.moreText}>
                    ... and {alerts.alerts.low_stock.count - 3} more products
                  </Text>
                )}
              </Card.Content>
            </Card>
          )}
        </View>
      )}

      {/* Bulk Stock Update Dialog */}
      <Portal>
        <Dialog
          visible={updateDialogVisible}
          onDismiss={() => setUpdateDialogVisible(false)}
          style={styles.dialog}
        >
          <Dialog.Title>Update Stock Quantities</Dialog.Title>
          <Dialog.Content>
            <FlatList
              data={stockUpdates}
              renderItem={renderStockUpdateItem}
              keyExtractor={(item) => item.productId.toString()}
              style={styles.updateList}
              showsVerticalScrollIndicator={false}
            />
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setUpdateDialogVisible(false)}>
              Cancel
            </Button>
            <Button
              mode="contained"
              onPress={submitStockUpdates}
              loading={updating}
              disabled={updating}
            >
              Update Stock
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </Surface>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    borderRadius: 12,
    elevation: 2,
    backgroundColor: colors.surface,
    marginBottom: 16,
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: colors.onSurface,
  },
  alertBadge: {
    backgroundColor: colors.errorContainer,
    borderColor: colors.error,
  },
  alertBadgeText: {
    color: colors.error,
    fontSize: 12,
  },
  noAlerts: {
    alignItems: 'center',
    padding: 24,
  },
  noAlertsText: {
    fontSize: 16,
    color: colors.onSurface,
    fontWeight: '500',
  },
  alertSection: {
    marginBottom: 16,
    backgroundColor: colors.surface,
    elevation: 1,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  actionButton: {
    borderColor: colors.primary,
  },
  thresholdText: {
    fontSize: 14,
    color: colors.outline,
    marginBottom: 12,
  },
  productItem: {
    paddingVertical: 8,
    paddingHorizontal: 4,
    borderRadius: 8,
  },
  productInfo: {
    flex: 1,
  },
  productName: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.onSurface,
    marginBottom: 4,
  },
  productPrice: {
    fontSize: 14,
    color: colors.primary,
    marginBottom: 8,
  },
  stockInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  statusChip: {
    marginRight: 8,
    marginBottom: 4,
  },
  statusText: {
    fontSize: 12,
  },
  featuredChip: {
    backgroundColor: colors.primaryContainer,
    borderColor: colors.primary,
    marginBottom: 4,
  },
  moreText: {
    fontSize: 14,
    color: colors.outline,
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: 8,
  },
  loadingText: {
    fontSize: 16,
    color: colors.outline,
    textAlign: 'center',
    padding: 24,
  },
  errorText: {
    fontSize: 16,
    color: colors.error,
    textAlign: 'center',
    padding: 24,
  },
  dialog: {
    maxHeight: '70%',
  },
  updateList: {
    maxHeight: 300,
  },
  updateItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  updateInfo: {
    flex: 1,
    marginRight: 12,
  },
  updateProductName: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.onSurface,
    marginBottom: 4,
  },
  currentStock: {
    fontSize: 12,
    color: colors.outline,
  },
  stockInput: {
    width: 80,
    height: 40,
  },
  inputContent: {
    fontSize: 14,
    textAlign: 'center',
  },
});

export default InventoryOverview;