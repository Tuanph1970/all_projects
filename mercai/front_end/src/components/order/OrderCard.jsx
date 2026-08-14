import React from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import { Surface, Text, Button, Divider } from 'react-native-paper';
import { OrderStatusBadge } from './OrderStatusBadge.jsx';
import { colors, spacing, typography } from '../../constants/theme.js';
import { useLanguage } from '@i18n';

const OrderStatus = {
  PENDING: 'PENDING',
  CONFIRMED: 'CONFIRMED',
  PROCESSING: 'PROCESSING',
  SHIPPED: 'SHIPPED',
  DELIVERED: 'DELIVERED',
  CANCELLED: 'CANCELLED',
  REFUNDED: 'REFUNDED'
};

export const OrderCard = ({
  order,
  onPress,
  onQuickAction,
  showQuickActions = true
}) => {
  const { formatCurrency } = useLanguage();

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getQuickActions = () => {
    switch (order.status) {
      case OrderStatus.PENDING:
        return [
          { label: 'Process', action: 'process', color: colors.primary },
          { label: 'Cancel', action: 'cancel', color: colors.error }
        ];
      case OrderStatus.PROCESSING:
        return [
          { label: 'Mark Shipped', action: 'ship', color: colors.success || '#4CAF50' }
        ];
      case OrderStatus.SHIPPED:
        return [
          { label: 'Track', action: 'track', color: colors.info || '#2196F3' }
        ];
      default:
        return [];
    }
  };

  const quickActions = showQuickActions ? getQuickActions() : [];

  return (
    <Surface style={styles.card}>
      <TouchableOpacity onPress={() => onPress(order)} style={styles.cardContent}>
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Text style={styles.orderNumber}>#{order.order_number}</Text>
            <Text style={styles.date}>{formatDate(order.created_at)}</Text>
          </View>
          <OrderStatusBadge status={order.status} />
        </View>

        <View style={styles.customerInfo}>
          <Text style={styles.customerName}>
            {order.customer?.first_name} {order.customer?.last_name}
          </Text>
          <Text style={styles.customerEmail}>{order.customer?.email}</Text>
        </View>

        <View style={styles.orderDetails}>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Items</Text>
            <Text style={styles.detailValue}>{order.items?.length || 0}</Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Total</Text>
            <Text style={styles.totalAmount}>{formatCurrency(order.total_amount || 0)}</Text>
          </View>
        </View>

        {order.tracking_number && (
          <View style={styles.trackingInfo}>
            <Text style={styles.trackingLabel}>Tracking</Text>
            <Text style={styles.trackingNumber}>{order.tracking_number}</Text>
            {order.shipping_carrier && (
              <Text style={styles.carrier}>via {order.shipping_carrier}</Text>
            )}
          </View>
        )}
      </TouchableOpacity>

      {quickActions.length > 0 && (
        <>
          <Divider style={styles.divider} />
          <View style={styles.quickActions}>
            {quickActions.map((action, index) => (
              <Button
                key={index}
                mode="outlined"
                onPress={() => onQuickAction?.(order, action.action)}
                style={[
                  styles.quickActionButton,
                  { borderColor: action.color }
                ]}
                labelStyle={[
                  styles.quickActionLabel,
                  { color: action.color }
                ]}
              >
                {action.label}
              </Button>
            ))}
          </View>
        </>
      )}
    </Surface>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 12,
    marginBottom: spacing.md,
    overflow: 'hidden',
    elevation: 2,
  },
  cardContent: {
    padding: spacing.md,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  headerLeft: {
    flex: 1,
  },
  orderNumber: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  date: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  customerInfo: {
    marginBottom: spacing.md,
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
  orderDetails: {
    marginBottom: spacing.md,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  detailLabel: {
    fontSize: typography.sizes.md,
    color: colors.outline,
  },
  detailValue: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    fontWeight: typography.weights.medium,
  },
  totalAmount: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
  },
  trackingInfo: {
    backgroundColor: colors.surfaceVariant,
    padding: spacing.md,
    borderRadius: 8,
    marginBottom: spacing.md,
  },
  trackingLabel: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginBottom: spacing.xs,
  },
  trackingNumber: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.primary,
  },
  carrier: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginTop: spacing.xs,
  },
  divider: {
    marginVertical: 0,
  },
  quickActions: {
    flexDirection: 'row',
    padding: spacing.md,
    gap: spacing.sm,
    flexWrap: 'wrap',
  },
  quickActionButton: {
    flex: 1,
    minWidth: 100,
  },
  quickActionLabel: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
  },
});

export default OrderCard;