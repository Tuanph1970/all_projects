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
  // Use SELLER_FULFILLMENT endpoint for seller order management
  // Routes to /api/v1/seller/fulfillment in backend (via seller-service)
  ordersEndpoint = API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT; // '/api/v1/seller/fulfillment'

  // Get paginated list of seller's orders
  async getOrders(params = {}) {
    const response = await apiClient.get(`${this.ordersEndpoint}/`, {
      params
    });

    // Backend returns array directly, transform to expected format
    const ordersArray = Array.isArray(response) ? response : (response.data || []);

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
        customer_name: order.customer_name || `Customer #${order.customer_id}`
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
  async updateOrderStatus(orderId, statusUpdate) {
    return await apiClient.patch(
      `${this.ordersEndpoint}/${orderId}/status`,
      statusUpdate
    );
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

  // Bulk update order statuses
  async bulkUpdateOrderStatus(updates) {
    // Process updates sequentially if bulk endpoint doesn't exist
    const results = [];
    for (const update of updates) {
      try {
        const result = await this.updateOrderStatus(update.order_id, { status: update.status });
        results.push(result);
      } catch (error) {
        console.error(`Failed to update order ${update.order_id}:`, error);
      }
    }
    return { data: results };
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
    return await apiClient.post(
      `${this.ordersEndpoint}/${orderId}/refund`,
      { ...refundRequest, order_id: orderId }
    );
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
    try {
      return await apiClient.get(`${this.ordersEndpoint}/analytics/fulfillment`, {
        params: { days }
      });
    } catch (error) {
      console.warn('Fulfillment analytics endpoint not available');
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