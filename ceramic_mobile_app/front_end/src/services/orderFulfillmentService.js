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
  // Get paginated list of seller's orders
  async getOrders(params = {}) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders`, {
      params
    });
  }

  // Get detailed order information
  async getOrderDetails(orderId) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders/${orderId}`);
  }

  // Update order status
  async updateOrderStatus(orderId, statusUpdate) {
    return await apiClient.patch(
      `${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders/${orderId}/status`,
      statusUpdate
    );
  }

  // Get order statistics overview
  async getOrderStats(days = 30) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders/stats/overview`, {
      params: { days }
    });
  }

  // Ship an order
  async shipOrder(orderId, shippingInfo) {
    return await apiClient.post(
      `${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders/${orderId}/ship`,
      shippingInfo
    );
  }

  // Bulk update order statuses
  async bulkUpdateOrderStatus(updates) {
    return await apiClient.post(
      `${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders/bulk/update-status`,
      updates
    );
  }

  // Process return request
  async processReturn(orderId, returnRequest) {
    return await apiClient.post(
      `${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders/${orderId}/return`,
      { ...returnRequest, order_id: orderId }
    );
  }

  // Process refund
  async processRefund(orderId, refundRequest) {
    return await apiClient.post(
      `${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders/${orderId}/refund`,
      { ...refundRequest, order_id: orderId }
    );
  }

  // Get pending returns
  async getPendingReturns() {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders/returns/pending`);
  }

  // Get fulfillment analytics
  async getFulfillmentAnalytics(days = 30) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_FULFILLMENT}/orders/analytics/fulfillment`, {
      params: { days }
    });
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