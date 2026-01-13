import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

class CartService {
  baseURL = API_CONFIG.ENDPOINTS.CART; // '/api/v1/cart'

  /**
   * Get current user's cart
   */
  async getCart() {
    try {
      // Use trailing slash to avoid 307 redirect which loses Authorization header
      return await apiClient.get(`${this.baseURL}/`);
    } catch (error) {
      console.error('Error fetching cart:', error);
      throw error;
    }
  }

  /**
   * Add item to cart
   */
  async addToCart(request) {
    try {
      return await apiClient.post(`${this.baseURL}/add`, request);
    } catch (error) {
      console.error('Error adding to cart:', error);
      throw error;
    }
  }

  /**
   * Update cart item quantity
   */
  async updateCartItem(itemId, request) {
    try {
      return await apiClient.put(`${this.baseURL}/items/${itemId}`, request);
    } catch (error) {
      console.error('Error updating cart item:', error);
      throw error;
    }
  }

  /**
   * Remove item from cart
   */
  async removeFromCart(itemId) {
    try {
      return await apiClient.delete(`${this.baseURL}/items/${itemId}`);
    } catch (error) {
      console.error('Error removing from cart:', error);
      throw error;
    }
  }

  /**
   * Clear all items from cart
   */
  async clearCart() {
    try {
      return await apiClient.delete(`${this.baseURL}/clear`);
    } catch (error) {
      console.error('Error clearing cart:', error);
      throw error;
    }
  }

  /**
   * Get cart item count
   */
  async getCartCount() {
    try {
      return await apiClient.get(`${this.baseURL}/count`);
    } catch (error) {
      console.error('Error fetching cart count:', error);
      throw error;
    }
  }

  /**
   * Checkout from cart
   */
  async checkout(shippingAddress) {
    try {
      return await apiClient.post(`${API_CONFIG.ENDPOINTS.ORDERS}/checkout`, shippingAddress);
    } catch (error) {
      console.error('Error during checkout:', error);
      throw error;
    }
  }
}

export const cartService = new CartService();