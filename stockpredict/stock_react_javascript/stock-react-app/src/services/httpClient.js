import axios from 'axios';
import { REQUEST_TIMEOUT, API_BASE_URLS, API_ENDPOINTS } from '../constants/api';

/**
 * HTTP Client Service
 * Centralized HTTP client with error handling and request/response interceptors
 *
 * Uses Traefik API Gateway as base URL for routing to microservices:
 * - Auth Service: /api/v2/auth
 * - Stock Data Service: /api/v2/stocks, /api/v2/companies, /api/v2/market
 * - Portfolio Service: /api/v2/portfolio, /api/v2/alerts
 * - Analysis Service: /api/v2/analysis, /api/v2/industries
 * - Prediction Service: /api/v2/predict, /api/v2/models, /api/v2/solutions
 * - AI Insights Service: /api/v2/ai
 * - Chatbot Service: /api/v2/chatbot
 */

class HttpClient {
  constructor() {
    // Use the API Gateway URL (Traefik routes to appropriate microservices)
    const baseURL = API_BASE_URLS.GATEWAY;

    this.client = axios.create({
      baseURL,
      timeout: REQUEST_TIMEOUT,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Single-flight refresh promise. While a refresh is in progress all other
    // 401s wait on the same promise instead of stampeding the auth-service.
    this._refreshPromise = null;

    this.setupInterceptors();
  }

  _isAuthEndpoint(url) {
    if (!url) return false;
    return (
      url.includes(API_ENDPOINTS.AUTH_REFRESH) ||
      url.includes(API_ENDPOINTS.AUTH_LOGIN) ||
      url.includes(API_ENDPOINTS.AUTH_REGISTER)
    );
  }

  _clearAuthStorage() {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('email');
    localStorage.removeItem('userId');
  }

  async _refreshAccessToken() {
    if (this._refreshPromise) {
      return this._refreshPromise;
    }
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      return Promise.reject(new Error('No refresh token'));
    }

    this._refreshPromise = axios
      .post(
        API_ENDPOINTS.AUTH_REFRESH,
        { refresh_token: refreshToken },
        { headers: { 'Content-Type': 'application/json' } }
      )
      .then((res) => {
        const data = res.data || {};
        if (data.access_token) {
          localStorage.setItem('token', data.access_token);
        }
        if (data.refresh_token) {
          localStorage.setItem('refreshToken', data.refresh_token);
        }
        return data.access_token;
      })
      .finally(() => {
        // Release the slot whether refresh succeeded or failed.
        this._refreshPromise = null;
      });

    return this._refreshPromise;
  }

  setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add authentication token if available
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(this.handleError(error));
      }
    );

    // Response interceptor — retry once after a refresh on 401
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        const status = error.response?.status;

        const refreshable =
          status === 401 &&
          originalRequest &&
          !originalRequest._retry &&
          !this._isAuthEndpoint(originalRequest.url) &&
          !!localStorage.getItem('refreshToken');

        if (refreshable) {
          originalRequest._retry = true;
          try {
            const newToken = await this._refreshAccessToken();
            if (newToken) {
              originalRequest.headers = originalRequest.headers || {};
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.client.request(originalRequest);
            }
          } catch (refreshError) {
            // Fall through to logout below.
          }
          // Refresh failed — clear auth so the app drops to login.
          this._clearAuthStorage();
        }

        return Promise.reject(this.handleError(error));
      }
    );
  }

  handleError(error) {
    const errorInfo = {
      message: 'An error occurred',
      status: null,
      data: null
    };

    if (error.response) {
      // Server responded with error status
      errorInfo.status = error.response.status;
      errorInfo.data = error.response.data;
      errorInfo.message = error.response.data?.message || `Server error: ${error.response.status}`;
    } else if (error.request) {
      // Request was made but no response received
      errorInfo.message = 'Network error: No response from server';
    } else {
      // Something else happened
      errorInfo.message = error.message || 'Unknown error occurred';
    }

    return errorInfo;
  }

  async get(url, config = {}) {
    try {
      const response = await this.client.get(url, config);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error };
    }
  }

  async post(url, data, config = {}) {
    try {
      const response = await this.client.post(url, data, config);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error };
    }
  }

  async put(url, data, config = {}) {
    try {
      const response = await this.client.put(url, data, config);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error };
    }
  }

  async delete(url, config = {}) {
    try {
      const response = await this.client.delete(url, config);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error };
    }
  }

  async patch(url, data, config = {}) {
    try {
      const response = await this.client.patch(url, data, config);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error };
    }
  }
}

export default new HttpClient();