import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  RefreshControl,
} from 'react-native';
import {
  Text,
  Card,
  Chip,
  Button,
  ActivityIndicator,
  Appbar,
  Divider,
} from 'react-native-paper';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { customerOrderService } from '../../services/customerOrderService.js';
import { colors, spacing, typography } from '../../constants/theme.js';
import { useTranslation } from '@i18n';

// Order Card Component
const OrderCard = ({ order, onPress, t, index }) => {
  const statusColor = customerOrderService.getStatusColor(order.status);
  const formattedDate = customerOrderService.formatDate(order.created_at);
  const formattedAmount = customerOrderService.formatCurrency(order.total_amount);

  return (
    <Card
      style={styles.orderCard}
      onPress={() => onPress(order)}
      testID={`order-history-card-${index}`}
    >
      <Card.Content>
        <View style={styles.orderHeader}>
          <Text style={styles.orderNumber} testID={`order-history-number-${index}`}>
            #{order.order_number}
          </Text>
          <Chip
            mode="flat"
            style={[styles.statusChip, { backgroundColor: statusColor }]}
            textStyle={styles.statusText}
            testID={`order-history-status-${index}`}
          >
            {customerOrderService.getStatusDisplayName(order.status)}
          </Chip>
        </View>

        <Divider style={styles.divider} />

        <View style={styles.orderDetails}>
          <View style={styles.orderInfo}>
            <Text style={styles.orderLabel}>{t('orderHistory.items')}</Text>
            <Text style={styles.orderValue} testID={`order-history-items-${index}`}>
              {order.items?.length || order.item_count || 0} {t('orderHistory.products')}
            </Text>
          </View>

          <View style={styles.orderInfo}>
            <Text style={styles.orderLabel}>{t('orderHistory.date')}</Text>
            <Text style={styles.orderValue} testID={`order-history-date-${index}`}>
              {formattedDate}
            </Text>
          </View>

          <View style={styles.orderInfo}>
            <Text style={styles.orderLabel}>{t('orderHistory.total')}</Text>
            <Text style={styles.orderTotal} testID={`order-history-total-${index}`}>
              {formattedAmount}
            </Text>
          </View>
        </View>

        <Button
          mode="outlined"
          onPress={() => onPress(order)}
          style={styles.viewButton}
          testID={`order-history-view-btn-${index}`}
        >
          {t('orderHistory.viewDetails')}
        </Button>
      </Card.Content>
    </Card>
  );
};

export const OrderHistoryScreen = () => {
  const navigation = useNavigation();
  const t = useTranslation();

  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  useFocusEffect(
    useCallback(() => {
      loadOrders();
    }, [])
  );

  const loadOrders = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const response = await customerOrderService.getOrders();
      // Handle different response formats
      setOrders(response.orders || response.data || response || []);
    } catch (error) {
      console.error('Error loading orders:', error);
      setError(error.message || 'Failed to load orders');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleOrderPress = (order) => {
    navigation.navigate('CustomerOrderDetails', { orderId: order.id });
  };

  const handleRefresh = () => {
    loadOrders(true);
  };

  const renderOrderCard = ({ item, index }) => (
    <OrderCard
      order={item}
      index={index}
      onPress={handleOrderPress}
      t={t}
    />
  );

  if (loading && !refreshing) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} testID="order-history-back" />
          <Appbar.Content title={t('orderHistory.title')} />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>{t('orderHistory.loading')}</Text>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} testID="order-history-back" />
          <Appbar.Content title={t('orderHistory.title')} />
        </Appbar.Header>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{t('orderHistory.errorLoading')}</Text>
          <Button mode="contained" onPress={() => loadOrders()}>
            {t('common.retry')}
          </Button>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container} testID="order-history-screen">
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="order-history-back" />
        <Appbar.Content title={t('orderHistory.title')} />
      </Appbar.Header>

      <FlatList
        data={orders}
        renderItem={renderOrderCard}
        keyExtractor={(item) => item.id?.toString() || Math.random().toString()}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
          />
        }
        ListEmptyComponent={() => (
          <View style={styles.emptyContainer} testID="order-history-empty">
            <Text style={styles.emptyTitle}>{t('orderHistory.noOrders')}</Text>
            <Text style={styles.emptySubtitle}>
              {t('orderHistory.noOrdersMessage')}
            </Text>
            <Button
              mode="contained"
              style={styles.shopButton}
              onPress={() => navigation.navigate('Home')}
              testID="order-history-shop-button"
            >
              {t('orderHistory.startShopping')}
            </Button>
          </View>
        )}
        showsVerticalScrollIndicator={false}
        testID="order-history-list"
      />
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
    padding: spacing.lg,
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.onSurface,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  errorText: {
    fontSize: typography.sizes.lg,
    color: colors.error,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  listContainer: {
    padding: spacing.md,
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
    color: colors.onPrimary || '#fff',
    fontWeight: typography.weights.medium,
    fontSize: typography.sizes.sm,
  },
  divider: {
    marginVertical: spacing.sm,
  },
  orderDetails: {
    marginBottom: spacing.md,
  },
  orderInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.xs,
  },
  orderLabel: {
    fontSize: typography.sizes.md,
    color: colors.outline,
  },
  orderValue: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
  },
  orderTotal: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
  },
  viewButton: {
    marginTop: spacing.sm,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
    marginTop: spacing.xl * 2,
  },
  emptyTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  emptySubtitle: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  shopButton: {
    marginTop: spacing.md,
  },
});
