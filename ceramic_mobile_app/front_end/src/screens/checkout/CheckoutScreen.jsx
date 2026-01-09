import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, Alert } from 'react-native';
import { Text, Appbar, Button, TextInput, Divider, ActivityIndicator, Card } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import { colors, spacing, typography } from '../../constants/theme.js';
import { fetchCart, checkout } from '../../store/slices/cartSlice.js';

export const CheckoutScreen = () => {
  const dispatch = useDispatch();
  const navigation = useNavigation();
  const { cart, loading, error } = useSelector((state) => state.cart);
  const [checkingOut, setCheckingOut] = useState(false);
  
  // Shipping address form state
  const [shippingAddress, setShippingAddress] = useState({
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    postal_code: '',
    country: '',
    notes: '',
  });

  const [formErrors, setFormErrors] = useState({});

  useEffect(() => {
    dispatch(fetchCart());
  }, [dispatch]);

  const validateForm = () => {
    const errors = {};

    if (!shippingAddress.address_line1.trim()) {
      errors.address_line1 = 'Address is required';
    }
    if (!shippingAddress.city.trim()) {
      errors.city = 'City is required';
    }
    if (!shippingAddress.state.trim()) {
      errors.state = 'State is required';
    }
    if (!shippingAddress.postal_code.trim()) {
      errors.postal_code = 'Postal code is required';
    }
    if (!shippingAddress.country.trim()) {
      errors.country = 'Country is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (field, value) => {
    setShippingAddress(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error for this field when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: ''
      }));
    }
  };

  const handlePlaceOrder = async () => {
    if (!cart || cart.items.length === 0) {
      Alert.alert('Empty Cart', 'Your cart is empty. Add some items before checkout.');
      return;
    }

    if (!validateForm()) {
      Alert.alert('Invalid Information', 'Please fill in all required fields.');
      return;
    }

    setCheckingOut(true);
    
    try {
      const order = await dispatch(checkout(shippingAddress)).unwrap();
      
      Alert.alert(
        'Order Placed Successfully!',
        `Your order #${order.order_number} has been placed. Total: $${order.total_amount.toFixed(2)}`,
        [
          {
            text: 'View Order',
            onPress: () => navigation.navigate('OrderDetails', { orderId: order.id })
          },
          {
            text: 'Continue Shopping',
            onPress: () => navigation.navigate('Home')
          }
        ]
      );
    } catch (error) {
      Alert.alert('Checkout Failed', error.message || 'An error occurred during checkout. Please try again.');
    } finally {
      setCheckingOut(false);
    }
  };

  const handleGoBack = () => {
    navigation.goBack();
  };

  if (loading && !cart) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyTitle}>Your cart is empty</Text>
        <Text style={styles.emptySubtitle}>
          Add some items to your cart before checkout
        </Text>
        <Button 
          mode="contained" 
          onPress={() => navigation.navigate('Home')}
          style={styles.shopButton}
        >
          Continue Shopping
        </Button>
      </View>
    );
  }

  return (
    <View style={styles.container} testID="checkout-screen">
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={handleGoBack} testID="checkout-back-button" />
        <Appbar.Content title="Checkout" />
      </Appbar.Header>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Order Summary */}
        <Card style={styles.card}>
          <Text style={styles.sectionTitle}>Order Summary</Text>
          <Divider style={styles.divider} />
          
          {cart.items.map((item) => (
            <View key={item.id} style={styles.orderItem}>
              <View style={styles.itemInfo}>
                <Text style={styles.itemName}>{item.product_name}</Text>
                <Text style={styles.itemDetails}>Qty: {item.quantity}</Text>
              </View>
              <Text style={styles.itemTotal}>${item.total_price.toFixed(2)}</Text>
            </View>
          ))}

          <Divider style={styles.divider} />
          
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Subtotal</Text>
            <Text style={styles.summaryValue}>${cart.summary.subtotal.toFixed(2)}</Text>
          </View>
          
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Tax</Text>
            <Text style={styles.summaryValue}>${cart.summary.tax_amount.toFixed(2)}</Text>
          </View>
          
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Shipping</Text>
            <Text style={styles.summaryValue}>
              {cart.summary.shipping_amount === 0 ? 'FREE' : `$${cart.summary.shipping_amount.toFixed(2)}`}
            </Text>
          </View>
          
          <Divider style={styles.divider} />
          
          <View style={styles.summaryRow}>
            <Text style={styles.totalLabel}>Total</Text>
            <Text style={styles.totalValue}>${cart.summary.total_amount.toFixed(2)}</Text>
          </View>
        </Card>

        {/* Shipping Address */}
        <Card style={styles.card}>
          <Text style={styles.sectionTitle}>Shipping Address</Text>
          <Divider style={styles.divider} />
          
          <TextInput
            label="Address Line 1*"
            value={shippingAddress.address_line1}
            onChangeText={(text) => handleInputChange('address_line1', text)}
            style={styles.input}
            error={!!formErrors.address_line1}
            mode="outlined"
            testID="checkout-address-line1"
          />
          {formErrors.address_line1 && (
            <Text style={styles.errorText}>{formErrors.address_line1}</Text>
          )}
          
          <TextInput
            label="Address Line 2"
            value={shippingAddress.address_line2}
            onChangeText={(text) => handleInputChange('address_line2', text)}
            style={styles.input}
            mode="outlined"
          />

          <View style={styles.rowInputs}>
            <TextInput
              label="City*"
              value={shippingAddress.city}
              onChangeText={(text) => handleInputChange('city', text)}
              style={[styles.input, styles.halfInput]}
              error={!!formErrors.city}
              mode="outlined"
              testID="checkout-city"
            />
            <TextInput
              label="State*"
              value={shippingAddress.state}
              onChangeText={(text) => handleInputChange('state', text)}
              style={[styles.input, styles.halfInput]}
              error={!!formErrors.state}
              mode="outlined"
              testID="checkout-state"
            />
          </View>

          <View style={styles.rowErrors}>
            {formErrors.city && (
              <Text style={[styles.errorText, styles.halfError]}>{formErrors.city}</Text>
            )}
            {formErrors.state && (
              <Text style={[styles.errorText, styles.halfError]}>{formErrors.state}</Text>
            )}
          </View>

          <View style={styles.rowInputs}>
            <TextInput
              label="Postal Code*"
              value={shippingAddress.postal_code}
              onChangeText={(text) => handleInputChange('postal_code', text)}
              style={[styles.input, styles.halfInput]}
              error={!!formErrors.postal_code}
              mode="outlined"
              testID="checkout-postal-code"
            />
            <TextInput
              label="Country*"
              value={shippingAddress.country}
              onChangeText={(text) => handleInputChange('country', text)}
              style={[styles.input, styles.halfInput]}
              error={!!formErrors.country}
              mode="outlined"
              testID="checkout-country"
            />
          </View>

          <View style={styles.rowErrors}>
            {formErrors.postal_code && (
              <Text style={[styles.errorText, styles.halfError]}>{formErrors.postal_code}</Text>
            )}
            {formErrors.country && (
              <Text style={[styles.errorText, styles.halfError]}>{formErrors.country}</Text>
            )}
          </View>

          <TextInput
            label="Special Notes"
            value={shippingAddress.notes}
            onChangeText={(text) => handleInputChange('notes', text)}
            style={styles.input}
            multiline
            numberOfLines={3}
            mode="outlined"
          />
        </Card>

        {/* Place Order Button */}
        <View style={styles.buttonContainer}>
          <Button
            mode="contained"
            onPress={handlePlaceOrder}
            loading={checkingOut}
            disabled={checkingOut}
            style={styles.placeOrderButton}
            contentStyle={{ height: 48 }}
            testID="checkout-place-order-button"
          >
            {checkingOut ? 'Placing Order...' : `Place Order - $${cart.summary.total_amount.toFixed(2)}`}
          </Button>
        </View>
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
    padding: spacing.xl,
  },
  emptyTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
    textAlign: 'center',
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
  card: {
    marginBottom: spacing.md,
    padding: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  divider: {
    marginVertical: spacing.sm,
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
  input: {
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
  },
  rowInputs: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  halfInput: {
    width: '48%',
  },
  rowErrors: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  halfError: {
    width: '48%',
  },
  errorText: {
    color: colors.error,
    fontSize: typography.sizes.sm,
    marginBottom: spacing.sm,
  },
  buttonContainer: {
    marginTop: spacing.lg,
    marginBottom: spacing.xl,
  },
  placeOrderButton: {
    backgroundColor: colors.primary,
  },
});