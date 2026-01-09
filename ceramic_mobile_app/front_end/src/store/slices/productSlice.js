import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { productService } from '../../services/productService.js';

const initialState = {
  // Product lists
  featuredProducts: [],
  products: [],
  popularProducts: [],
  newArrivals: [],
  saleProducts: [],
  favorites: [],
  
  // Categories
  categories: [],
  mainCategories: [],
  
  // Current product details
  currentProduct: null,
  relatedProducts: [],
  
  // Pagination
  currentPage: 1,
  totalPages: 0,
  hasMore: false,
  total: 0,
  
  // Filters and search
  filters: {},
  searchQuery: '',
  viewType: 'grid',
  
  // Loading states
  isLoading: false,
  isLoadingMore: false,
  isRefreshing: false,
  isFeaturedLoading: false,
  isCategoriesLoading: false,
  isProductLoading: false,
  
  // Error states
  error: null,
  featuredError: null,
  categoriesError: null,
  productError: null,
};

// Async thunks
export const fetchFeaturedProducts = createAsyncThunk(
  'products/fetchFeaturedProducts',
  async (_, { rejectWithValue }) => {
    try {
      const response = await productService.getFeaturedProducts();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch featured products');
    }
  }
);

export const fetchProducts = createAsyncThunk(
  'products/fetchProducts',
  async (params = {}, { rejectWithValue }) => {
    try {
      const response = await productService.getProducts(params);
      return { response, isLoadMore: params.page > 1 };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch products');
    }
  }
);

export const fetchProductsByCategory = createAsyncThunk(
  'products/fetchProductsByCategory',
  async ({ categoryId, params = {} }, { rejectWithValue }) => {
    try {
      const response = await productService.getProductsByCategory(categoryId, params);
      return { response, isLoadMore: params.page > 1 };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch products by category');
    }
  }
);

export const searchProducts = createAsyncThunk(
  'products/searchProducts',
  async ({ query, params = {} }, { rejectWithValue }) => {
    try {
      const response = await productService.searchProducts(query, params);
      return { response, query, isLoadMore: params.page > 1 };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to search products');
    }
  }
);

export const fetchProduct = createAsyncThunk(
  'products/fetchProduct',
  async (productId, { rejectWithValue }) => {
    try {
      const product = await productService.getProductById(productId);
      const relatedProducts = await productService.getRelatedProducts(productId);
      return { product, relatedProducts };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch product');
    }
  }
);

export const fetchPopularProducts = createAsyncThunk(
  'products/fetchPopularProducts',
  async (limit = 20, { rejectWithValue }) => {
    try {
      const products = await productService.getPopularProducts(limit);
      return products;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch popular products');
    }
  }
);

export const fetchNewArrivals = createAsyncThunk(
  'products/fetchNewArrivals',
  async (limit = 20, { rejectWithValue }) => {
    try {
      const products = await productService.getNewArrivals(limit);
      return products;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch new arrivals');
    }
  }
);

export const fetchSaleProducts = createAsyncThunk(
  'products/fetchSaleProducts',
  async (limit = 20, { rejectWithValue }) => {
    try {
      const products = await productService.getSaleProducts(limit);
      return products;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch sale products');
    }
  }
);

export const fetchCategories = createAsyncThunk(
  'products/fetchCategories',
  async (_, { rejectWithValue }) => {
    try {
      const categories = await productService.getCategories();
      const mainCategories = await productService.getMainCategories();
      return { categories, mainCategories };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch categories');
    }
  }
);

export const fetchFavorites = createAsyncThunk(
  'products/fetchFavorites',
  async (_, { rejectWithValue }) => {
    try {
      const favorites = await productService.getFavorites();
      return favorites;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch favorites');
    }
  }
);

export const toggleFavorite = createAsyncThunk(
  'products/toggleFavorite',
  async (productId, { getState, rejectWithValue }) => {
    try {
      const state = getState();
      const isFavorite = state.products.favorites.some(p => p.id === productId);
      
      if (isFavorite) {
        await productService.removeFromFavorites(productId);
      } else {
        await productService.addToFavorites(productId);
      }
      
      return { productId, isFavorite: !isFavorite };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to toggle favorite');
    }
  }
);

