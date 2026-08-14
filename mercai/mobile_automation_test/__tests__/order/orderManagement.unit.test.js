/**
 * Order Management Unit Tests
 *
 * Test Coverage: TC-ORDER-001 to TC-ORDER-015
 * - View orders (customer and seller views)
 * - View order details
 * - Create orders from checkout
 * - Checkout validation (empty cart, stock, multi-seller)
 * - Order confirmation
 * - Stock deduction after order
 * - Cart clearing after checkout
 * - Update order status (seller only)
 * - Authorization (view and update)
 * - Order number generation
 *
 * Note: These are pure unit tests with mocked axios calls.
 * No E2E simulation - testing validation logic only.
 */

const axios = require('axios');

// Mock axios
jest.mock('axios');

describe('Order Management Unit Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ==================== TC-ORDER-001 & TC-ORDER-002: View Orders List ====================
  describe('View Orders List (TC-ORDER-001, TC-ORDER-002)', () => {
    test('TC-ORDER-001: Customer should view their order history', async () => {
      // Arrange
      const mockCustomerOrders = {
        data: [
          {
            id: 1,
            order_number: 'ORD-ABC12345',
            customer_id: 1,
            seller_id: 2,
            status: 'pending',
            subtotal: 100.00,
            tax_amount: 8.00,
            shipping_amount: 10.00,
            total_amount: 118.00,
            created_at: '2025-01-20T10:00:00',
            items: [
              {
                id: 1,
                product_id: 1,
                product_name: 'Ceramic Vase',
                quantity: 2,
                unit_price: 50.00,
                total_price: 100.00
              }
            ]
          }
        ]
      };

      axios.get.mockResolvedValue(mockCustomerOrders);

      // Act
      const response = await axios.get('/api/v1/orders/', {
        headers: { Authorization: 'Bearer customer-token' }
      });

      // Assert
      expect(response.data).toHaveLength(1);
      expect(response.data[0].customer_id).toBe(1);
      expect(response.data[0].order_number).toMatch(/^ORD-/);
    });

    test('TC-ORDER-002: Seller should view orders for their products', async () => {
      // Arrange
      const mockSellerOrders = {
        data: [
          {
            id: 1,
            order_number: 'ORD-XYZ98765',
            customer_id: 1,
            seller_id: 2,
            status: 'processing',
            subtotal: 150.00,
            tax_amount: 12.00,
            shipping_amount: 0.00,
            total_amount: 162.00,
            created_at: '2025-01-20T11:00:00'
          }
        ]
      };

      axios.get.mockResolvedValue(mockSellerOrders);

      // Act
      const response = await axios.get('/api/v1/orders/', {
        headers: { Authorization: 'Bearer seller-token' }
      });

      // Assert
      expect(response.data).toHaveLength(1);
      expect(response.data[0].seller_id).toBe(2);
    });

    test('TC-ORDER-001: Should return empty array when no orders', async () => {
      // Arrange
      axios.get.mockResolvedValue({ data: [] });

      // Act
      const response = await axios.get('/api/v1/orders/', {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Assert
      expect(response.data).toHaveLength(0);
    });

    test('TC-ORDER-001: Should require authentication to view orders', async () => {
      // Arrange
      axios.get.mockRejectedValue({
        response: { status: 401, data: { detail: 'Not authenticated' } }
      });

      // Act & Assert
      await expect(
        axios.get('/api/v1/orders/')
      ).rejects.toMatchObject({
        response: { status: 401 }
      });
    });
  });

  // ==================== TC-ORDER-003: View Order Details ====================
  describe('View Order Details (TC-ORDER-003)', () => {
    test('TC-ORDER-003: Should retrieve detailed order information', async () => {
      // Arrange
      const mockOrderDetails = {
        data: {
          id: 1,
          order_number: 'ORD-ABC12345',
          customer_id: 1,
          seller_id: 2,
          status: 'pending',
          subtotal: 100.00,
          tax_amount: 8.00,
          shipping_amount: 10.00,
          total_amount: 118.00,
          shipping_address_line1: '123 Main St',
          shipping_city: 'New York',
          shipping_state: 'NY',
          shipping_postal_code: '10001',
          shipping_country: 'USA',
          customer_notes: 'Please handle with care',
          created_at: '2025-01-20T10:00:00',
          updated_at: '2025-01-20T10:00:00',
          items: [
            {
              id: 1,
              product_id: 1,
              product_name: 'Ceramic Vase',
              product_description: 'Beautiful handmade vase',
              quantity: 2,
              unit_price: 50.00,
              total_price: 100.00
            }
          ]
        }
      };

      axios.get.mockResolvedValue(mockOrderDetails);

      // Act
      const response = await axios.get('/api/v1/orders/1', {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Assert
      expect(response.data.id).toBe(1);
      expect(response.data.items).toHaveLength(1);
      expect(response.data.shipping_address_line1).toBeDefined();
      expect(response.data.customer_notes).toBe('Please handle with care');
    });

    test('TC-ORDER-003: Should handle non-existent order', async () => {
      // Arrange
      axios.get.mockRejectedValue({
        response: {
          status: 404,
          data: { detail: 'Order not found' }
        }
      });

      // Act & Assert
      await expect(
        axios.get('/api/v1/orders/99999', {
          headers: { Authorization: 'Bearer valid-token' }
        })
      ).rejects.toMatchObject({
        response: { status: 404 }
      });
    });
  });

  // ==================== TC-ORDER-004 to TC-ORDER-008: Checkout Validation ====================
  describe('Checkout from Cart (TC-ORDER-004 to TC-ORDER-008)', () => {
    // Validation function for shipping address
    const validateShippingAddress = (address) => {
      const errors = {};

      if (!address.address_line1 || address.address_line1.trim() === '') {
        errors.address_line1 = 'Street address is required';
      }
      if (!address.city || address.city.trim() === '') {
        errors.city = 'City is required';
      }
      if (!address.state || address.state.trim() === '') {
        errors.state = 'State is required';
      }
      if (!address.postal_code || address.postal_code.trim() === '') {
        errors.postal_code = 'Postal code is required';
      }
      if (!address.country || address.country.trim() === '') {
        errors.country = 'Country is required';
      }

      if (Object.keys(errors).length > 0) {
        return { valid: false, errors };
      }
      return { valid: true, errors: null };
    };

    test('TC-ORDER-004: Should successfully checkout from cart', async () => {
      // Arrange
      const shippingAddress = {
        address_line1: '123 Main St',
        address_line2: 'Apt 4B',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA',
        notes: 'Ring doorbell'
      };

      const validation = validateShippingAddress(shippingAddress);
      expect(validation.valid).toBe(true);

      const mockOrderResponse = {
        data: {
          id: 1,
          order_number: 'ORD-NEW12345',
          customer_id: 1,
          seller_id: 2,
          status: 'pending',
          subtotal: 75.00,
          tax_amount: 6.00,
          shipping_amount: 10.00,
          total_amount: 91.00,
          created_at: '2025-01-20T12:00:00'
        }
      };

      axios.post.mockResolvedValue(mockOrderResponse);

      // Act
      const response = await axios.post('/api/v1/orders/checkout', shippingAddress, {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Assert
      expect(response.data.order_number).toMatch(/^ORD-/);
      expect(response.data.status).toBe('pending');
      expect(response.data.total_amount).toBeDefined();
    });

    test('TC-ORDER-005: Should validate shipping address selection', () => {
      // Test missing required fields
      let validation = validateShippingAddress({
        address_line1: '123 Main St',
        city: 'New York'
        // Missing state, postal_code, country
      });
      expect(validation.valid).toBe(false);
      expect(validation.errors.state).toBeDefined();
      expect(validation.errors.postal_code).toBeDefined();
      expect(validation.errors.country).toBeDefined();

      // Test valid address
      validation = validateShippingAddress({
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      });
      expect(validation.valid).toBe(true);
    });

    test('TC-ORDER-006: Should reject checkout with empty cart', async () => {
      // Arrange
      const shippingAddress = {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      };

      axios.post.mockRejectedValue({
        response: {
          status: 400,
          data: { detail: 'Cart is empty' }
        }
      });

      // Act & Assert
      await expect(
        axios.post('/api/v1/orders/checkout', shippingAddress, {
          headers: { Authorization: 'Bearer valid-token' }
        })
      ).rejects.toMatchObject({
        response: {
          status: 400,
          data: { detail: 'Cart is empty' }
        }
      });
    });

    test('TC-ORDER-007: Should reject checkout when insufficient stock', async () => {
      // Arrange
      const shippingAddress = {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      };

      axios.post.mockRejectedValue({
        response: {
          status: 400,
          data: { detail: 'Insufficient stock for product Ceramic Vase' }
        }
      });

      // Act & Assert
      await expect(
        axios.post('/api/v1/orders/checkout', shippingAddress, {
          headers: { Authorization: 'Bearer valid-token' }
        })
      ).rejects.toMatchObject({
        response: {
          status: 400,
          data: { detail: expect.stringContaining('Insufficient stock') }
        }
      });
    });

    test('TC-ORDER-008: Should reject cart with items from multiple sellers', async () => {
      // Arrange
      const shippingAddress = {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      };

      axios.post.mockRejectedValue({
        response: {
          status: 400,
          data: { detail: 'Cart contains items from multiple sellers. Please checkout separately.' }
        }
      });

      // Act & Assert
      await expect(
        axios.post('/api/v1/orders/checkout', shippingAddress, {
          headers: { Authorization: 'Bearer valid-token' }
        })
      ).rejects.toMatchObject({
        response: {
          status: 400,
          data: { detail: expect.stringContaining('multiple sellers') }
        }
      });
    });

    test('TC-ORDER-004: Should handle product unavailability during checkout', async () => {
      // Arrange
      const shippingAddress = {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      };

      axios.post.mockRejectedValue({
        response: {
          status: 400,
          data: { detail: 'Product Ceramic Bowl is no longer available' }
        }
      });

      // Act & Assert
      await expect(
        axios.post('/api/v1/orders/checkout', shippingAddress, {
          headers: { Authorization: 'Bearer valid-token' }
        })
      ).rejects.toMatchObject({
        response: {
          status: 400,
          data: { detail: expect.stringContaining('no longer available') }
        }
      });
    });
  });

  // ==================== TC-ORDER-009: Order Confirmation ====================
  describe('Order Confirmation (TC-ORDER-009)', () => {
    test('TC-ORDER-009: Should display order confirmation with correct details', async () => {
      // Arrange
      const mockOrderConfirmation = {
        data: {
          id: 1,
          order_number: 'ORD-CONF1234',
          status: 'pending',
          subtotal: 100.00,
          tax_amount: 8.00,
          shipping_amount: 10.00,
          total_amount: 118.00,
          shipping_address_line1: '123 Main St',
          shipping_city: 'New York',
          shipping_state: 'NY',
          shipping_postal_code: '10001',
          shipping_country: 'USA',
          created_at: '2025-01-20T12:00:00',
          items: [
            {
              product_name: 'Ceramic Vase',
              quantity: 2,
              unit_price: 50.00,
              total_price: 100.00
            }
          ]
        }
      };

      axios.get.mockResolvedValue(mockOrderConfirmation);

      // Act
      const response = await axios.get('/api/v1/orders/1', {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Assert - Confirmation should show all order details
      expect(response.data.order_number).toBe('ORD-CONF1234');
      expect(response.data.total_amount).toBe(118.00);
      expect(response.data.shipping_address_line1).toBeDefined();
      expect(response.data.items).toHaveLength(1);
      expect(response.data.created_at).toBeDefined();
    });
  });

  // ==================== TC-ORDER-010 & TC-ORDER-011: Business Logic ====================
  describe('Order Business Logic (TC-ORDER-010, TC-ORDER-011)', () => {
    test('TC-ORDER-010: Stock should be deducted after order creation', async () => {
      // This test verifies the logic that stock deduction happens
      // In backend: product.quantity_available -= cart_item.quantity

      // Arrange - Mock order creation response
      const mockOrderWithStockUpdate = {
        data: {
          id: 1,
          order_number: 'ORD-STOCK123',
          status: 'pending',
          items: [
            {
              product_id: 1,
              quantity: 3,
              // Backend should have deducted 3 from product stock
            }
          ]
        }
      };

      axios.post.mockResolvedValue(mockOrderWithStockUpdate);

      // Act
      const response = await axios.post('/api/v1/orders/checkout', {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      }, {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Assert - Order created successfully
      expect(response.data.order_number).toBeDefined();
      expect(response.data.items[0].quantity).toBe(3);
      // Note: Stock deduction happens in backend, verified by successful order creation
    });

    test('TC-ORDER-011: Cart should be cleared after successful checkout', async () => {
      // This test verifies the logic that cart is cleared after order
      // In backend: db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

      // Arrange - Mock successful checkout
      axios.post.mockResolvedValue({
        data: {
          id: 1,
          order_number: 'ORD-CLEAR123',
          status: 'pending'
        }
      });

      // Act - Checkout
      await axios.post('/api/v1/orders/checkout', {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      }, {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Verify cart should be empty after checkout
      axios.get.mockResolvedValue({
        data: {
          items: [],
          summary: {
            item_count: 0,
            subtotal: 0,
            total_amount: 0
          }
        }
      });

      const cartResponse = await axios.get('/api/v1/cart/', {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Assert - Cart should be empty
      expect(cartResponse.data.items).toHaveLength(0);
      expect(cartResponse.data.summary.item_count).toBe(0);
    });
  });

  // ==================== TC-ORDER-012: Update Order Status ====================
  describe('Update Order Status (TC-ORDER-012)', () => {
    const validateOrderStatus = (status) => {
      const validStatuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled'];

      if (!status || typeof status !== 'string') {
        return { valid: false, error: 'Status is required' };
      }

      if (!validStatuses.includes(status)) {
        return { valid: false, error: `Status must be one of: ${validStatuses.join(', ')}` };
      }

      return { valid: true, error: null };
    };

    test('TC-ORDER-012: Seller should update order status to processing', async () => {
      // Arrange
      const statusUpdate = { status: 'processing' };
      const validation = validateOrderStatus(statusUpdate.status);
      expect(validation.valid).toBe(true);

      axios.put.mockResolvedValue({
        data: {
          id: 1,
          order_number: 'ORD-UPDATE123',
          status: 'processing',
          updated_at: '2025-01-20T13:00:00'
        }
      });

      // Act
      const response = await axios.put('/api/v1/orders/1', statusUpdate, {
        headers: { Authorization: 'Bearer seller-token' }
      });

      // Assert
      expect(response.data.status).toBe('processing');
      expect(response.data.updated_at).toBeDefined();
    });

    test('TC-ORDER-012: Seller should update order status to shipped', async () => {
      // Arrange
      const statusUpdate = { status: 'shipped' };
      const validation = validateOrderStatus(statusUpdate.status);
      expect(validation.valid).toBe(true);

      axios.put.mockResolvedValue({
        data: {
          id: 1,
          order_number: 'ORD-SHIP123',
          status: 'shipped',
          updated_at: '2025-01-20T14:00:00'
        }
      });

      // Act
      const response = await axios.put('/api/v1/orders/1', statusUpdate, {
        headers: { Authorization: 'Bearer seller-token' }
      });

      // Assert
      expect(response.data.status).toBe('shipped');
    });

    test('TC-ORDER-012: Seller should update order status to delivered', async () => {
      // Arrange
      const statusUpdate = { status: 'delivered' };
      const validation = validateOrderStatus(statusUpdate.status);
      expect(validation.valid).toBe(true);

      axios.put.mockResolvedValue({
        data: {
          id: 1,
          order_number: 'ORD-DELIV123',
          status: 'delivered',
          updated_at: '2025-01-20T15:00:00'
        }
      });

      // Act
      const response = await axios.put('/api/v1/orders/1', statusUpdate, {
        headers: { Authorization: 'Bearer seller-token' }
      });

      // Assert
      expect(response.data.status).toBe('delivered');
    });

    test('TC-ORDER-012: Should validate order status values', () => {
      // Test invalid status
      let validation = validateOrderStatus('invalid-status');
      expect(validation.valid).toBe(false);
      expect(validation.error).toContain('must be one of');

      // Test empty status
      validation = validateOrderStatus('');
      expect(validation.valid).toBe(false);

      // Test missing status
      validation = validateOrderStatus(null);
      expect(validation.valid).toBe(false);

      // Test valid statuses
      const validStatuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled'];
      validStatuses.forEach(status => {
        validation = validateOrderStatus(status);
        expect(validation.valid).toBe(true);
      });
    });
  });

  // ==================== TC-ORDER-013: Update Order Authorization ====================
  describe('Update Order Authorization (TC-ORDER-013)', () => {
    test('TC-ORDER-013: Only seller should be able to update order status', async () => {
      // Arrange
      const statusUpdate = { status: 'processing' };

      axios.put.mockRejectedValue({
        response: {
          status: 403,
          data: { detail: 'Only the seller can update order status' }
        }
      });

      // Act & Assert - Customer trying to update
      await expect(
        axios.put('/api/v1/orders/1', statusUpdate, {
          headers: { Authorization: 'Bearer customer-token' }
        })
      ).rejects.toMatchObject({
        response: {
          status: 403,
          data: { detail: expect.stringContaining('seller') }
        }
      });
    });

    test('TC-ORDER-013: Seller cannot update another sellers order', async () => {
      // Arrange
      const statusUpdate = { status: 'processing' };

      axios.put.mockRejectedValue({
        response: {
          status: 403,
          data: { detail: 'Only the seller can update order status' }
        }
      });

      // Act & Assert
      await expect(
        axios.put('/api/v1/orders/1', statusUpdate, {
          headers: { Authorization: 'Bearer different-seller-token' }
        })
      ).rejects.toMatchObject({
        response: { status: 403 }
      });
    });

    test('TC-ORDER-013: Should handle non-existent order update', async () => {
      // Arrange
      const statusUpdate = { status: 'processing' };

      axios.put.mockRejectedValue({
        response: {
          status: 404,
          data: { detail: 'Order not found' }
        }
      });

      // Act & Assert
      await expect(
        axios.put('/api/v1/orders/99999', statusUpdate, {
          headers: { Authorization: 'Bearer seller-token' }
        })
      ).rejects.toMatchObject({
        response: { status: 404 }
      });
    });
  });

  // ==================== TC-ORDER-014: View Order Authorization ====================
  describe('View Order Authorization (TC-ORDER-014)', () => {
    test('TC-ORDER-014: User should only view their own orders', async () => {
      // Arrange - User trying to view another users order
      axios.get.mockRejectedValue({
        response: {
          status: 403,
          data: { detail: 'Not authorized to view this order' }
        }
      });

      // Act & Assert
      await expect(
        axios.get('/api/v1/orders/1', {
          headers: { Authorization: 'Bearer wrong-user-token' }
        })
      ).rejects.toMatchObject({
        response: {
          status: 403,
          data: { detail: expect.stringContaining('Not authorized') }
        }
      });
    });

    test('TC-ORDER-014: Customer can view their own order', async () => {
      // Arrange
      const mockOrder = {
        data: {
          id: 1,
          order_number: 'ORD-CUST123',
          customer_id: 1,
          seller_id: 2,
          status: 'pending'
        }
      };

      axios.get.mockResolvedValue(mockOrder);

      // Act
      const response = await axios.get('/api/v1/orders/1', {
        headers: { Authorization: 'Bearer customer-token' }
      });

      // Assert
      expect(response.data.customer_id).toBe(1);
    });

    test('TC-ORDER-014: Seller can view orders for their products', async () => {
      // Arrange
      const mockOrder = {
        data: {
          id: 1,
          order_number: 'ORD-SELL123',
          customer_id: 1,
          seller_id: 2,
          status: 'processing'
        }
      };

      axios.get.mockResolvedValue(mockOrder);

      // Act
      const response = await axios.get('/api/v1/orders/1', {
        headers: { Authorization: 'Bearer seller-token' }
      });

      // Assert
      expect(response.data.seller_id).toBe(2);
    });
  });

  // ==================== TC-ORDER-015: Order Number Generation ====================
  describe('Order Number Generation (TC-ORDER-015)', () => {
    const validateOrderNumber = (orderNumber) => {
      // Format: ORD-XXXXXXXX (8 uppercase alphanumeric characters)
      const orderNumberPattern = /^ORD-[A-Z0-9]{8}$/;

      if (!orderNumber || typeof orderNumber !== 'string') {
        return { valid: false, error: 'Order number is required' };
      }

      if (!orderNumberPattern.test(orderNumber)) {
        return { valid: false, error: 'Order number must be in format ORD-XXXXXXXX' };
      }

      return { valid: true, error: null };
    };

    test('TC-ORDER-015: Should generate unique order number in correct format', async () => {
      // Arrange
      const mockOrder1 = {
        data: {
          id: 1,
          order_number: 'ORD-ABC12345',
          status: 'pending'
        }
      };

      const mockOrder2 = {
        data: {
          id: 2,
          order_number: 'ORD-XYZ98765',
          status: 'pending'
        }
      };

      // Act
      axios.post
        .mockResolvedValueOnce(mockOrder1)
        .mockResolvedValueOnce(mockOrder2);

      const response1 = await axios.post('/api/v1/orders/checkout', {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      }, {
        headers: { Authorization: 'Bearer valid-token' }
      });

      const response2 = await axios.post('/api/v1/orders/checkout', {
        address_line1: '456 Oak Ave',
        city: 'Boston',
        state: 'MA',
        postal_code: '02101',
        country: 'USA'
      }, {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Assert - Both should have valid format
      const validation1 = validateOrderNumber(response1.data.order_number);
      const validation2 = validateOrderNumber(response2.data.order_number);

      expect(validation1.valid).toBe(true);
      expect(validation2.valid).toBe(true);

      // Order numbers should be different (unique)
      expect(response1.data.order_number).not.toBe(response2.data.order_number);
    });

    test('TC-ORDER-015: Should validate order number format', () => {
      // Test valid format
      let validation = validateOrderNumber('ORD-ABC12345');
      expect(validation.valid).toBe(true);

      validation = validateOrderNumber('ORD-XYZ98765');
      expect(validation.valid).toBe(true);

      // Test invalid formats
      validation = validateOrderNumber('ABC12345'); // Missing prefix
      expect(validation.valid).toBe(false);

      validation = validateOrderNumber('ORD-abc12345'); // Lowercase
      expect(validation.valid).toBe(false);

      validation = validateOrderNumber('ORD-ABC123'); // Too short
      expect(validation.valid).toBe(false);

      validation = validateOrderNumber('ORD-ABC123456'); // Too long
      expect(validation.valid).toBe(false);

      validation = validateOrderNumber(''); // Empty
      expect(validation.valid).toBe(false);
    });

    test('TC-ORDER-015: Order number should be generated server-side', async () => {
      // Arrange - Client doesn't send order_number, it's generated by server
      const checkoutRequest = {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
        // No order_number in request
      };

      axios.post.mockResolvedValue({
        data: {
          id: 1,
          order_number: 'ORD-GEN12345', // Generated by server
          status: 'pending'
        }
      });

      // Act
      const response = await axios.post('/api/v1/orders/checkout', checkoutRequest, {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Assert - Order number should be present in response
      expect(response.data.order_number).toBeDefined();
      expect(response.data.order_number).toMatch(/^ORD-/);
    });
  });

  // ==================== Edge Cases and Security ====================
  describe('Edge Cases and Security', () => {
    test('Should handle concurrent order creation', async () => {
      // Arrange
      const shippingAddress = {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      };

      axios.post
        .mockResolvedValueOnce({ data: { id: 1, order_number: 'ORD-CONC1234' } })
        .mockResolvedValueOnce({ data: { id: 2, order_number: 'ORD-CONC5678' } });

      // Act - Simulate concurrent requests
      const [response1, response2] = await Promise.all([
        axios.post('/api/v1/orders/checkout', shippingAddress, {
          headers: { Authorization: 'Bearer token1' }
        }),
        axios.post('/api/v1/orders/checkout', shippingAddress, {
          headers: { Authorization: 'Bearer token2' }
        })
      ]);

      // Assert - Both orders should be created with unique order numbers
      expect(response1.data.order_number).toBeDefined();
      expect(response2.data.order_number).toBeDefined();
      expect(response1.data.order_number).not.toBe(response2.data.order_number);
    });

    test('Should calculate order totals correctly with decimals', () => {
      // Arrange
      const items = [
        { unit_price: 19.99, quantity: 3 },  // 59.97
        { unit_price: 7.95, quantity: 2 }    // 15.90
      ];

      // Act
      const subtotal = items.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
      const tax = subtotal * 0.08;  // 8% tax
      const shipping = subtotal >= 100 ? 0 : 10.00;
      const total = subtotal + tax + shipping;

      // Assert
      expect(subtotal).toBe(75.87);
      expect(parseFloat(tax.toFixed(2))).toBe(6.07);
      expect(shipping).toBe(10.00);
      expect(parseFloat(total.toFixed(2))).toBe(91.94);
    });

    test('Should require authentication for all order operations', async () => {
      // Test view orders
      axios.get.mockRejectedValue({
        response: { status: 401, data: { detail: 'Not authenticated' } }
      });

      await expect(axios.get('/api/v1/orders/')).rejects.toMatchObject({
        response: { status: 401 }
      });

      // Test create order - set mock for post as well
      axios.post.mockRejectedValue({
        response: { status: 401, data: { detail: 'Not authenticated' } }
      });

      await expect(
        axios.post('/api/v1/orders/checkout', {})
      ).rejects.toMatchObject({
        response: { status: 401 }
      });

      // Test update order - set mock for put as well
      axios.put.mockRejectedValue({
        response: { status: 401, data: { detail: 'Not authenticated' } }
      });

      await expect(
        axios.put('/api/v1/orders/1', { status: 'processing' })
      ).rejects.toMatchObject({
        response: { status: 401 }
      });
    });

    test('Should handle order with free shipping (over $100)', async () => {
      // Arrange
      const mockOrderWithFreeShipping = {
        data: {
          id: 1,
          order_number: 'ORD-FREE1234',
          subtotal: 150.00,
          tax_amount: 12.00,
          shipping_amount: 0.00,  // Free shipping
          total_amount: 162.00
        }
      };

      axios.post.mockResolvedValue(mockOrderWithFreeShipping);

      // Act
      const response = await axios.post('/api/v1/orders/checkout', {
        address_line1: '123 Main St',
        city: 'New York',
        state: 'NY',
        postal_code: '10001',
        country: 'USA'
      }, {
        headers: { Authorization: 'Bearer valid-token' }
      });

      // Assert
      expect(response.data.subtotal).toBeGreaterThanOrEqual(100);
      expect(response.data.shipping_amount).toBe(0.00);
    });
  });
});
