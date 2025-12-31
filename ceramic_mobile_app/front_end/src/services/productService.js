import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';

class ProductService {
  baseUrl = API_CONFIG.ENDPOINTS.PRODUCTS; // '/api/v1/products'
  categoriesUrl = API_CONFIG.ENDPOINTS.CATEGORIES; // '/api/v1/products/categories'

  // Get featured products for home screen
  async getFeaturedProducts() {
    return apiClient.get(`${this.baseUrl}/featured`);
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

  // Get category by ID
  async getCategoryById(id) {
    return apiClient.get(`${this.categoriesUrl}/${id}`);
  }

  // Get product recommendations based on a product ID
  async getRecommendations(productId, limit = 10) {
    return apiClient.get(`${this.baseUrl}/${productId}/recommendations?limit=${limit}`);
  }

  // Get popular products
  async getPopularProducts(limit = 10) {
    return apiClient.get(`${this.baseUrl}/popular?limit=${limit}`);
  }

  // Get new products
  async getNewProducts(limit = 10) {
    return apiClient.get(`${this.baseUrl}/new?limit=${limit}`);
  }

  // Get discounted products
  async getDiscountedProducts(limit = 10) {
    return apiClient.get(`${this.baseUrl}/discounted?limit=${limit}`);
  }

  // Get product reviews
  async getProductReviews(productId, page = 1, limit = 20) {
    return apiClient.get(`${this.baseUrl}/${productId}/reviews?page=${page}&limit=${limit}`);
  }

  // Get product images
  async getProductImages(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/images`);
  }

  // Get product variants
  async getProductVariants(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/variants`);
  }

  // Check product availability
  async checkAvailability(productId, variantId = null) {
    const url = variantId ? 
      `${this.baseUrl}/${productId}/variants/${variantId}/availability` :
      `${this.baseUrl}/${productId}/availability`;
    return apiClient.get(url);
  }

  // Get price history for a product
  async getPriceHistory(productId, days = 30) {
    return apiClient.get(`${this.baseUrl}/${productId}/price-history?days=${days}`);
  }

  // Get product specifications
  async getProductSpecifications(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/specifications`);
  }

  // Compare products
  async compareProducts(productIds) {
    const params = productIds.map(id => `ids=${id}`).join('&');
    return apiClient.get(`${this.baseUrl}/compare?${params}`);
  }

  // Get category hierarchy
  async getCategoryHierarchy() {
    return apiClient.get(`${this.categoriesUrl}/hierarchy`);
  }

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

  // Get product tags
  async getProductTags(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/tags`);
  }

  // Get related products
  async getRelatedProducts(productId, limit = 10) {
    return apiClient.get(`${this.baseUrl}/${productId}/related?limit=${limit}`);
  }

  // Get product attributes
  async getProductAttributes(productId) {
    return apiClient.get(`${this.baseUrl}/${productId}/attributes`);
  }
}

export const productService = new ProductService();