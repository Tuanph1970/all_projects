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

class CustomerOrderService {
  constructor() {
    this.baseURL = API_CONFIG.ENDPOINTS.ORDERS;
  }

  // Get customer's order history
  async getOrders(params = {}) {
    try {
      // Use trailing slash to avoid 307 redirect which loses Authorization header
      const response = await apiClient.get(`${this.baseURL}/`, { params });
      return response;
    } catch (error) {
      console.error('Error fetching orders:', error);
      throw error;
    }
  }

  // Get specific order details
  async getOrderDetails(orderId) {
    try {
      const response = await apiClient.get(`${this.baseURL}/${orderId}`);
      return response;
    } catch (error) {
      console.error('Error fetching order details:', error);
      throw error;
    }
  }

  // Cancel an order (if allowed)
  async cancelOrder(orderId) {
    try {
      const response = await apiClient.post(`${this.baseURL}/${orderId}/cancel`);
      return response;
    } catch (error) {
      console.error('Error cancelling order:', error);
      throw error;
    }
  }

  // Helper methods
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
    return [OrderStatus.PENDING, OrderStatus.CONFIRMED].includes(status);
  }

  formatCurrency(amount) {
    if (amount === undefined || amount === null) return '$0.00';
    return `$${parseFloat(amount).toFixed(2)}`;
  }

  formatDate(dateString) {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}

export const customerOrderService = new CustomerOrderService();
export default customerOrderService;
