import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

class SellerService {
  // Dashboard Overview
  async getDashboardOverview(days = 30) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_DASHBOARD}/overview`, {
      params: { days }
    });
  }

  // Sales Chart Data
  async getSalesChartData(
    days = 30,
    granularity = 'day'
  ) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_DASHBOARD}/sales-chart`, {
      params: { days, granularity }
    });
  }

  // Top Products
  async getTopProducts(
    days = 30,
    metric = 'revenue',
    limit = 10
  ) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_DASHBOARD}/top-products`, {
      params: { days, metric, limit }
    });
  }

  // Category Performance
  async getCategoryPerformance(days = 30) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_DASHBOARD}/category-performance`, {
      params: { days }
    });
  }

  // Recent Orders
  async getRecentOrders(
    limit = 20,
    status
  ) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_DASHBOARD}/recent-orders`, {
      params: { limit, ...(status && { status }) }
    });
  }

  // Inventory Alerts
  async getInventoryAlerts(lowStockThreshold = 5) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_DASHBOARD}/inventory-alerts`, {
      params: { lowStockThreshold }
    });
  }

  // Product Analytics
  async getProductAnalytics(
    productId,
    days = 30
  ) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_DASHBOARD}/product-analytics/${productId}`, {
      params: { days }
    });
  }

  // Product Management
  async getProductsForManagement(params = {}) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.SELLER_PRODUCTS}/management`, { params });
  }

  // Image Upload
  async uploadImage(formData) {
    return await apiClient.upload(`${API_CONFIG.ENDPOINTS.SELLER_PRODUCTS}/upload-image`, formData);
  }

  // Bulk Operations
  async bulkUpdateStatus(
    productIds,
    isActive
  ) {
    return await apiClient.post(`${API_CONFIG.ENDPOINTS.SELLER_PRODUCTS}/bulk-operations/update-status`, {
      product_ids: productIds,
      is_active: isActive
    });
  }

  async bulkUpdatePrices(updates) {
    return await apiClient.post(`${API_CONFIG.ENDPOINTS.SELLER_PRODUCTS}/bulk-operations/update-prices`, {
      updates
    });
  }

  async bulkUpdateStock(updates) {
    return await apiClient.post(`${API_CONFIG.ENDPOINTS.PRODUCTS}/bulk/update-stock`, {
      updates
    });
  }

  async bulkUpdateFeatured(
    productIds,
    isFeatured
  ) {
    return await apiClient.post(`${API_CONFIG.ENDPOINTS.PRODUCTS}/bulk/update-featured`, {
      product_ids: productIds,
      is_featured: isFeatured
    });
  }

  // Create Product
  async createProduct(productData) {
    return await apiClient.post(`${API_CONFIG.ENDPOINTS.PRODUCTS}/`, productData);
  }

  // Delete Product
  async deleteProduct(productId) {
    return await apiClient.delete(`${API_CONFIG.ENDPOINTS.SELLER_PRODUCTS}/${productId}`);
  }
}

export default new SellerService();