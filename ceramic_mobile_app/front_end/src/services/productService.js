import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

class ProductService {
  baseUrl = API_CONFIG.ENDPOINTS.PRODUCTS; // '/api/v1/products'
  categoriesUrl = API_CONFIG.ENDPOINTS.CATEGORIES; // '/api/v1/products/categories'

  // Get featured products for home screen
  async getFeaturedProducts() {
    const products = await apiClient.get(`${this.baseUrl}/featured`);
    // Wrap array response in expected format for Redux slice
    return {
      products: Array.isArray(products) ? products : [],
      categories: []
    };
  }

  // Get product list with pagination and filters
  async getProducts(params = {}) {
    const queryParams = new URLSearchParams();
    
    // Add pagination parameters
    queryParams.append('page', (params.page || 1).toString());
    queryParams.append('limit', (params.limit || 20).toString());
    
    // Add filter parameters
    if (params.categoryId) queryParams.append('categoryId', params.categoryId);
    if (params.search) queryParams.append('search', params.search);
    if (params.minPrice !== undefined) queryParams.append('minPrice', params.minPrice.toString());
    if (params.maxPrice !== undefined) queryParams.append('maxPrice', params.maxPrice.toString());
    if (params.sortBy) queryParams.append('sortBy', params.sortBy);
    if (params.sortOrder) queryParams.append('sortOrder', params.sortOrder);
    if (params.isActive !== undefined) queryParams.append('isActive', params.isActive.toString());

    const url = queryParams.toString() ? 
      `${this.baseUrl}?${queryParams.toString()}` : 
      this.baseUrl;
    
    return apiClient.get(url);
  }

  // Get single product by ID
  async getProductById(id) {
    return apiClient.get(`${this.baseUrl}/${id}`);
  }

  // TODO: Backend endpoint not implemented - /slug/{slug} does not exist
  // Get product by slug (for SEO-friendly URLs)
  async getProductBySlug(slug) {
    return apiClient.get(`${this.baseUrl}/slug/${slug}`);
  }

  // Get products by category
  async getProductsByCategory(categoryId, params = {}) {
    const queryParams = new URLSearchParams();
    
    queryParams.append('categoryId', categoryId);
    queryParams.append('page', (params.page || 1).toString());
    queryParams.append('limit', (params.limit || 20).toString());
    
    if (params.search) queryParams.append('search', params.search);
    if (params.minPrice !== undefined) queryParams.append('minPrice', params.minPrice.toString());
    if (params.maxPrice !== undefined) queryParams.append('maxPrice', params.maxPrice.toString());
    if (params.sortBy) queryParams.append('sortBy', params.sortBy);
    if (params.sortOrder) queryParams.append('sortOrder', params.sortOrder);

    return apiClient.get(`${this.baseUrl}?${queryParams.toString()}`);
  }

  // Search products
  async searchProducts(searchTerm, params = {}) {
    const queryParams = new URLSearchParams();
    
    queryParams.append('search', searchTerm);
    queryParams.append('page', (params.page || 1).toString());
    queryParams.append('limit', (params.limit || 20).toString());
    
    if (params.categoryId) queryParams.append('categoryId', params.categoryId);
    if (params.minPrice !== undefined) queryParams.append('minPrice', params.minPrice.toString());
    if (params.maxPrice !== undefined) queryParams.append('maxPrice', params.maxPrice.toString());
    if (params.sortBy) queryParams.append('sortBy', params.sortBy);
    if (params.sortOrder) queryParams.append('sortOrder', params.sortOrder);

    return apiClient.get(`${this.baseUrl}?${queryParams.toString()}`);
  }

  // Get all categories
  async getCategories() {
    return apiClient.get(this.categoriesUrl);
  }

  // TODO: Backend endpoint not implemented - /categories/{id} does not exist
  // Get category by ID
  async getCategoryById(id) {
    return apiClient.get(`${this.categoriesUrl}/${id}`);
  }