export const advancedSearch = createAsyncThunk(
  'products/advancedSearch',
  async (params, { rejectWithValue }) => {
    try {
      const response = await productService.advancedSearch(params);
      return { response, isLoadMore: params.page > 1 };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to perform advanced search');
    }
  }
);

const productSlice = createSlice({
  name: 'products',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
      state.featuredError = null;
      state.categoriesError = null;
      state.productError = null;
    },
    clearProducts: (state) => {
      state.products = [];
      state.currentPage = 1;
      state.hasMore = false;
      state.total = 0;
    },
    setFilters: (state, action) => {
      state.filters = action.payload;
      state.products = [];
      state.currentPage = 1;
    },
    setSearchQuery: (state, action) => {
      state.searchQuery = action.payload;
      state.products = [];
      state.currentPage = 1;
    },
    setViewType: (state, action) => {
      state.viewType = action.payload;
    },
    clearCurrentProduct: (state) => {
      state.currentProduct = null;
      state.relatedProducts = [];
    },
    updateProductInList: (state, action) => {
      const updatedProduct = action.payload;
      
      // Update in main products list
      const productIndex = state.products.findIndex(p => p.id === updatedProduct.id);
      if (productIndex !== -1) {
        state.products[productIndex] = updatedProduct;
      }
      
      // Update in featured products
      const featuredIndex = state.featuredProducts.findIndex(p => p.id === updatedProduct.id);
      if (featuredIndex !== -1) {
        state.featuredProducts[featuredIndex] = updatedProduct;
      }
      
      // Update current product if it matches
      if (state.currentProduct?.id === updatedProduct.id) {
        state.currentProduct = updatedProduct;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch featured products
      .addCase(fetchFeaturedProducts.pending, (state) => {
        state.isFeaturedLoading = true;
        state.featuredError = null;
      })
      .addCase(fetchFeaturedProducts.fulfilled, (state, action) => {
        state.isFeaturedLoading = false;
        state.featuredProducts = action.payload.products;
        state.mainCategories = action.payload.categories;
      })
      .addCase(fetchFeaturedProducts.rejected, (state, action) => {
        state.isFeaturedLoading = false;
        state.featuredError = action.payload;
      })
      
      // Fetch products
      .addCase(fetchProducts.pending, (state, action) => {
        if (action.meta.arg.page && action.meta.arg.page > 1) {
          state.isLoadingMore = true;
        } else {
          state.isLoading = true;
        }
        state.error = null;
      })
      .addCase(fetchProducts.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isLoadingMore = false;
        state.isRefreshing = false;
        
        const { response, isLoadMore } = action.payload;
        
        if (isLoadMore) {
          state.products = [...state.products, ...response.products];
        } else {
          state.products = response.products;
        }
        
        state.currentPage = response.page;
        state.totalPages = response.totalPages;
        state.hasMore = response.hasMore;
        state.total = response.total;
      })
      .addCase(fetchProducts.rejected, (state, action) => {
        state.isLoading = false;
        state.isLoadingMore = false;
        state.isRefreshing = false;
        state.error = action.payload;
      })
      
      // Fetch products by category
      .addCase(fetchProductsByCategory.pending, (state, action) => {
        if (action.meta.arg.params?.page && action.meta.arg.params.page > 1) {
          state.isLoadingMore = true;
        } else {
          state.isLoading = true;
        }
        state.error = null;
      })
      .addCase(fetchProductsByCategory.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isLoadingMore = false;
        
        const { response, isLoadMore } = action.payload;
        
        if (isLoadMore) {
          state.products = [...state.products, ...response.products];
        } else {
          state.products = response.products;
        }
        
        state.currentPage = response.page;
        state.totalPages = response.totalPages;
        state.hasMore = response.hasMore;
        state.total = response.total;
      })
      .addCase(fetchProductsByCategory.rejected, (state, action) => {
        state.isLoading = false;
        state.isLoadingMore = false;
        state.error = action.payload;
      })
      
      // Search products
      .addCase(searchProducts.pending, (state, action) => {
        if (action.meta.arg.params?.page && action.meta.arg.params.page > 1) {
          state.isLoadingMore = true;
        } else {
          state.isLoading = true;
        }
        state.error = null;
      })
      .addCase(searchProducts.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isLoadingMore = false;
        
        const { response, query, isLoadMore } = action.payload;
        
        state.searchQuery = query;
        
        if (isLoadMore) {
          state.products = [...state.products, ...response.products];
        } else {
          state.products = response.products;
        }
        
        state.currentPage = response.page;
        state.totalPages = response.totalPages;
        state.hasMore = response.hasMore;
        state.total = response.total;
      })
      .addCase(searchProducts.rejected, (state, action) => {
        state.isLoading = false;
        state.isLoadingMore = false;
        state.error = action.payload;
      })
      
      // Fetch single product
      .addCase(fetchProduct.pending, (state) => {
        state.isProductLoading = true;
        state.productError = null;
      })
      .addCase(fetchProduct.fulfilled, (state, action) => {
        state.isProductLoading = false;
        state.currentProduct = action.payload.product;
        state.relatedProducts = action.payload.relatedProducts;
      })
      .addCase(fetchProduct.rejected, (state, action) => {
        state.isProductLoading = false;
        state.productError = action.payload;
      })
      
      // Fetch popular products
      .addCase(fetchPopularProducts.fulfilled, (state, action) => {
        state.popularProducts = action.payload;
      })
      
      // Fetch new arrivals
      .addCase(fetchNewArrivals.fulfilled, (state, action) => {
        state.newArrivals = action.payload;
      })
      
      // Fetch sale products
      .addCase(fetchSaleProducts.fulfilled, (state, action) => {
        state.saleProducts = action.payload;
      })
      
      // Fetch categories
      .addCase(fetchCategories.pending, (state) => {
        state.isCategoriesLoading = true;
        state.categoriesError = null;
      })
      .addCase(fetchCategories.fulfilled, (state, action) => {
        state.isCategoriesLoading = false;
        state.categories = action.payload.categories;
        state.mainCategories = action.payload.mainCategories;
      })
      .addCase(fetchCategories.rejected, (state, action) => {
        state.isCategoriesLoading = false;
        state.categoriesError = action.payload;
      })
      
      // Fetch favorites
      .addCase(fetchFavorites.fulfilled, (state, action) => {
        state.favorites = action.payload;
      })
      
      // Toggle favorite
      .addCase(toggleFavorite.fulfilled, (state, action) => {
        const { productId, isFavorite } = action.payload;
        
        if (isFavorite) {
          // Add to favorites if not already there
          const product = state.products.find(p => p.id === productId) || 
                         state.featuredProducts.find(p => p.id === productId) ||
                         state.currentProduct;
          if (product && !state.favorites.some(p => p.id === productId)) {
            state.favorites.push(product);
          }
        } else {
          // Remove from favorites
          state.favorites = state.favorites.filter(p => p.id !== productId);
        }
      })
      
      // Advanced search
      .addCase(advancedSearch.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(advancedSearch.fulfilled, (state, action) => {
        state.isLoading = false;
        const { response, isLoadMore } = action.payload;
        
        if (isLoadMore) {
          state.products = [...state.products, ...response.products];
        } else {
          state.products = response.products;
        }
        
        state.total = response.total;
        state.currentPage = Math.floor((response.page * response.limit) / 20) + 1; // Convert to UI pagination
        state.totalPages = response.pages;
        state.hasMore = response.has_more;
      })
      .addCase(advancedSearch.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });
  },
});

export const {
  clearError,
  clearProducts,
  setFilters,
  setSearchQuery,
  setViewType,
  clearCurrentProduct,
  updateProductInList,
} = productSlice.actions;

export default productSlice.reducer;