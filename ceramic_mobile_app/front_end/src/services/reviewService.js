import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

class ReviewService {
  constructor() {
    this.baseUrl = API_CONFIG.ENDPOINTS.REVIEWS;
  }

  /**
   * Create a new review for a product
   * @param {Object} reviewData - { product_id, order_id, rating, title?, comment?, image_urls? }
   */
  async createReview(reviewData) {
    return await apiClient.post(`${this.baseUrl}/`, reviewData);
  }

  /**
   * Get all reviews for a product
   * @param {number} productId
   * @param {Object} params - { skip?, limit? }
   */
  async getProductReviews(productId, params = {}) {
    return await apiClient.get(`${this.baseUrl}/product/${productId}`, { params });
  }

  /**
   * Get a specific review by ID
   * @param {number} reviewId
   */
  async getReview(reviewId) {
    return await apiClient.get(`${this.baseUrl}/${reviewId}`);
  }

  /**
   * Update a review (reviewer can edit, seller can respond)
   * @param {number} reviewId
   * @param {Object} updateData - { rating?, title?, comment?, image_urls?, seller_response? }
   */
  async updateReview(reviewId, updateData) {
    return await apiClient.put(`${this.baseUrl}/${reviewId}`, updateData);
  }

  /**
   * Delete a review (reviewer only)
   * @param {number} reviewId
   */
  async deleteReview(reviewId) {
    return await apiClient.delete(`${this.baseUrl}/${reviewId}`);
  }

  /**
   * Mark a review as helpful
   * @param {number} reviewId
   */
  async markHelpful(reviewId) {
    return await apiClient.post(`${this.baseUrl}/${reviewId}/helpful`);
  }

  /**
   * Get all reviews for a seller
   * @param {number} sellerId
   * @param {Object} params - { skip?, limit? }
   */
  async getSellerReviews(sellerId, params = {}) {
    return await apiClient.get(`${this.baseUrl}/seller/${sellerId}`, { params });
  }

  /**
   * Get all reviews written by current user
   * @param {number} userId
   * @param {Object} params - { skip?, limit? }
   */
  async getUserReviews(userId, params = {}) {
    return await apiClient.get(`${this.baseUrl}/user/${userId}`, { params });
  }

  /**
   * Get review statistics for a product
   * @param {number} productId
   */
  async getProductReviewStats(productId) {
    return await apiClient.get(`${this.baseUrl}/stats/product/${productId}`);
  }
}

export const reviewService = new ReviewService();
export default reviewService;
