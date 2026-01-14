import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
  FlatList
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
  Appbar
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

// OrderCard component
const OrderCard = ({ order, onPress, onQuickAction, t }) => (
  <Card style={styles.orderCard} onPress={() => onPress(order)} testID={`order-card-${order.id}`}>
    <Card.Content>
      <View style={styles.orderHeader}>
        <Text style={styles.orderNumber} testID={`order-number-${order.id}`}>#{order.order_number}</Text>
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
    <Card.Actions>
      {order.status === 'PENDING' && (
        <Button mode="text" onPress={() => onQuickAction(order, 'confirm')} testID={`order-confirm-btn-${order.id}`}>
          {t('orderManagement.confirm')}
        </Button>
      )}
      {order.status === 'CONFIRMED' && (
        <Button mode="text" onPress={() => onQuickAction(order, 'process')} testID={`order-process-btn-${order.id}`}>
          {t('orderManagement.process')}
        </Button>
      )}
      {order.status === 'PROCESSING' && (
        <Button mode="text" onPress={() => onQuickAction(order, 'ship')} testID={`order-ship-btn-${order.id}`}>
          {t('orderManagement.ship')}
        </Button>
      )}
    </Card.Actions>
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

  const handleSearch = async (query) => {
    setSearchQuery(query);
    
    // Debounce search
    setTimeout(async () => {
      if (query === searchQuery) {
        try {
          const response = await orderFulfillmentService.getOrders({
            page: 1,
            per_page: 20,
            status: statusFilter,
            search: query
          });
          setOrders(response.orders);
          setPagination(response.pagination);
        } catch (error) {
          console.error('Search failed:', error);
        }
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
    navigation.navigate('OrderDetails', { orderId: order.id });
  };

  const handleQuickAction = async (order, action) => {
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
          // Navigate to shipping screen
          navigation.navigate('ShipOrder', { orderId: order.id });
          return;
        case 'deliver':
          newStatus = OrderStatus.DELIVERED;
          break;
        case 'cancel':
          newStatus = OrderStatus.CANCELLED;
          break;
        default:
          return;
      }

      await orderFulfillmentService.updateOrderStatus(order.id, newStatus);

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
      console.error('Quick action failed:', error);
      showSnackbar(t('orderManagement.updateStatusError'));
    }
  };

  const showSnackbar = (message) => {
    setSnackbarMessage(message);
    setSnackbarVisible(true);
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
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="order-management-back" />
        <Appbar.Content title={t('orderManagement.title')} />
      </Appbar.Header>

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
    color: colors.outline,
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
});