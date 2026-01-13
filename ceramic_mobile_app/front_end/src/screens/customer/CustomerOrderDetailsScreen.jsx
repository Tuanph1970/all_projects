import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
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
import { useRoute, useNavigation } from '@react-navigation/native';
import { customerOrderService } from '../../services/customerOrderService.js';
import { colors, spacing, typography } from '../../constants/theme.js';
import { useTranslation } from '@i18n';

export const CustomerOrderDetailsScreen = () => {
  const route = useRoute();
  const navigation = useNavigation();
  const t = useTranslation();
  const { orderId } = route.params;

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [cancelling, setCancelling] = useState(false);

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
      setError(null);

      const response = await customerOrderService.getOrderDetails(orderId);
      setOrder(response);
    } catch (error) {
      console.error('Error loading order details:', error);
      setError(error.message || 'Failed to load order details');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    loadOrderDetails(true);
  };

  const handleCancelOrder = () => {
    Alert.alert(
      t('orderDetails.cancelOrder'),
      t('orderDetails.cancelOrderConfirm'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('orderDetails.confirmCancel'),
          style: 'destructive',
          onPress: async () => {
            try {
              setCancelling(true);
              await customerOrderService.cancelOrder(orderId);
              await loadOrderDetails();
              Alert.alert(t('orderDetails.success'), t('orderDetails.orderCancelled'));
            } catch (error) {
              Alert.alert(t('orderDetails.error'), error.message || t('orderDetails.cancelFailed'));
            } finally {
              setCancelling(false);
            }
          },
        },
      ]
    );
  };

  if (loading && !refreshing) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} testID="order-details-back" />
          <Appbar.Content title={t('orderDetails.title')} />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>{t('orderDetails.loading')}</Text>
        </View>
      </View>
    );
  }

  if (error || !order) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} testID="order-details-back" />
          <Appbar.Content title={t('orderDetails.title')} />
        </Appbar.Header>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error || t('orderDetails.notFound')}</Text>
          <Button mode="contained" onPress={() => loadOrderDetails()}>
            {t('common.retry')}
          </Button>
        </View>
      </View>
    );
  }

  const statusColor = customerOrderService.getStatusColor(order.status);
  const formattedDate = customerOrderService.formatDate(order.created_at);
  const canCancel = customerOrderService.canCancelOrder(order.status);

  return (
    <View style={styles.container} testID="customer-order-details-screen">
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="order-details-back" />
        <Appbar.Content title={`${t('orderDetails.order')} #${order.order_number}`} />
      </Appbar.Header>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Order Status Card */}
        <Card style={styles.card} testID="order-details-status-card">
          <Card.Content>
            <Text style={styles.sectionTitle}>{t('orderDetails.orderStatus')}</Text>
            <View style={styles.statusContainer}>
              <Chip
                mode="flat"
                style={[styles.statusChip, { backgroundColor: statusColor }]}
                textStyle={styles.statusText}
                testID="order-details-status"
              >
                {customerOrderService.getStatusDisplayName(order.status)}
              </Chip>
              <Text style={styles.orderDate} testID="order-details-date">
                {formattedDate}
              </Text>
            </View>
          </Card.Content>
        </Card>

        {/* Order Items Card */}
        <Card style={styles.card} testID="order-details-items-card">
          <Card.Content>
            <Text style={styles.sectionTitle}>{t('orderDetails.orderItems')}</Text>
            {order.items?.map((item, index) => (
              <View key={item.id || index} style={styles.orderItem} testID={`order-details-item-${index}`}>
                <View style={styles.itemInfo}>
                  <Text style={styles.itemName} testID={`order-details-item-name-${index}`}>
                    {item.product_name}
                  </Text>
                  <Text style={styles.itemDetails}>
                    {t('orderDetails.qty')}: {item.quantity}
                  </Text>
                </View>
                <Text style={styles.itemTotal} testID={`order-details-item-total-${index}`}>
                  {customerOrderService.formatCurrency(item.total_price)}
                </Text>
              </View>
            ))}

            <Divider style={styles.divider} />

            {/* Order Summary */}
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>{t('orderDetails.subtotal')}</Text>
              <Text style={styles.summaryValue} testID="order-details-subtotal">
                {customerOrderService.formatCurrency(order.subtotal)}
              </Text>
            </View>

            {order.tax_amount !== undefined && (
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>{t('orderDetails.tax')}</Text>
                <Text style={styles.summaryValue} testID="order-details-tax">
                  {customerOrderService.formatCurrency(order.tax_amount)}
                </Text>
              </View>
            )}

            {order.shipping_amount !== undefined && (
              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>{t('orderDetails.shipping')}</Text>
                <Text style={styles.summaryValue} testID="order-details-shipping">
                  {parseFloat(order.shipping_amount) === 0
                    ? t('orderDetails.free')
                    : customerOrderService.formatCurrency(order.shipping_amount)}
                </Text>
              </View>
            )}

            <Divider style={styles.divider} />

            <View style={styles.summaryRow}>
              <Text style={styles.totalLabel}>{t('orderDetails.total')}</Text>
              <Text style={styles.totalValue} testID="order-details-total">
                {customerOrderService.formatCurrency(order.total_amount)}
              </Text>
            </View>
          </Card.Content>
        </Card>

        {/* Shipping Address Card */}
        {order.shipping_address && (
          <Card style={styles.card} testID="order-details-address-card">
            <Card.Content>
              <Text style={styles.sectionTitle}>{t('orderDetails.shippingAddress')}</Text>
              <Text style={styles.addressText} testID="order-details-address">
                {order.shipping_address.address_line1}
                {order.shipping_address.address_line2 && `\n${order.shipping_address.address_line2}`}
                {`\n${order.shipping_address.city}, ${order.shipping_address.state} ${order.shipping_address.postal_code}`}
                {`\n${order.shipping_address.country}`}
              </Text>
            </Card.Content>
          </Card>
        )}

        {/* Tracking Info Card (if shipped) */}
        {order.tracking_number && (
          <Card style={styles.card} testID="order-details-tracking-card">
            <Card.Content>
              <Text style={styles.sectionTitle}>{t('orderDetails.trackingInfo')}</Text>
              <Text style={styles.trackingNumber} testID="order-details-tracking">
                {order.tracking_number}
              </Text>
              {order.carrier && (
                <Text style={styles.carrierText}>{order.carrier}</Text>
              )}
            </Card.Content>
          </Card>
        )}

        {/* Actions */}
        {canCancel && (
          <Button
            mode="outlined"
            onPress={handleCancelOrder}
            loading={cancelling}
            disabled={cancelling}
            style={styles.cancelButton}
            textColor={colors.error}
            testID="order-details-cancel-button"
          >
            {t('orderDetails.cancelOrder')}
          </Button>
        )}

        <View style={styles.bottomSpacer} />
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
  card: {
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  statusContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusChip: {
    alignSelf: 'flex-start',
  },
  statusText: {
    color: colors.onPrimary || '#fff',
    fontWeight: typography.weights.medium,
  },
  orderDate: {
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
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  summaryLabel: {
    fontSize: typography.sizes.md,
    color: colors.outline,
  },
  summaryValue: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    fontWeight: typography.weights.medium,
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
    lineHeight: 22,
  },
  trackingNumber: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.primary,
    marginBottom: spacing.xs,
  },
  carrierText: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  cancelButton: {
    marginTop: spacing.md,
    borderColor: colors.error,
  },
  bottomSpacer: {
    height: spacing.xl,
  },
});
