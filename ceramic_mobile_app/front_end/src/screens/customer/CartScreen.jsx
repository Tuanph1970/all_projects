import React, { useEffect, useState } from 'react';
import { View, StyleSheet, ScrollView, Alert, RefreshControl } from 'react-native';
import { Text, Appbar, Button, IconButton, Divider, ActivityIndicator, Card } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import { colors, spacing, typography } from '../../constants/theme.js';
import { fetchCart, removeFromCart, updateCartItem, clearCart } from '../../store/slices/cartSlice.js';
import { useTranslation } from '@i18n';

const CartItemCard = ({ item, onUpdateQuantity, onRemove, t, index }) => {
  const [quantity, setQuantity] = useState(item.quantity);

  const handleQuantityChange = (newQuantity) => {
    if (newQuantity <= 0) {
      Alert.alert(
        t('cart.removeItem'),
        t('cart.removeItemConfirm'),
        [
          { text: t('common.cancel'), style: 'cancel' },
          { text: t('cart.remove'), style: 'destructive', onPress: () => onRemove(item.id) },
        ]
      );
      return;
    }
    setQuantity(newQuantity);
    onUpdateQuantity(item.id, newQuantity);
  };

  return (
    <Card style={styles.cartItem} testID={`cart-item-${index}`}>
      <View style={styles.itemContent}>
        <View style={styles.itemInfo}>
          <Text style={styles.productName} testID={`cart-item-name-${index}`}>{item.product_name}</Text>
          {item.product_category && (
            <Text style={styles.productCategory} testID={`cart-item-category-${index}`}>{item.product_category}</Text>
          )}
          <Text style={styles.productPrice} testID={`cart-item-price-${index}`}>${parseFloat(item.unit_price).toFixed(2)}</Text>
        </View>

        <View style={styles.itemActions}>
          <View style={styles.quantityControls} testID={`cart-item-quantity-controls-${index}`}>
            <IconButton
              icon="minus"
              mode="outlined"
              size={20}
              onPress={() => handleQuantityChange(quantity - 1)}
              disabled={quantity <= 1}
              testID={`cart-item-quantity-minus-${index}`}
            />
            <Text style={styles.quantityText} testID={`cart-item-quantity-${index}`}>{quantity}</Text>
            <IconButton
              icon="plus"
              mode="outlined"
              size={20}
              onPress={() => handleQuantityChange(quantity + 1)}
              testID={`cart-item-quantity-plus-${index}`}
            />
          </View>

          <View style={styles.itemTotal}>
            <Text style={styles.totalPrice} testID={`cart-item-total-${index}`}>${parseFloat(item.total_price).toFixed(2)}</Text>
            <IconButton
              icon="delete"
              iconColor={colors.error}
              size={20}
              onPress={() => onRemove(item.id)}
              testID={`cart-item-remove-${index}`}
            />
          </View>
        </View>
      </View>
    </Card>
  );
};

