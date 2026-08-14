/**
 * Seller Category Service
 * API service for seller-specific product category management
 */
import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

const SELLER_CATEGORIES_BASE = `${API_CONFIG.ENDPOINTS.SELLER}/categories`;

class SellerCategoryService {
  /**
   * Get paginated list of seller's categories
   * @param {Object} params - Query parameters
   * @param {number} params.page - Page number (default: 1)
   * @param {number} params.page_size - Items per page (default: 50)
   * @param {number|null} params.parent_id - Filter by parent ID
   * @param {number} params.level - Filter by level (1-4)
   * @param {boolean} params.is_active - Filter by active status
   * @param {string} params.search - Search by name
   */
  async getCategories(params = {}) {
    return await apiClient.get(SELLER_CATEGORIES_BASE, { params });
  }

  /**
   * Get full category tree structure
   * @param {boolean} includeInactive - Include inactive categories
   */
  async getCategoryTree(includeInactive = false) {
    return await apiClient.get(`${SELLER_CATEGORIES_BASE}/tree`, {
      params: { include_inactive: includeInactive }
    });
  }

  /**
   * Get root-level categories only
   * @param {boolean} includeInactive - Include inactive categories
   */
  async getRootCategories(includeInactive = false) {
    return await apiClient.get(`${SELLER_CATEGORIES_BASE}/roots`, {
      params: { include_inactive: includeInactive }
    });
  }

  /**
   * Get category statistics
   */
  async getCategoryStats() {
    return await apiClient.get(`${SELLER_CATEGORIES_BASE}/stats`);
  }

  /**
   * Get a single category by ID
   * @param {number} categoryId - Category ID
   * @param {boolean} includeChildren - Include child categories
   */
  async getCategory(categoryId, includeChildren = true) {
    return await apiClient.get(`${SELLER_CATEGORIES_BASE}/${categoryId}`, {
      params: { include_children: includeChildren }
    });
  }

  /**
   * Get breadcrumb path for a category
   * @param {number} categoryId - Category ID
   */
  async getCategoryPath(categoryId) {
    return await apiClient.get(`${SELLER_CATEGORIES_BASE}/${categoryId}/path`);
  }

  /**
   * Get direct children of a category
   * @param {number} categoryId - Parent category ID
   * @param {boolean} includeInactive - Include inactive categories
   */
  async getCategoryChildren(categoryId, includeInactive = false) {
    return await apiClient.get(`${SELLER_CATEGORIES_BASE}/${categoryId}/children`, {
      params: { include_inactive: includeInactive }
    });
  }

  /**
   * Create a new category
   * @param {Object} categoryData - Category data
   * @param {string} categoryData.name - Category name (required)
   * @param {string} categoryData.slug - URL-friendly slug
   * @param {string} categoryData.description - Category description
   * @param {number|null} categoryData.parent_id - Parent category ID
   * @param {string} categoryData.icon_url - Icon image URL
   * @param {string} categoryData.image_url - Category image URL
   * @param {boolean} categoryData.is_active - Active status
   * @param {number} categoryData.display_order - Display order
   */
  async createCategory(categoryData) {
    return await apiClient.post(SELLER_CATEGORIES_BASE, categoryData);
  }

  /**
   * Update an existing category
   * @param {number} categoryId - Category ID
   * @param {Object} categoryData - Updated category data
   */
  async updateCategory(categoryId, categoryData) {
    return await apiClient.put(`${SELLER_CATEGORIES_BASE}/${categoryId}`, categoryData);
  }

  /**
   * Delete a category
   * @param {number} categoryId - Category ID
   * @param {boolean} cascade - Delete all child categories too
   */
  async deleteCategory(categoryId, cascade = false) {
    return await apiClient.delete(`${SELLER_CATEGORIES_BASE}/${categoryId}`, {
      params: { cascade }
    });
  }

  /**
   * Move a category to a new parent
   * @param {number} categoryId - Category ID to move
   * @param {number|null} newParentId - New parent category ID (null for root)
   */
  async moveCategory(categoryId, newParentId) {
    return await apiClient.post(`${SELLER_CATEGORIES_BASE}/${categoryId}/move`, {
      new_parent_id: newParentId
    });
  }

  /**
   * Reorder multiple categories
   * @param {Array} items - Array of {id, display_order, parent_id?}
   */
  async reorderCategories(items) {
    return await apiClient.put(`${SELLER_CATEGORIES_BASE}/reorder`, { items });
  }

  /**
   * Perform bulk action on multiple categories
   * @param {Array<number>} categoryIds - Category IDs
   * @param {string} action - Action: 'activate', 'deactivate', 'delete'
   */
  async bulkAction(categoryIds, action) {
    return await apiClient.post(`${SELLER_CATEGORIES_BASE}/bulk-action`, {
      category_ids: categoryIds,
      action
    });
  }

  /**
   * Duplicate a category
   * @param {number} categoryId - Category ID to duplicate
   * @param {boolean} includeChildren - Duplicate children too
   */
  async duplicateCategory(categoryId, includeChildren = false) {
    return await apiClient.post(`${SELLER_CATEGORIES_BASE}/${categoryId}/duplicate`, null, {
      params: { include_children: includeChildren }
    });
  }
}

export default new SellerCategoryService();