  // TODO: Backend has /recommendations/{user_id} (user-based), not /{product_id}/recommendations
  // Get product recommendations based on a product ID
  async getRecommendations(productId, limit = 10) {
    return apiClient.get(`${this.baseUrl}/${productId}/recommendations?limit=${limit}`);
  }

  // Get popular products
  async getPopularProducts(limit = 10) {
    return apiClient.get(`${this.baseUrl}/analytics/popular?limit=${limit}`);
  }

  // TODO: Backend endpoint not implemented - /new does not exist
  // Get new products
  async getNewProducts(limit = 10) {
    return apiClient.get(`${this.baseUrl}/new?limit=${limit}`);
  }

  // TODO: Backend endpoint not implemented - /discounted does not exist
  // Get discounted products
  async getDiscountedProducts(limit = 10) {
    return apiClient.get(`${this.baseUrl}/discounted?limit=${limit}`);
  }

  // Get product reviews
  async getProductReviews(productId, page = 1, limit = 20) {
    return apiClient.get(`${API_CONFIG.ENDPOINTS.REVIEWS}/product/${productId}?page=${page}&limit=${limit}`);
  }

  // Get product images
  async getProductImages(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/images`);
  }

  // TODO: Backend endpoint not implemented - /{product_id}/variants does not exist
  // Get product variants
  async getProductVariants(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/variants`);
  }

  // TODO: Backend endpoint not implemented - /{product_id}/availability does not exist
  // Check product availability
  async checkAvailability(productId, variantId = null) {
    const url = variantId ?
      `${this.baseUrl}/${productId}/variants/${variantId}/availability` :
      `${this.baseUrl}/${productId}/availability`;
    return apiClient.get(url);
  }

  // TODO: Backend endpoint not implemented - /{product_id}/price-history does not exist
  // Get price history for a product
  async getPriceHistory(productId, days = 30) {
    return apiClient.get(`${this.baseUrl}/${productId}/price-history?days=${days}`);
  }

  // TODO: Backend endpoint not implemented - /{product_id}/specifications does not exist
  // Get product specifications
  async getProductSpecifications(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/specifications`);
  }

  // TODO: Backend endpoint not implemented - /compare does not exist
  // Compare products
  async compareProducts(productIds) {
    const params = productIds.map(id => `ids=${id}`).join('&');
    return apiClient.get(`${this.baseUrl}/compare?${params}`);
  }

  // Get category hierarchy (tree structure)
  async getCategoryHierarchy() {
    return apiClient.get(`${this.baseUrl}/categories/tree`);
  }

  // TODO: Backend endpoint not implemented - /brands does not exist (also missing /api/v1/products prefix)
  // Get brands
  async getBrands() {
    return apiClient.get('/brands');
  }

  // Get products by brand
  async getProductsByBrand(brandId, params = {}) {
    const queryParams = new URLSearchParams();
    
    queryParams.append('brandId', brandId);
    queryParams.append('page', (params.page || 1).toString());
    queryParams.append('limit', (params.limit || 20).toString());
    
    if (params.search) queryParams.append('search', params.search);
    if (params.categoryId) queryParams.append('categoryId', params.categoryId);
    if (params.minPrice !== undefined) queryParams.append('minPrice', params.minPrice.toString());
    if (params.maxPrice !== undefined) queryParams.append('maxPrice', params.maxPrice.toString());
    if (params.sortBy) queryParams.append('sortBy', params.sortBy);
    if (params.sortOrder) queryParams.append('sortOrder', params.sortOrder);

    return apiClient.get(`${this.baseUrl}?${queryParams.toString()}`);
  }

  // TODO: Backend endpoint not implemented - /{product_id}/tags does not exist
  // Get product tags
  async getProductTags(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/tags`);
  }

  // Get related products
  async getRelatedProducts(productId, limit = 10) {
    return apiClient.get(`${this.baseUrl}/${productId}/related?limit=${limit}`);
  }

  // TODO: Backend endpoint not implemented - /{product_id}/attributes does not exist
  // Get product attributes
  async getProductAttributes(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/attributes`);
  }
}

export const productService = new ProductService();