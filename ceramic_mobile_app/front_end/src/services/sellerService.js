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

  // Get single product for editing
  async getProduct(productId) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.PRODUCTS}/${productId}`);
  }

  // Update product
  async updateProduct(productId, productData) {
    // Use product service endpoint which has the PUT handler
    return await apiClient.put(`${API_CONFIG.ENDPOINTS.PRODUCTS}/${productId}`, productData);
  }

  // Image Upload
  async uploadImage(formData) {
    return await apiClient.upload(`${API_CONFIG.ENDPOINTS.SELLER}/upload-image`, formData);
  }

  // Video Upload
  async uploadVideo(formData, onProgress) {
    return await apiClient.upload(
      `${API_CONFIG.ENDPOINTS.SELLER}/upload-video`,
      formData,
      onProgress
    );
  }

  // Add video to product
  async addVideoToProduct(productId, videoData) {
    // videoData: { video_url, thumbnail_url?, duration_seconds?, file_size_mb?, resolution?, alt_text? }
    const formData = new FormData();
    formData.append('video_url', videoData.video_url);
    if (videoData.thumbnail_url) formData.append('thumbnail_url', videoData.thumbnail_url);
    if (videoData.duration_seconds) formData.append('duration_seconds', videoData.duration_seconds.toString());
    if (videoData.file_size_mb) formData.append('file_size_mb', videoData.file_size_mb.toString());
    if (videoData.resolution) formData.append('resolution', videoData.resolution);
    if (videoData.alt_text) formData.append('alt_text', videoData.alt_text);

    return await apiClient.post(`${API_CONFIG.ENDPOINTS.PRODUCTS}/${productId}/videos`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  // Get product videos
  async getProductVideos(productId) {
    return await apiClient.get(`${API_CONFIG.ENDPOINTS.PRODUCTS}/${productId}/videos`);
  }

  // Delete product video
  async deleteProductVideo(productId, videoId) {
    return await apiClient.delete(`${API_CONFIG.ENDPOINTS.PRODUCTS}/${productId}/videos/${videoId}`);
  }

  // Add image to product
  async addProductImage(productId, imageData) {
    // imageData: { image_url, alt_text?, is_primary?, order_index? }
    const params = new URLSearchParams();
    params.append('image_url', imageData.image_url);
    if (imageData.alt_text) params.append('alt_text', imageData.alt_text);
    if (imageData.is_primary !== undefined) params.append('is_primary', imageData.is_primary);
    if (imageData.order_index !== undefined) params.append('order_index', imageData.order_index);

    return await apiClient.post(`${API_CONFIG.ENDPOINTS.PRODUCTS}/${productId}/images?${params.toString()}`);
  }

  // Bulk Operations
  async bulkUpdateStatus(productIds, isActive) {
    return await apiClient.post(`${API_CONFIG.ENDPOINTS.SELLER}/bulk-operations/update-status`, {
      product_ids: productIds,
      is_active: isActive
    });
  }

  async bulkUpdatePrices(updates) {
    const url = `${API_CONFIG.ENDPOINTS.SELLER}/bulk-operations/update-prices`;
    console.log('[DEBUG] bulkUpdatePrices URL:', url);
    console.log('[DEBUG] bulkUpdatePrices payload:', JSON.stringify(updates));
    try {
      // API expects direct array, not wrapped in {updates: [...]}
      const response = await apiClient.post(url, updates);
      console.log('[DEBUG] bulkUpdatePrices SUCCESS:', JSON.stringify(response));
      return response;
    } catch (error) {
      console.error('[DEBUG] bulkUpdatePrices FAILED');
      console.error('[DEBUG] Error status:', error.response?.status);
      console.error('[DEBUG] Error data:', JSON.stringify(error.response?.data));
      throw error;
    }
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
    // Use the products service bulk endpoint
    // is_featured is a query param, product_ids is a direct array in body
    const url = `${API_CONFIG.ENDPOINTS.PRODUCTS}/bulk/update-featured?is_featured=${isFeatured}`;
    console.log('[DEBUG] bulkUpdateFeatured URL:', url);
    console.log('[DEBUG] bulkUpdateFeatured payload:', JSON.stringify(productIds));
    try {
      const response = await apiClient.post(url, productIds);
      console.log('[DEBUG] bulkUpdateFeatured SUCCESS:', JSON.stringify(response));
      return response;
    } catch (error) {
      console.error('[DEBUG] bulkUpdateFeatured FAILED');
      console.error('[DEBUG] Error status:', error.response?.status);
      console.error('[DEBUG] Error data:', JSON.stringify(error.response?.data));
      throw error;
    }
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