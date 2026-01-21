import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

// Order status enum matching backend
export const OrderStatus = {
  PENDING: 'PENDING',
  CONFIRMED: 'CONFIRMED',
  PROCESSING: 'PROCESSING',
  SHIPPED: 'SHIPPED',
  DELIVERED: 'DELIVERED',
  CANCELLED: 'CANCELLED',
  REFUNDED: 'REFUNDED'
};

export const PaymentStatus = {
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
  REFUNDED: 'REFUNDED'
};

class OrderFulfillmentService {
  // Use SELLER_FULFILLMENT endpoint for all order operations
  // Backend API: /api/v1/seller/fulfillment/orders
  ordersEndpoint = API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT;
  statusEndpoint = API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT;

  // Get paginated list of seller's orders
  async getOrders(params = {}) {
    const response = await apiClient.get(this.ordersEndpoint, {
      params
    });

    // Backend returns {orders: [...], pagination: {...}} format
    // Handle various response structures for compatibility
    const ordersArray = response.orders || (Array.isArray(response) ? response : (response.data?.orders || response.data || []));

    // Apply client-side status filtering if specified
    let filteredOrders = ordersArray;
    if (params.status) {
      filteredOrders = ordersArray.filter(
        order => order.status?.toUpperCase() === params.status.toUpperCase()
      );
    }

    // Apply client-side search if specified
    if (params.search) {
      const searchLower = params.search.toLowerCase();
      filteredOrders = filteredOrders.filter(order =>
        order.order_number?.toLowerCase().includes(searchLower) ||
        order.customer_name?.toLowerCase().includes(searchLower)
      );
    }

    // Transform to expected format with pagination
    return {
      orders: filteredOrders.map(order => ({
        ...order,
        total_amount: parseFloat(order.total_amount) || 0,
        customer_name: order.customer_name ||
          (order.customer ? `${order.customer.first_name || ''} ${order.customer.last_name || ''}`.trim() : null) ||
          `Customer #${order.customer_id}`,
        // Ensure date field is available (try different field names)
        created_at: order.created_at || order.order_date || order.date || new Date().toISOString()
      })),
      pagination: {
        current_page: params.page || 1,
        total_pages: 1,
        has_next: false,
        has_prev: false
      }
    };
  }

  // Get detailed order information
  async getOrderDetails(orderId) {
    return await apiClient.get(`${this.ordersEndpoint}/${orderId}`);
  }

  // Update order status (uses PATCH /{order_id}/status as per backend API)
  // Backend expects lowercase status: 'pending', 'confirmed', 'processing', etc.
  async updateOrderStatus(orderId, statusUpdate) {
    const url = `${this.statusEndpoint}/${orderId}/status`;
    // Convert status to lowercase for backend API
    const body = {
      ...statusUpdate,
      status: statusUpdate.status?.toLowerCase()
    };
    console.log('[DEBUG] updateOrderStatus URL:', url);
    console.log('[DEBUG] updateOrderStatus body:', JSON.stringify(body));
    try {
      const response = await apiClient.patch(url, body);
      console.log('[DEBUG] updateOrderStatus SUCCESS:', JSON.stringify(response));
      return response;
    } catch (error) {
      console.error('[DEBUG] updateOrderStatus FAILED');
      console.error('[DEBUG] Error status:', error.response?.status);
      console.error('[DEBUG] Error data:', JSON.stringify(error.response?.data));
      console.error('[DEBUG] Error message:', error.message);
      throw error;
    }
  }

  // Get order statistics overview
  // Note: This endpoint may not exist - returns mock data as fallback
  async getOrderStats(days = 30) {
    try {
      return await apiClient.get(`${this.ordersEndpoint}/stats/overview`, {
        params: { days }
      });
    } catch (error) {
      // Return mock stats if endpoint doesn't exist
      console.warn('Order stats endpoint not available, using mock data');
      return {
        data: {
          total_orders: 0,
          total_revenue: 0,
          pending_confirmations: 0,
          ready_to_ship: 0
        }
      };
    }
  }

  // Ship an order (using POST to /ship endpoint as per backend API)
  async shipOrder(orderId, shippingInfo) {
    return await apiClient.post(
      `${this.ordersEndpoint}/${orderId}/ship`,
      {
        tracking_number: shippingInfo.tracking_number,
        carrier: shippingInfo.carrier,
        estimated_delivery: shippingInfo.estimated_delivery,
        notes: shippingInfo.notes
      }
    );
  }

