import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
  FlatList,
  TouchableOpacity
} from 'react-native';
import {
  Surface,
  Text,
  Searchbar,
  Button,
  Menu,
  Divider,
  FAB,
  Snackbar,
  Card,
  Chip,
  ActivityIndicator,
  IconButton,
  Appbar,
  Checkbox,
  Portal,
  Modal
} from 'react-native-paper';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import orderFulfillmentService from '../../services/orderFulfillmentService.js';
import { colors, spacing, typography } from '../../constants/theme.js';
import { useTranslation } from '@i18n';

// Order Status Constants
const OrderStatus = {
  PENDING: 'PENDING',
  CONFIRMED: 'CONFIRMED',
  PROCESSING: 'PROCESSING',
  SHIPPED: 'SHIPPED',
  DELIVERED: 'DELIVERED',
  CANCELLED: 'CANCELLED',
  REFUNDED: 'REFUNDED'
};

// OrderCard component - Card.Content wrapped in TouchableOpacity for tap handling
// Card.Actions remain outside TouchableOpacity so buttons work independently
// Supports selection mode with checkbox
const OrderCard = ({ order, onPress, onQuickAction, t, selectionMode, isSelected, onSelect }) => (
  <Card style={[styles.orderCard, isSelected && styles.orderCardSelected]} testID={`order-card-${order.id}`}>
    <TouchableOpacity
      onPress={() => {
        if (selectionMode) {
          onSelect(order.id);
        } else {
          console.log('[DEBUG] TouchableOpacity onPress triggered for order:', order.id);
          onPress(order);
        }
      }}
      activeOpacity={0.7}
      testID={`order-card-touch-${order.id}`}
    >
      <Card.Content>
        <View style={styles.orderHeader}>
          {selectionMode && (
            <View style={styles.checkboxContainer}>
              <Checkbox
                status={isSelected ? 'checked' : 'unchecked'}
                onPress={() => onSelect(order.id)}
                color="#2196F3"
                uncheckedColor="#666666"
                testID={`order-checkbox-${order.id}`}
              />
            </View>
          )}
          <Text style={[styles.orderNumber, selectionMode && { marginLeft: 8, flex: 1 }]} testID={`order-number-${order.id}`}>#{order.order_number}</Text>
          <Chip
            mode="flat"
            style={[styles.statusChip, { backgroundColor: getStatusColor(order.status) }]}
            textStyle={styles.statusText}
            testID={`order-status-${order.id}`}
          >
            {order.status}
          </Chip>
        </View>
        <Text style={styles.customerName} testID={`order-customer-${order.id}`}>{order.customer_name}</Text>
        <Text style={styles.orderTotal} testID={`order-total-${order.id}`}>${order.total_amount.toFixed(2)}</Text>
        <Text style={styles.orderDate} testID={`order-date-${order.id}`}>
          {new Date(order.created_at).toLocaleDateString()}
        </Text>
      </Card.Content>
    </TouchableOpacity>
    {!selectionMode && (
      <Card.Actions>
        {order.status?.toUpperCase() === 'PENDING' && (
          <Button mode="text" onPress={() => onQuickAction(order, 'confirm')} testID={`order-confirm-btn-${order.id}`}>
            {t('orderManagement.confirm')}
          </Button>
        )}
        {order.status?.toUpperCase() === 'CONFIRMED' && (
          <Button mode="text" onPress={() => onQuickAction(order, 'process')} testID={`order-process-btn-${order.id}`}>
            {t('orderManagement.process')}
          </Button>
        )}
        {order.status?.toUpperCase() === 'PROCESSING' && (
          <Button mode="text" onPress={() => onQuickAction(order, 'ship')} testID={`order-ship-btn-${order.id}`}>
            {t('orderManagement.ship')}
          </Button>
        )}
        {order.status?.toUpperCase() === 'SHIPPED' && (
          <Button mode="text" onPress={() => onQuickAction(order, 'deliver')} testID={`order-deliver-btn-${order.id}`}>
            Deliver
          </Button>
        )}
        {(order.status?.toUpperCase() === 'DELIVERED' || order.status?.toUpperCase() === 'SHIPPED') && (
          <Button mode="text" onPress={() => onQuickAction(order, 'refund')} testID={`order-refund-btn-${order.id}`} textColor="#E53935">
            Refund
          </Button>
        )}
      </Card.Actions>
    )}
  </Card>
);

