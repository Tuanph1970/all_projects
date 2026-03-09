import apiClient, { handleApiResponse, handleApiError } from './apiClient';
import * as SecureStore from 'expo-secure-store';

class AuthService {
  // Login user with username or email.
  // The backend LoginRequest DTO uses `usernameOrEmail` which accepts either field.
  async login(usernameOrEmail, password) {
    try {
      const response = await apiClient.post('/auth/login', {
        usernameOrEmail,
        password,
      });
      
      const data = handleApiResponse(response);
      
      // Store tokens securely
      if (data.token) {
        await SecureStore.setItemAsync('authToken', data.token);
      }
      if (data.refreshToken) {
        await SecureStore.setItemAsync('refreshToken', data.refreshToken);
      }
      
      return data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // Register user
  async register(username, email, password) {
    try {
      const response = await apiClient.post('/auth/register', {
        username,
        email,
        password,
        confirmPassword: password, // Add confirmPassword for backend validation
      });
      
      const data = handleApiResponse(response);
      
      // Store tokens securely
      if (data.token) {
        await SecureStore.setItemAsync('authToken', data.token);
      }
      if (data.refreshToken) {
        await SecureStore.setItemAsync('refreshToken', data.refreshToken);
      }
      
      return data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // Logout user
  async logout() {
    try {
      // Get refresh token for logout request
      const refreshToken = await SecureStore.getItemAsync('refreshToken');
      
      // Call logout endpoint to invalidate token on server
      await apiClient.post('/auth/logout', {
        refreshToken: refreshToken || '',
      });
    } catch (error) {
      // Continue with logout even if server call fails
      console.warn('Logout endpoint failed:', error.message);
    } finally {
      // Always clear local tokens
      await this.clearTokens();
    }
  }

  // Refresh access token
  async refreshToken() {
    try {
      const [authToken, refreshToken] = await Promise.all([
        SecureStore.getItemAsync('authToken'),
        SecureStore.getItemAsync('refreshToken')
      ]);
      
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }
      
      const response = await apiClient.post('/auth/refresh', {
        token: authToken || '',
        refreshToken,
      });
      
      const data = handleApiResponse(response);
      
      // Store new tokens
      if (data.token) {
        await SecureStore.setItemAsync('authToken', data.token);
      }
      if (data.refreshToken) {
        await SecureStore.setItemAsync('refreshToken', data.refreshToken);
      }
      
      return data;
    } catch (error) {
      // Clear tokens if refresh fails
      await this.clearTokens();
      handleApiError(error);
    }
  }

  // Forgot password
  async forgotPassword(email) {
    try {
      const response = await apiClient.post('/auth/forgot-password', {
        email,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Reset password
  async resetPassword(token, newPassword) {
    try {
      const response = await apiClient.post('/auth/reset-password', {
        token,
        newPassword,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Change password
  async changePassword(currentPassword, newPassword) {
    try {
      const response = await apiClient.post('/auth/change-password', {
        currentPassword,
        newPassword,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Verify email
  async verifyEmail(token) {
    try {
      const response = await apiClient.post('/auth/verify-email', {
        token,
      });
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Resend email verification
  async resendEmailVerification() {
    try {
      const response = await apiClient.post('/auth/resend-verification');
      
      return handleApiResponse(response);
    } catch (error) {
      handleApiError(error);
    }
  }

  // Get stored tokens
  async getStoredTokens() {
    try {
      const [authToken, refreshToken] = await Promise.all([
        SecureStore.getItemAsync('authToken'),
        SecureStore.getItemAsync('refreshToken'),
      ]);
      
      return {
        authToken,
        refreshToken,
      };
    } catch (error) {
      console.error('Error getting stored tokens:', error);
      return {
        authToken: null,
        refreshToken: null,
      };
    }
  }

  // Clear stored tokens
  async clearTokens() {
    try {
      await Promise.all([
        SecureStore.deleteItemAsync('authToken'),
        SecureStore.deleteItemAsync('refreshToken'),
      ]);
    } catch (error) {
      console.error('Error clearing tokens:', error);
    }
  }

  // Check if user is authenticated
  async isAuthenticated() {
    const { authToken } = await this.getStoredTokens();
    return !!authToken;
  }
}

export const authService = new AuthService();