  // Bulk update order statuses (uses POST to /bulk/update-status endpoint)
  async bulkUpdateOrderStatus(updates) {
    const url = `${this.ordersEndpoint}/bulk/update-status`;
    // Convert status to lowercase for backend API
    const body = updates.map(update => ({
      order_id: update.order_id,
      status: update.status?.toLowerCase()
    }));
    console.log('[DEBUG] bulkUpdateOrderStatus URL:', url);
    console.log('[DEBUG] bulkUpdateOrderStatus body:', JSON.stringify(body));
    try {
      const response = await apiClient.post(url, body);
      console.log('[DEBUG] bulkUpdateOrderStatus SUCCESS:', JSON.stringify(response));
      return response;
    } catch (error) {
      console.error('[DEBUG] bulkUpdateOrderStatus FAILED');
      console.error('[DEBUG] Error status:', error.response?.status);
      console.error('[DEBUG] Error data:', JSON.stringify(error.response?.data));
      // Fallback: process updates sequentially if bulk endpoint fails
      console.log('[DEBUG] Falling back to sequential updates');
      const results = [];
      for (const update of updates) {
        try {
          const result = await this.updateOrderStatus(update.order_id, { status: update.status });
          results.push(result);
        } catch (seqError) {
          console.error(`Failed to update order ${update.order_id}:`, seqError);
        }
      }
      return { data: results };
    }
  }

  // Process return request
  async processReturn(orderId, returnRequest) {
    return await apiClient.post(
      `${this.ordersEndpoint}/${orderId}/return`,
      { ...returnRequest, order_id: orderId }
    );
  }

  // Process refund
  async processRefund(orderId, refundRequest) {
    const url = `${this.ordersEndpoint}/${orderId}/refund`;
    const body = { ...refundRequest, order_id: orderId };
    console.log('[DEBUG] processRefund URL:', url);
    console.log('[DEBUG] processRefund body:', JSON.stringify(body));
    try {
      const response = await apiClient.post(url, body);
      console.log('[DEBUG] processRefund SUCCESS:', JSON.stringify(response));
      return response;
    } catch (error) {
      console.error('[DEBUG] processRefund FAILED');
      console.error('[DEBUG] Error status:', error.response?.status);
      console.error('[DEBUG] Error data:', JSON.stringify(error.response?.data));
      console.error('[DEBUG] Error message:', error.message);
      throw error;
    }
  }

  // Get pending returns
  async getPendingReturns() {
    try {
      return await apiClient.get(`${this.ordersEndpoint}/returns/pending`);
    } catch (error) {
      console.warn('Pending returns endpoint not available');
      return { data: [] };
    }
  }

  // Get fulfillment analytics
  async getFulfillmentAnalytics(days = 30) {
    const url = `${this.ordersEndpoint}/analytics/fulfillment`;
    console.log('[DEBUG] getFulfillmentAnalytics URL:', url);
    try {
      const response = await apiClient.get(url, {
        params: { days }
      });
      console.log('[DEBUG] getFulfillmentAnalytics SUCCESS:', JSON.stringify(response));
      return response;
    } catch (error) {
      console.error('[DEBUG] getFulfillmentAnalytics FAILED');
      console.error('[DEBUG] Error status:', error.response?.status);
      console.error('[DEBUG] Error data:', JSON.stringify(error.response?.data));
      return { data: {} };
    }
  }

  // Helper methods for status management
  getValidNextStatuses(currentStatus) {
    const transitions = {
      [OrderStatus.PENDING]: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
      [OrderStatus.CONFIRMED]: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
      [OrderStatus.PROCESSING]: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
      [OrderStatus.SHIPPED]: [OrderStatus.DELIVERED],
      [OrderStatus.DELIVERED]: [OrderStatus.REFUNDED],
      [OrderStatus.CANCELLED]: [],
      [OrderStatus.REFUNDED]: []
    };

    return transitions[currentStatus] || [];
  }

  getStatusColor(status) {
    const colors = {
      [OrderStatus.PENDING]: '#f59e0b',     // yellow
      [OrderStatus.CONFIRMED]: '#3b82f6',   // blue
      [OrderStatus.PROCESSING]: '#8b5cf6',  // purple
      [OrderStatus.SHIPPED]: '#06b6d4',     // cyan
      [OrderStatus.DELIVERED]: '#10b981',   // green
      [OrderStatus.CANCELLED]: '#ef4444',   // red
      [OrderStatus.REFUNDED]: '#6b7280'     // gray
    };

    return colors[status] || '#6b7280';
  }

  getStatusDisplayName(status) {
    const names = {
      [OrderStatus.PENDING]: 'Pending',
      [OrderStatus.CONFIRMED]: 'Confirmed',
      [OrderStatus.PROCESSING]: 'Processing',
      [OrderStatus.SHIPPED]: 'Shipped',
      [OrderStatus.DELIVERED]: 'Delivered',
      [OrderStatus.CANCELLED]: 'Cancelled',
      [OrderStatus.REFUNDED]: 'Refunded'
    };

    return names[status] || status;
  }

  canCancelOrder(status) {
    return [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING].includes(status);
  }

  canShipOrder(status) {
    return status === OrderStatus.PROCESSING;
  }

  canRefundOrder(status) {
    return [OrderStatus.DELIVERED, OrderStatus.SHIPPED].includes(status);
  }

  formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  }

  formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  formatRelativeDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

    if (diffInHours < 24) {
      return `${diffInHours} hours ago`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `${diffInDays} days ago`;
    }
  }
}

export default new OrderFulfillmentService();