// OrderStatsCard component
const OrderStatsCard = ({ title, value, subtitle, color, icon }) => (
  <Card style={styles.statsCard}>
    <Card.Content style={styles.statsContent}>
      <View style={styles.statsIcon}>
        <Text style={[styles.iconText, { color }]}>{icon}</Text>
      </View>
      <View style={styles.statsInfo}>
        <Text style={styles.statsValue}>{value}</Text>
        <Text style={styles.statsTitle}>{title}</Text>
        <Text style={styles.statsSubtitle}>{subtitle}</Text>
      </View>
    </Card.Content>
  </Card>
);

const getStatusColor = (status) => {
  switch (status) {
    case 'PENDING': return colors.warning || '#FF9800';
    case 'CONFIRMED': return colors.info || '#2196F3';
    case 'PROCESSING': return colors.primary;
    case 'SHIPPED': return colors.success || '#4CAF50';
    case 'DELIVERED': return colors.success || '#4CAF50';
    case 'CANCELLED': return colors.error;
    case 'REFUNDED': return colors.outline;
    default: return colors.outline;
  }
};

export const OrderManagementScreen = () => {
  const navigation = useNavigation();
  const t = useTranslation();
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState(null);
  const [statusMenuVisible, setStatusMenuVisible] = useState(false);
  const [snackbarVisible, setSnackbarVisible] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [pagination, setPagination] = useState({
    current_page: 1,
    total_pages: 1,
    has_next: false,
    has_prev: false
  });

  // Bulk selection state
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedOrders, setSelectedOrders] = useState(new Set());
  const [bulkActionLoading, setBulkActionLoading] = useState(false);

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [])
  );

  const loadData = async (refresh = false) => {
    try {
      if (refresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const [ordersResponse, statsResponse] = await Promise.all([
        orderFulfillmentService.getOrders({
          page: 1,
          per_page: 20,
          status: statusFilter,
          search: searchQuery
        }),
        orderFulfillmentService.getOrderStats(30)
      ]);

      setOrders(ordersResponse.orders);
      setPagination(ordersResponse.pagination);
      setStats(statsResponse);
    } catch (error) {
      console.error('Failed to load order data:', error);
      showSnackbar(t('orderManagement.loadError'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadMoreOrders = async () => {
    if (!pagination.has_next || loading) return;

    try {
      const response = await orderFulfillmentService.getOrders({
        page: pagination.current_page + 1,
        per_page: 20,
        status: statusFilter,
        search: searchQuery
      });

      setOrders(prev => [...prev, ...response.orders]);
      setPagination(response.pagination);
    } catch (error) {
      console.error('Failed to load more orders:', error);
      showSnackbar(t('orderManagement.loadMoreError'));
    }
  };

  const searchTimeoutRef = React.useRef(null);

  const handleSearch = async (query) => {
    setSearchQuery(query);

    // Clear previous timeout for debounce
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Debounce search
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        console.log('[DEBUG] Searching orders with query:', query);
        const response = await orderFulfillmentService.getOrders({
          page: 1,
          per_page: 20,
          status: statusFilter,
          search: query
        });
        console.log('[DEBUG] Search results:', response.orders.length, 'orders');
        setOrders(response.orders);
        setPagination(response.pagination);
      } catch (error) {
        console.error('Search failed:', error);
      }
    }, 500);
  };

  const handleStatusFilter = async (status) => {
    setStatusFilter(status);
    setStatusMenuVisible(false);

    try {
      const response = await orderFulfillmentService.getOrders({
        page: 1,
        per_page: 20,
        status: status,
        search: searchQuery
      });
      setOrders(response.orders);
      setPagination(response.pagination);
    } catch (error) {
      console.error('Filter failed:', error);
    }
  };

  const handleOrderPress = (order) => {
    console.log('[DEBUG] handleOrderPress called with order:', order.id);
    navigation.navigate('OrderDetails', { orderId: order.id });
  };

  const handleQuickAction = async (order, action) => {
    console.log('[DEBUG] handleQuickAction called:', { orderId: order.id, action });

    // Handle refund action with confirmation dialog
    if (action === 'refund') {
      Alert.alert(
        'Process Refund',
        `Are you sure you want to refund order #${order.order_number}?\nAmount: $${order.total_amount.toFixed(2)}`,
        [
          {
            text: 'Cancel',
            style: 'cancel'
          },
          {
            text: 'Refund',
            style: 'destructive',
            onPress: async () => {
              try {
                console.log('[DEBUG] Processing refund for order:', order.id);
                const response = await orderFulfillmentService.processRefund(order.id, {
                  amount: order.total_amount,
                  reason: 'Customer return request'
                });
                console.log('[DEBUG] processRefund response:', response);

                // Update local state
                setOrders(prev =>
                  prev.map(o =>
                    o.id === order.id
                      ? { ...o, status: OrderStatus.REFUNDED }
                      : o
                  )
                );

                showSnackbar(`Order #${order.order_number} refunded successfully`);
              } catch (error) {
                console.error('[DEBUG] Refund failed:', error);
                console.error('[DEBUG] Error response:', error.response?.status, error.response?.data);
                showSnackbar('Failed to process refund');
              }
            }
          }
        ]
      );
      return;
    }

    try {
      let newStatus;
      switch (action) {
        case 'confirm':
          newStatus = OrderStatus.CONFIRMED;
          break;
        case 'process':
          newStatus = OrderStatus.PROCESSING;
          break;
        case 'ship':
          // Directly update status to SHIPPED
          newStatus = OrderStatus.SHIPPED;
          break;
        case 'deliver':
          newStatus = OrderStatus.DELIVERED;
          break;
        case 'cancel':
          newStatus = OrderStatus.CANCELLED;
          break;
        default:
          return;
      }

      console.log('[DEBUG] Calling updateOrderStatus:', { orderId: order.id, newStatus });
      const response = await orderFulfillmentService.updateOrderStatus(order.id, { status: newStatus });
      console.log('[DEBUG] updateOrderStatus response:', response);

      // Update local state
      setOrders(prev =>
        prev.map(o =>
          o.id === order.id
            ? { ...o, status: newStatus }
            : o
        )
      );

      showSnackbar(t('orderManagement.orderActionSuccess', { orderNumber: order.order_number, action }));
    } catch (error) {
      console.error('[DEBUG] Quick action failed:', error);
      console.error('[DEBUG] Error response:', error.response?.status, error.response?.data);
      showSnackbar(t('orderManagement.updateStatusError'));
    }
  };

  const showSnackbar = (message) => {
    setSnackbarMessage(message);
    setSnackbarVisible(true);
  };

  // Toggle selection mode
  const toggleSelectionMode = () => {
    setSelectionMode(!selectionMode);
    setSelectedOrders(new Set());
  };

  // Handle order selection
  const handleOrderSelect = (orderId) => {
    setSelectedOrders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(orderId)) {
        newSet.delete(orderId);
      } else {
        newSet.add(orderId);
      }
      return newSet;
    });
  };

  // Select all visible orders
  const handleSelectAll = () => {
    if (selectedOrders.size === orders.length) {
      setSelectedOrders(new Set());
    } else {
      setSelectedOrders(new Set(orders.map(o => o.id)));
    }
  };

  // Bulk confirm all pending orders
  const handleBulkConfirmPending = async () => {
    const pendingOrders = orders.filter(o => o.status?.toUpperCase() === 'PENDING');
    if (pendingOrders.length === 0) {
      showSnackbar('No pending orders to confirm');
      return;
    }

    Alert.alert(
      'Confirm All Pending Orders',
      `Are you sure you want to confirm ${pendingOrders.length} pending orders?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Confirm All',
          onPress: async () => {
            setBulkActionLoading(true);
            try {
              const updates = pendingOrders.map(order => ({
                order_id: order.id,
                status: 'confirmed'
              }));

              console.log('[DEBUG] Bulk confirming orders:', updates);
              await orderFulfillmentService.bulkUpdateOrderStatus(updates);

              // Update local state
              setOrders(prev =>
                prev.map(o =>
                  pendingOrders.find(p => p.id === o.id)
                    ? { ...o, status: 'CONFIRMED' }
                    : o
                )
              );

              showSnackbar(`${pendingOrders.length} orders confirmed successfully`);
            } catch (error) {
              console.error('[DEBUG] Bulk confirm failed:', error);
              showSnackbar('Failed to confirm orders');
            } finally {
              setBulkActionLoading(false);
            }
          }
        }
      ]
    );
  };

  // Bulk action on selected orders
  const handleBulkAction = async (action) => {
    if (selectedOrders.size === 0) {
      showSnackbar('No orders selected');
      return;
    }

    const selectedOrdersList = orders.filter(o => selectedOrders.has(o.id));
    let newStatus;
    let actionName;

    switch (action) {
      case 'confirm':
        newStatus = 'confirmed';
        actionName = 'confirm';
        break;
      case 'process':
        newStatus = 'processing';
        actionName = 'process';
        break;
      case 'ship':
        newStatus = 'shipped';
        actionName = 'ship';
        break;
      case 'deliver':
        newStatus = 'delivered';
        actionName = 'deliver';
        break;
      default:
        return;
    }

    Alert.alert(
      `Bulk ${actionName}`,
      `Are you sure you want to ${actionName} ${selectedOrders.size} orders?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: `${actionName.charAt(0).toUpperCase() + actionName.slice(1)} All`,
          onPress: async () => {
            setBulkActionLoading(true);
            try {
              const updates = selectedOrdersList.map(order => ({
                order_id: order.id,
                status: newStatus
              }));

              console.log('[DEBUG] Bulk action:', action, updates);
              await orderFulfillmentService.bulkUpdateOrderStatus(updates);

              // Update local state
              setOrders(prev =>
                prev.map(o =>
                  selectedOrders.has(o.id)
                    ? { ...o, status: newStatus.toUpperCase() }
                    : o
                )
              );

              showSnackbar(`${selectedOrders.size} orders ${actionName}ed successfully`);
              setSelectedOrders(new Set());
              setSelectionMode(false);
            } catch (error) {
              console.error('[DEBUG] Bulk action failed:', error);
              showSnackbar(`Failed to ${actionName} orders`);
            } finally {
              setBulkActionLoading(false);
            }
          }
        }
      ]
    );
  };

  // Get available bulk actions based on selected orders
  const getAvailableBulkActions = () => {
    if (selectedOrders.size === 0) return [];

    const selectedOrdersList = orders.filter(o => selectedOrders.has(o.id));
    const statuses = [...new Set(selectedOrdersList.map(o => o.status?.toUpperCase()))];

    // Only allow bulk actions if all selected orders have the same status
    if (statuses.length !== 1) return ['mixed'];

    switch (statuses[0]) {
      case 'PENDING':
        return ['confirm'];
      case 'CONFIRMED':
        return ['process'];
      case 'PROCESSING':
        return ['ship'];
      case 'SHIPPED':
        return ['deliver'];
      default:
        return [];
    }
  };

  const getStatusFilterText = () => {
    if (!statusFilter) return t('orderManagement.allOrders');
    return t(`orderManagement.status.${statusFilter.toLowerCase()}`);
  };

  const renderOrderCard = ({ item }) => (
    <OrderCard
      order={item}
      onPress={handleOrderPress}
      onQuickAction={handleQuickAction}
      t={t}
      selectionMode={selectionMode}
      isSelected={selectedOrders.has(item.id)}
      onSelect={handleOrderSelect}
    />
  );

  if (loading && !refreshing) {
    return (
      <View style={styles.container}>
        <Appbar.Header>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title={t('orderManagement.title')} />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>{t('orderManagement.loadingOrders')}</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container} testID="order-management-screen">
      <Appbar.Header>
        {selectionMode ? (
          <>
            <Appbar.Action icon="close" onPress={toggleSelectionMode} testID="cancel-selection" />
            <Appbar.Content title={`${selectedOrders.size} selected`} />
            <Button
              mode="text"
              onPress={handleSelectAll}
              testID="select-all-btn"
              textColor="#fff"
            >
              {selectedOrders.size === orders.length ? "Deselect All" : "Select All"}
            </Button>
          </>
        ) : (
          <>
            <Appbar.BackAction onPress={() => navigation.goBack()} testID="order-management-back" />
            <Appbar.Content title={t('orderManagement.title')} />
            <Button
              mode="contained"
              onPress={toggleSelectionMode}
              testID="enter-selection-mode"
              style={styles.selectModeButton}
              labelStyle={styles.selectModeButtonLabel}
              icon="checkbox-multiple-marked-outline"
              buttonColor="#FF9800"
              textColor="#FFFFFF"
            >
              Select
            </Button>
          </>
        )}
      </Appbar.Header>

      {/* Bulk Action Bar - shown when in selection mode with orders selected */}
      {selectionMode && selectedOrders.size > 0 && (
        <View style={styles.bulkActionBar} testID="bulk-action-bar">
          {getAvailableBulkActions().includes('mixed') ? (
            <Text style={styles.bulkActionText}>Select orders with same status for bulk actions</Text>
          ) : (
            <View style={styles.bulkActionButtons}>
              {getAvailableBulkActions().includes('confirm') && (
                <Button
                  mode="contained"
                  onPress={() => handleBulkAction('confirm')}
                  loading={bulkActionLoading}
                  style={styles.bulkButton}
                  testID="bulk-confirm-btn"
                >
                  Confirm ({selectedOrders.size})
                </Button>
              )}
              {getAvailableBulkActions().includes('process') && (
                <Button
                  mode="contained"
                  onPress={() => handleBulkAction('process')}
                  loading={bulkActionLoading}
                  style={styles.bulkButton}
                  testID="bulk-process-btn"
                >
                  Process ({selectedOrders.size})
                </Button>
              )}
              {getAvailableBulkActions().includes('ship') && (
                <Button
                  mode="contained"
                  onPress={() => handleBulkAction('ship')}
                  loading={bulkActionLoading}
                  style={styles.bulkButton}
                  testID="bulk-ship-btn"
                >
                  Ship ({selectedOrders.size})
                </Button>
              )}
              {getAvailableBulkActions().includes('deliver') && (
                <Button
                  mode="contained"
                  onPress={() => handleBulkAction('deliver')}
                  loading={bulkActionLoading}
                  style={styles.bulkButton}
                  testID="bulk-deliver-btn"
                >
                  Deliver ({selectedOrders.size})
                </Button>
              )}
            </View>
          )}
        </View>
      )}

      {/* Quick "Confirm All Pending" Button - shown when filtered to pending */}
      {!selectionMode && statusFilter === 'PENDING' && orders.filter(o => o.status?.toUpperCase() === 'PENDING').length > 0 && (
        <View style={styles.quickActionBar} testID="quick-action-bar">
          <Button
            mode="contained"
            icon="check-all"
            onPress={handleBulkConfirmPending}
            loading={bulkActionLoading}
            style={styles.confirmAllButton}
            testID="confirm-all-pending-btn"
          >
            Confirm All Pending ({orders.filter(o => o.status?.toUpperCase() === 'PENDING').length})
          </Button>
        </View>
      )}

      {/* Header Stats */}
      {stats && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.statsContainer}>
          <View style={styles.statsRow}>
            <OrderStatsCard
              title={t('orderManagement.totalOrders')}
              value={stats.total_orders}
              subtitle={t('orderManagement.last30Days')}
              color={colors.primary}
              icon="📦"
            />
            <OrderStatsCard
              title={t('orderManagement.revenue')}
              value={`$${stats.revenue?.total?.toFixed(0) || 0}`}
              subtitle={t('orderManagement.avgRevenue', { amount: stats.revenue?.average?.toFixed(0) || 0 })}
              color={colors.success || '#4CAF50'}
              icon="💰"
            />
            <OrderStatsCard
              title={t('orderManagement.pending')}
              value={stats.pending_actions?.pending_confirmation || 0}
              subtitle={t('orderManagement.needConfirmation')}
              color={colors.warning || '#FF9800'}
              icon="⏳"
            />
            <OrderStatsCard
              title={t('orderManagement.readyToShip')}
              value={stats.pending_actions?.ready_to_ship || 0}
              subtitle={t('orderManagement.processingOrders')}
              color={colors.info || '#2196F3'}
              icon="🚚"
            />
          </View>
        </ScrollView>
      )}

      {/* Search and Filters */}
      <View style={styles.searchContainer} testID="order-search-container">
        <Searchbar
          placeholder={t('orderManagement.searchPlaceholder')}
          value={searchQuery}
          onChangeText={handleSearch}
          style={styles.searchbar}
          testID="order-search-bar"
        />
        <Menu
          visible={statusMenuVisible}
          onDismiss={() => setStatusMenuVisible(false)}
          anchor={
            <Button
              mode="outlined"
              onPress={() => setStatusMenuVisible(true)}
              style={styles.filterButton}
              contentStyle={styles.filterButtonContent}
              testID="order-filter-button"
            >
              {getStatusFilterText()}
            </Button>
          }
        >
          <Menu.Item onPress={() => handleStatusFilter(undefined)} title={t('orderManagement.allOrders')} testID="filter-all-orders" />
          <Divider />
          <Menu.Item onPress={() => handleStatusFilter(OrderStatus.PENDING)} title={t('orderManagement.status.pending')} testID="filter-pending" />
          <Menu.Item onPress={() => handleStatusFilter(OrderStatus.CONFIRMED)} title={t('orderManagement.status.confirmed')} testID="filter-confirmed" />
          <Menu.Item onPress={() => handleStatusFilter(OrderStatus.PROCESSING)} title={t('orderManagement.status.processing')} testID="filter-processing" />
          <Menu.Item onPress={() => handleStatusFilter(OrderStatus.SHIPPED)} title={t('orderManagement.status.shipped')} testID="filter-shipped" />
          <Menu.Item onPress={() => handleStatusFilter(OrderStatus.DELIVERED)} title={t('orderManagement.status.delivered')} testID="filter-delivered" />
          <Menu.Item onPress={() => handleStatusFilter(OrderStatus.CANCELLED)} title={t('orderManagement.status.cancelled')} testID="filter-cancelled" />
          <Menu.Item onPress={() => handleStatusFilter(OrderStatus.REFUNDED)} title={t('orderManagement.status.refunded')} testID="filter-refunded" />
        </Menu>
      </View>

      {/* Orders List */}
      <FlatList
        data={orders}
        renderItem={renderOrderCard}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => loadData(true)}
            colors={[colors.primary]}
          />
        }
        onEndReached={loadMoreOrders}
        onEndReachedThreshold={0.1}
        ListEmptyComponent={() => (
          <View style={styles.emptyContainer} testID="order-list-empty">
            <Text style={styles.emptyText}>{t('orderManagement.noOrdersFound')}</Text>
            <Text style={styles.emptySubtext}>
              {statusFilter || searchQuery
                ? t('orderManagement.tryAdjustingFilters')
                : t('orderManagement.ordersWillAppear')
              }
            </Text>
          </View>
        )}
        showsVerticalScrollIndicator={false}
        testID="order-list"
      />

      {/* Floating Action Button */}
      <FAB
        style={styles.fab}
        icon="chart-line"
        onPress={() => navigation.navigate('OrderAnalytics')}
        label={t('orderManagement.analytics')}
      />

      {/* Snackbar */}
      <Snackbar
        visible={snackbarVisible}
        onDismiss={() => setSnackbarVisible(false)}
        duration={3000}
        style={styles.snackbar}
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.surface,
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.onSurface,
  },
  statsContainer: {
    paddingVertical: spacing.md,
  },
  statsRow: {
    flexDirection: 'row',
    gap: spacing.md,
    paddingHorizontal: spacing.md,
  },
  statsCard: {
    minWidth: 150,
    marginRight: spacing.sm,
  },
  statsContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statsIcon: {
    marginRight: spacing.md,
  },
  iconText: {
    fontSize: 24,
  },
  statsInfo: {
    flex: 1,
  },
  statsValue: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  statsTitle: {
    fontSize: typography.sizes.sm,
    color: colors.onSurface,
    marginTop: spacing.xs,
  },
  statsSubtitle: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
  },
  searchContainer: {
    padding: spacing.md,
    borderRadius: 8,
    backgroundColor: colors.surface,
  },
  searchbar: {
    backgroundColor: colors.surfaceVariant,
    marginBottom: spacing.md,
  },
  filterButton: {
    alignSelf: 'flex-start',
  },
  filterButtonContent: {
    height: 40,
  },
  listContainer: {
    paddingTop: spacing.md,
    paddingHorizontal: spacing.md,
    paddingBottom: 100,
  },
  orderCard: {
    marginBottom: spacing.md,
  },
  orderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  orderNumber: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  statusChip: {
    alignSelf: 'flex-start',
  },
  statusText: {
    color: colors.onPrimary,
    fontWeight: typography.weights.medium,
    fontSize: typography.sizes.sm,
  },
  customerName: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  orderTotal: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
    marginBottom: spacing.xs,
  },
  orderDate: {
    fontSize: typography.sizes.sm,
    color: '#666666',
    fontWeight: '500',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: spacing.xl,
  },
  emptyText: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  emptySubtext: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    paddingHorizontal: spacing.lg,
  },
  fab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
    backgroundColor: colors.primary,
  },
  snackbar: {
    marginBottom: spacing.lg,
  },
  // Bulk selection styles
  checkboxContainer: {
    backgroundColor: '#E3F2FD',
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#2196F3',
    marginRight: 8,
  },
  orderCardSelected: {
    borderWidth: 3,
    borderColor: '#2196F3',
    backgroundColor: '#E3F2FD',
  },
  bulkActionBar: {
    backgroundColor: colors.primaryContainer || '#E3F2FD',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline,
  },
  bulkActionButtons: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  bulkActionText: {
    textAlign: 'center',
    color: colors.onSurfaceVariant,
    fontSize: typography.sizes.sm,
  },
  bulkButton: {
    minWidth: 120,
  },
  quickActionBar: {
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline,
  },
  confirmAllButton: {
    backgroundColor: colors.success || '#4CAF50',
  },
  selectModeButton: {
    marginRight: 8,
    borderColor: '#fff',
  },
  selectModeButtonLabel: {
    color: '#fff',
    fontSize: 12,
  },
});