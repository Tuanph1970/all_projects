import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert
} from 'react-native';
import {
  Text,
  Button,
  Chip,
  Divider,
  Card,
  ActivityIndicator,
  Appbar
} from 'react-native-paper';
import { useRoute, useNavigation } from '@react-navigation/native';
import orderFulfillmentService from '../../services/orderFulfillmentService.js';
import { colors, spacing, typography } from '../../constants/theme.js';

export const OrderDetailsScreen = () => {
  const route = useRoute();
  const navigation = useNavigation();
  const { orderId } = route.params;
  
  // State
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (orderId) {
      loadOrderDetails();
    }
  }, [orderId]);

  const loadOrderDetails = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const orderData = await orderFulfillmentService.getOrderDetails(orderId);
      setOrder(orderData);
    } catch (error) {
      console.error('Error loading order details:', error);
      Alert.alert('Error', 'Failed to load order details. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    loadOrderDetails(true);
  };

  const handleUpdateStatus = async (newStatus) => {
    try {
      setActionLoading(true);
      await orderFulfillmentService.updateOrderStatus(orderId, newStatus);
      await loadOrderDetails();
      Alert.alert('Success', `Order status updated to ${newStatus}`);
    } catch (error) {
      console.error('Error updating order status:', error);
      Alert.alert('Error', 'Failed to update order status. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

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

  const formatCurrency = (amount) => {
    return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading && !order) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title="Order Details" />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading order details...</Text>
        </View>
      </View>
    );
  }

  if (!order) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title="Order Details" />
        </Appbar.Header>
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>Order not found</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={`Order #${order.order_number}`} />
      </Appbar.Header>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Order Status */}
        <Card style={styles.card}>
          <Text style={styles.sectionTitle}>Order Status</Text>
          <View style={styles.statusContainer}>
            <Chip
              mode="flat"
              style={[styles.statusChip, { backgroundColor: getStatusColor(order.status) }]}
              textStyle={styles.statusText}
            >
              {order.status}
            </Chip>
            <Text style={styles.orderDate}>
              Created: {formatDate(order.created_at)}
            </Text>
          </View>
        </Card>

        {/* Customer Information */}
        <Card style={styles.card}>
          <Text style={styles.sectionTitle}>Customer Information</Text>
          <Text style={styles.customerName}>{order.customer_name}</Text>
          <Text style={styles.customerEmail}>{order.customer_email}</Text>
        </Card>

        {/* Order Items */}
        <Card style={styles.card}>
          <Text style={styles.sectionTitle}>Order Items</Text>
          {order.items?.map((item, index) => (
            <View key={index} style={styles.orderItem}>
              <View style={styles.itemInfo}>
                <Text style={styles.itemName}>{item.product_name}</Text>
                <Text style={styles.itemDetails}>Qty: {item.quantity}</Text>
              </View>
              <Text style={styles.itemTotal}>{formatCurrency(item.total_price)}</Text>
            </View>
          ))}
          <Divider style={styles.divider} />
          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Total Amount</Text>
            <Text style={styles.totalValue}>{formatCurrency(order.total_amount)}</Text>
          </View>
        </Card>

        {/* Shipping Address */}
        {order.shipping_address && (
          <Card style={styles.card}>
            <Text style={styles.sectionTitle}>Shipping Address</Text>
            <Text style={styles.addressText}>
              {order.shipping_address.address_line1}
              {order.shipping_address.address_line2 && `\n${order.shipping_address.address_line2}`}
              {`\n${order.shipping_address.city}, ${order.shipping_address.state} ${order.shipping_address.postal_code}`}
              {`\n${order.shipping_address.country}`}
            </Text>
          </Card>
        )}

        {/* Actions */}
        <Card style={styles.card}>
          <Text style={styles.sectionTitle}>Actions</Text>
          <View style={styles.actionsContainer}>
            {order.status === 'PENDING' && (
              <Button
                mode="contained"
                onPress={() => handleUpdateStatus('CONFIRMED')}
                loading={actionLoading}
                disabled={actionLoading}
                style={styles.actionButton}
              >
                Confirm Order
              </Button>
            )}
            {order.status === 'CONFIRMED' && (
              <Button
                mode="contained"
                onPress={() => handleUpdateStatus('PROCESSING')}
                loading={actionLoading}
                disabled={actionLoading}
                style={styles.actionButton}
              >
                Start Processing
              </Button>
            )}
            {order.status === 'PROCESSING' && (
              <Button
                mode="contained"
                onPress={() => handleUpdateStatus('SHIPPED')}
                loading={actionLoading}
                disabled={actionLoading}
                style={styles.actionButton}
              >
                Mark as Shipped
              </Button>
            )}
          </View>
        </Card>
      </ScrollView>
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
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  emptyText: {
    fontSize: typography.sizes.lg,
    color: colors.outline,
    textAlign: 'center',
  },
  card: {
    marginBottom: spacing.md,
    padding: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  statusChip: {
    alignSelf: 'flex-start',
  },
  statusText: {
    color: colors.onPrimary,
    fontWeight: typography.weights.medium,
  },
  orderDate: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  customerName: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  customerEmail: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  orderItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  itemInfo: {
    flex: 1,
    marginRight: spacing.md,
  },
  itemName: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  itemDetails: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  itemTotal: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
  },
  divider: {
    marginVertical: spacing.sm,
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  totalLabel: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  totalValue: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
  },
  addressText: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    lineHeight: 20,
  },
  actionsContainer: {
    gap: spacing.sm,
  },
  actionButton: {
    marginBottom: spacing.sm,
  },
});