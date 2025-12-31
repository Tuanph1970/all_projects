import axios from 'axios';
import { API_CONFIG } from '../constants/config.js';
import { secureStorage } from '../utils/secureStorage.js';
import { dispatchToStore } from '../utils/storeUtils.js';

class ApiClient {
  constructor() {
    this.isRefreshing = false;
    this.refreshSubscribers = [];
    
    // Debug logging for development
    if (__DEV__ || process.env.NODE_ENV === 'development') {
      console.log('🔗 API Base URL:', API_CONFIG.BASE_URL);
    }
    
    this.client = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  setupInterceptors() {
    // Request interceptor - Add auth token
    this.client.interceptors.request.use(
      async (config) => {
        const tokens = await secureStorage.getTokens();
        
        if (tokens?.accessToken) {
          config.headers.Authorization = `Bearer ${tokens.accessToken}`;
        }

        // Log request in development
        if (__DEV__ || process.env.NODE_ENV === 'development') {
          const fullUrl = config.baseURL ? `${config.baseURL}${config.url}` : config.url;
          console.log(`📤 ${config.method?.toUpperCase()} ${fullUrl}`);
        }

        return config;
      },
      (error) => {
        console.error('Request interceptor error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor - Handle token refresh
    this.client.interceptors.response.use(
      (response) => {
        // Log response in development
        if (__DEV__) {
          console.log(`📥 ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status}`);
        }
        return response;
      },
      async (error) => {
        const originalRequest = error.config;

        // Don't try to refresh token for auth endpoints (login, register, logout)
        if (originalRequest?.url?.includes('/login') ||
            originalRequest?.url?.includes('/register') ||
            originalRequest?.url?.includes('/logout')) {
          return Promise.reject(error);
        }

        // If error is 401 and we haven't already tried to refresh
        if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
          if (this.isRefreshing) {
            // Wait for the refresh to complete
            return new Promise((resolve) => {
              this.refreshSubscribers.push((token) => {
                if (originalRequest.headers) {
                  originalRequest.headers.Authorization = `Bearer ${token}`;
                }
                resolve(this.client(originalRequest));
              });
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const tokens = await secureStorage.getTokens();
            
            if (!tokens?.refreshToken) {
              throw new Error('No refresh token available');
            }

            // Dispatch refresh token action
            const { refreshToken } = await import('../store/slices/authSlice.js');
            const result = await dispatchToStore(refreshToken());
            
            if (refreshToken.fulfilled.match(result)) {
              const newTokens = result.payload;
              
              // Update all pending requests with new token
              this.refreshSubscribers.forEach(callback => callback(newTokens.accessToken));
              this.refreshSubscribers = [];
              
              // Retry original request with new token
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${newTokens.accessToken}`;
              }
              
              return this.client(originalRequest);
            } else {
              throw new Error('Token refresh failed');
            }
          } catch (refreshError) {
            console.error('Token refresh failed:', refreshError);
            
            // Clear subscribers and logout user
            this.refreshSubscribers = [];
            const { logoutUser } = await import('../store/slices/authSlice.js');
            dispatchToStore(logoutUser());
            
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        // Log error in development
        if (__DEV__) {
          const method = originalRequest?.method?.toUpperCase() || 'UNKNOWN';
          const url = originalRequest?.url || 'unknown-url';
          const status = error.response?.status || 'no-status';
          console.error(`❌ ${method} ${url} - ${status}`, error.response?.data);
        }

        return Promise.reject(error);
      }
    );
  }

  // HTTP Methods
  async get(url, config = {}) {
    const response = await this.client.get(url, config);
    return response.data;
  }

  async post(url, data = {}, config = {}) {
    const response = await this.client.post(url, data, config);
    return response.data;
  }

  async put(url, data = {}, config = {}) {
    const response = await this.client.put(url, data, config);
    return response.data;
  }

  async patch(url, data = {}, config = {}) {
    const response = await this.client.patch(url, data, config);
    return response.data;
  }

  async delete(url, config = {}) {
    const response = await this.client.delete(url, config);
    return response.data;
  }

  // Upload method for multipart/form-data
  async upload(url, formData, onUploadProgress) {
    const response = await this.client.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onUploadProgress(progress);
        }
      },
    });
    return response.data;
  }

  // Get the raw axios instance for advanced usage
  getInstance() {
    return this.client;
  }
}

export const apiClient = new ApiClient();