export const CartScreen = () => {
  const dispatch = useDispatch();
  const navigation = useNavigation();
  const t = useTranslation();
  const { cart, loading, error } = useSelector((state) => state.cart);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    dispatch(fetchCart());
  }, [dispatch]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await dispatch(fetchCart());
    setRefreshing(false);
  };

  const handleUpdateQuantity = (itemId, quantity) => {
    dispatch(updateCartItem({ itemId, quantity }));
  };

  const handleRemoveItem = (itemId) => {
    dispatch(removeFromCart(itemId));
  };

  const handleClearCart = () => {
    Alert.alert(
      t('cart.clearCart'),
      t('cart.clearCartConfirm'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        { text: t('cart.clear'), style: 'destructive', onPress: () => dispatch(clearCart()) },
      ]
    );
  };

  const handleCheckout = () => {
    if (!cart || !cart.items || cart.items.length === 0) {
      Alert.alert(t('cart.empty'), t('cart.emptyCheckout'));
      return;
    }
    navigation.navigate('Checkout');
  };

  if (loading && !cart) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title={t('cart.title')} />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>{t('cart.loadingCart')}</Text>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title={t('cart.title')} />
        </Appbar.Header>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{t('cart.errorLoading')}</Text>
          <Button mode="contained" onPress={() => dispatch(fetchCart())}>
            {t('common.retry')}
          </Button>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container} testID="cart-screen">
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="cart-back-button" />
        <Appbar.Content title={t('cart.title')} />
        {cart && cart.items && cart.items.length > 0 && (
          <Appbar.Action icon="delete-sweep" onPress={handleClearCart} testID="cart-clear-button" />
        )}
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
        {!cart || !cart.items || cart.items.length === 0 ? (
          <View style={styles.emptyContainer} testID="cart-empty">
            <Text style={styles.emptyTitle}>{t('cart.empty')}</Text>
            <Text style={styles.emptySubtitle}>
              {t('cart.emptyMessage')}
            </Text>
            <Button
              mode="contained"
              style={styles.shopButton}
              onPress={() => navigation.navigate('Home')}
              testID="cart-continue-shopping-button"
            >
              {t('cart.continueShopping')}
            </Button>
          </View>
        ) : (
          <>
            <View style={styles.itemsList} testID="cart-items-list">
              {cart.items.map((item, index) => (
                <CartItemCard
                  key={item.id}
                  item={item}
                  index={index}
                  onUpdateQuantity={handleUpdateQuantity}
                  onRemove={handleRemoveItem}
                  t={t}
                />
              ))}
            </View>

            <Card style={styles.summaryCard} testID="cart-summary">
              <Text style={styles.summaryTitle}>{t('cart.orderSummary')}</Text>
              <Divider style={styles.divider} />

              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>{t('cart.subtotal')} ({cart.summary.item_count} {t('cart.items')})</Text>
                <Text style={styles.summaryValue} testID="cart-subtotal">${parseFloat(cart.summary.subtotal).toFixed(2)}</Text>
              </View>

              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>{t('cart.tax')}</Text>
                <Text style={styles.summaryValue} testID="cart-tax">${parseFloat(cart.summary.tax_amount).toFixed(2)}</Text>
              </View>

              <View style={styles.summaryRow}>
                <Text style={styles.summaryLabel}>{t('cart.shipping')}</Text>
                <Text style={styles.summaryValue} testID="cart-shipping">
                  {parseFloat(cart.summary.shipping_amount) === 0 ? t('cart.free') : `$${parseFloat(cart.summary.shipping_amount).toFixed(2)}`}
                </Text>
              </View>

              <Divider style={styles.divider} />

              <View style={styles.summaryRow}>
                <Text style={styles.totalLabel}>{t('cart.total')}</Text>
                <Text style={styles.totalValue} testID="cart-total">${parseFloat(cart.summary.total_amount).toFixed(2)}</Text>
              </View>

              <Button
                mode="contained"
                style={styles.checkoutButton}
                onPress={handleCheckout}
                contentStyle={{ height: 48 }}
                testID="cart-checkout-button"
              >
                {t('cart.proceedToCheckout')}
              </Button>
            </Card>
          </>
        )}
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
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
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
  itemsList: {
    marginBottom: spacing.md,
  },
  cartItem: {
    marginBottom: spacing.sm,
    padding: spacing.md,
  },
  itemContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  itemInfo: {
    flex: 1,
    marginRight: spacing.md,
  },
  productName: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  productCategory: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginBottom: spacing.xs,
  },
  productPrice: {
    fontSize: typography.sizes.md,
    color: colors.primary,
    fontWeight: typography.weights.medium,
  },
  itemActions: {
    alignItems: 'flex-end',
  },
  quantityControls: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  quantityText: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    marginHorizontal: spacing.sm,
    minWidth: 30,
    textAlign: 'center',
  },
  itemTotal: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  totalPrice: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
    marginRight: spacing.sm,
  },
  summaryCard: {
    marginTop: spacing.md,
    padding: spacing.lg,
  },
  summaryTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  divider: {
    marginVertical: spacing.sm,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
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
  checkoutButton: {
    marginTop: spacing.lg,
    backgroundColor: colors.primary,
  },
});
