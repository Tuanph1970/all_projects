import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: Constants.expoConfig?.extra?.API_BASE_URL || process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1',
  timeout: parseInt(process.env.EXPO_PUBLIC_API_TIMEOUT) || 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Token management
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  
  failedQueue = [];
};

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  async (config) => {
    try {
      const token = await SecureStore.getItemAsync('authToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Error getting auth token:', error);
    }
    
    // Log request in development
    if (__DEV__) {
      console.log(`🌐 ${config.method?.toUpperCase()} ${config.url}`, {
        headers: config.headers,
        data: config.data,
      });
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => {
    // Log response in development
    if (__DEV__) {
      console.log(`✅ ${response.config.method?.toUpperCase()} ${response.config.url}`, {
        status: response.status,
        data: response.data,
      });
    }
    
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Log error in development
    if (__DEV__) {
      console.log(`❌ ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
        status: error.response?.status,
        message: error.message,
        data: error.response?.data,
      });
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = await SecureStore.getItemAsync('refreshToken');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        const response = await axios.post(`${apiClient.defaults.baseURL}/auth/refresh`, {
          refreshToken,
        });

        const { token: newToken, refreshToken: newRefreshToken } = response.data;

        await SecureStore.setItemAsync('authToken', newToken);
        await SecureStore.setItemAsync('refreshToken', newRefreshToken);

        apiClient.defaults.headers.common.Authorization = `Bearer ${newToken}`;
        originalRequest.headers.Authorization = `Bearer ${newToken}`;

        processQueue(null, newToken);

        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        
        // Clear stored tokens
        await SecureStore.deleteItemAsync('authToken');
        await SecureStore.deleteItemAsync('refreshToken');
        
        // Redirect to login - this should be handled by Redux middleware
        // For now, we'll just reject the promise
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Helper function to handle API responses
export const handleApiResponse = (response) => {
  if (response.data) {
    return response.data;
  }
  return response;
};

// Helper function to handle API errors
export const handleApiError = (error) => {
  if (error.response) {
    // Server responded with error status
    const { status, data } = error.response;
    
    if (data?.message) {
      throw new Error(data.message);
    }
    
    switch (status) {
      case 400:
        throw new Error('Bad request. Please check your input.');
      case 401:
        throw new Error('Authentication failed. Please log in again.');
      case 403:
        throw new Error('You do not have permission to perform this action.');
      case 404:
        throw new Error('The requested resource was not found.');
      case 500:
        throw new Error('Server error. Please try again later.');
      default:
        throw new Error(`Request failed with status ${status}`);
    }
  } else if (error.request) {
    // Network error
    if (error.code === 'NETWORK_ERROR' || !error.response) {
      throw new Error('Network error. Please check your internet connection.');
    }
    throw new Error('Request failed. Please try again.');
  } else {
    // Other error
    throw new Error(error.message || 'An unexpected error occurred.');
  }
};

export default apiClient;