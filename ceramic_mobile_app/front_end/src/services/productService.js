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

    const page = params.page || 1;
    const limit = params.limit || 20;

    // Add pagination parameters - backend uses skip/limit
    queryParams.append('skip', ((page - 1) * limit).toString());
    queryParams.append('limit', limit.toString());

    // Add filter parameters
    if (params.categoryId) queryParams.append('category_id', params.categoryId);
    if (params.search) queryParams.append('search', params.search);
    if (params.minPrice !== undefined) queryParams.append('min_price', params.minPrice.toString());
    if (params.maxPrice !== undefined) queryParams.append('max_price', params.maxPrice.toString());
    if (params.sortBy) queryParams.append('sort_by', params.sortBy === 'newest' ? 'created_at' : params.sortBy);
    if (params.sortOrder) queryParams.append('sort_order', params.sortOrder);

    const url = queryParams.toString() ?
      `${this.baseUrl}/?${queryParams.toString()}` :
      `${this.baseUrl}/`;

    const products = await apiClient.get(url);

    // Wrap array response in expected format for Redux slice
    const productList = Array.isArray(products) ? products : [];
    return {
      products: productList,
      page: page,
      totalPages: Math.ceil(productList.length / limit) || 1,
      hasMore: productList.length >= limit,
      total: productList.length
    };
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

    const page = params.page || 1;
    const limit = params.limit || 20;

    queryParams.append('category_id', categoryId);
    queryParams.append('skip', ((page - 1) * limit).toString());
    queryParams.append('limit', limit.toString());

    if (params.search) queryParams.append('search', params.search);
    if (params.minPrice !== undefined) queryParams.append('min_price', params.minPrice.toString());
    if (params.maxPrice !== undefined) queryParams.append('max_price', params.maxPrice.toString());
    if (params.sortBy) queryParams.append('sort_by', params.sortBy === 'newest' ? 'created_at' : params.sortBy);
    if (params.sortOrder) queryParams.append('sort_order', params.sortOrder);

    const products = await apiClient.get(`${this.baseUrl}/?${queryParams.toString()}`);

    // Wrap array response in expected format for Redux slice
    const productList = Array.isArray(products) ? products : [];
    return {
      products: productList,
      page: page,
      totalPages: Math.ceil(productList.length / limit) || 1,
      hasMore: productList.length >= limit,
      total: productList.length
    };
  }

  // Search products
  async searchProducts(searchTerm, params = {}) {
    const queryParams = new URLSearchParams();

    const page = params.page || 1;
    const limit = params.limit || 20;

    queryParams.append('search', searchTerm);
    queryParams.append('skip', ((page - 1) * limit).toString());
    queryParams.append('limit', limit.toString());

    if (params.categoryId) queryParams.append('category_id', params.categoryId);
    if (params.minPrice !== undefined) queryParams.append('min_price', params.minPrice.toString());
    if (params.maxPrice !== undefined) queryParams.append('max_price', params.maxPrice.toString());
    if (params.sortBy) queryParams.append('sort_by', params.sortBy === 'newest' ? 'created_at' : params.sortBy);
    if (params.sortOrder) queryParams.append('sort_order', params.sortOrder);

    const products = await apiClient.get(`${this.baseUrl}/?${queryParams.toString()}`);

    // Wrap array response in expected format for Redux slice
    const productList = Array.isArray(products) ? products : [];
    return {
      products: productList,
      page: page,
      totalPages: Math.ceil(productList.length / limit) || 1,
      hasMore: productList.length >= limit,
      total: productList.length
    };
  }

  // Get all categories
  async getCategories() {
    return apiClient.get(this.categoriesUrl);
  }

  // Get main (parent) categories for navigation
  async getMainCategories() {
    const categories = await apiClient.get(this.categoriesUrl);
    // Filter to get only parent categories (no parent_id)
    const mainCategories = Array.isArray(categories)
      ? categories.filter(c => !c.parent_id)
      : [];
    return mainCategories;
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
    return apiClient.get(`${this.baseUrl}/analytics/popular?limit=${limit}`);
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
    return apiClient.get(`${API_CONFIG.ENDPOINTS.REVIEWS}/product/${productId}?page=${page}&limit=${limit}`);
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
      `${this.baseUrl}/${productId}/availability?variant_id=${variantId}` :
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

  // Get category hierarchy (tree structure)
  async getCategoryHierarchy() {
    return apiClient.get(`${this.baseUrl}/categories/tree`);
  }

  // Get brands
  async getBrands() {
    return apiClient.get(`${this.baseUrl}/brands`);
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

  // Get search suggestions (autocomplete)
  async getSearchSuggestions(query, limit = 10) {
    if (!query || query.trim().length < 2) {
      return [];
    }
    try {
      // First try the dedicated suggestions endpoint
      const response = await apiClient.get(`${this.baseUrl}/search/suggestions?q=${encodeURIComponent(query)}&limit=${limit}`);
      return Array.isArray(response) ? response : (response.suggestions || []);
    } catch (error) {
      // Fallback: use regular product search to generate suggestions
      try {
        const queryParams = new URLSearchParams();
        queryParams.append('search', query);
        queryParams.append('skip', '0');
        queryParams.append('limit', limit.toString());

        const products = await apiClient.get(`${this.baseUrl}/?${queryParams.toString()}`);
        const productList = Array.isArray(products) ? products : [];

        // Transform products into suggestion format
        return productList.map(product => ({
          id: product.id,
          name: product.name,
          type: 'product',
          price: product.price,
          category: product.category_name || product.category
        }));
      } catch (fallbackError) {
        return [];
      }
    }
  }

  // Get filter options (available filters for search)
  async getFilterOptions() {
    try {
      const response = await apiClient.get(`${this.baseUrl}/filters/options`);
      return response;
    } catch (error) {
      console.log('Filter options error:', error);
      return { categories: [], brands: [], priceRanges: [] };
    }
  }

  // Get trending products
  async getTrendingProducts(limit = 10) {
    try {
      const response = await apiClient.get(`${this.baseUrl}/trending?limit=${limit}`);
      return Array.isArray(response) ? response : (response.products || []);
    } catch (error) {
      console.log('Trending products error:', error);
      return [];
    }
  }

  // Track product view (for analytics)
  async trackProductView(productId) {
    try {
      return await apiClient.post(`${this.baseUrl}/${productId}/view`);
    } catch (error) {
      console.log('Track view error:', error);
      // Silently fail - analytics shouldn't block user experience
    }
  }

  // Get similar products
  async getSimilarProducts(productId, limit = 10) {
    try {
      const response = await apiClient.get(`${this.baseUrl}/${productId}/similar?limit=${limit}`);
      return Array.isArray(response) ? response : (response.products || []);
    } catch (error) {
      console.log('Similar products error:', error);
      return [];
    }
  }
}

export const productService = new ProductService();