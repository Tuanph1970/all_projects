import axios from 'axios';
import { REQUEST_TIMEOUT, API_BASE_URLS } from '../constants/api';

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

    this.setupInterceptors();
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

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
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