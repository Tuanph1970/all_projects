import { apiClient } from './apiClient.js';
import { API_CONFIG } from '../constants/config.js';
import { LoginRequest, RegisterRequest, User, AuthTokens, UserRole } from '../types/auth.js';
import { secureStorage } from '../utils/secureStorage.js';

export class AuthService {
  async login(credentials) {
    console.log('🔐 [authService] Starting login with credentials:', credentials.username);

    const response = await apiClient.post(API_CONFIG.ENDPOINTS.LOGIN, credentials);
    console.log('✅ [authService] Login API response received:', {
      hasAccessToken: !!response.access_token,
      hasRefreshToken: !!response.refresh_token,
      tokenType: response.token_type,
    });

    // Transform API response from snake_case to camelCase for secureStorage
    const tokens = {
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
      tokenType: response.token_type,
      expiresIn: response.expires_in,
      temp_password_warning: response.temp_password_warning || null,
    };
    console.log('🔄 [authService] Transformed tokens:', {
      hasAccessToken: !!tokens.accessToken,
      hasRefreshToken: !!tokens.refreshToken,
      hasTempPasswordWarning: !!tokens.temp_password_warning,
    });

    // Store tokens first so they're available for the next request
    console.log('💾 [authService] Storing tokens...');
    await secureStorage.setTokens(tokens);
    console.log('✅ [authService] Tokens stored successfully');

    // Get user data after successful login (now with auth header)
    console.log('👤 [authService] Fetching current user...');
    const user = await this.getCurrentUser();
    console.log('✅ [authService] User data received:', {
      id: user.id,
      username: user.username,
      role: user.role,
    });

    console.log('🎉 [authService] Login completed successfully');
    return { user, tokens };
  }

  async register(userData) {
    console.log('📝 [authService] Starting registration with data:', {
      email: userData.email,
      username: userData.username,
      full_name: userData.full_name,
      role: userData.role,
      // Don't log password for security
    });
    console.log('🌐 [authService] Register endpoint:', API_CONFIG.ENDPOINTS.REGISTER);
    console.log('🔗 [authService] Full URL:', `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.REGISTER}`);

    try {
      const response = await apiClient.post(API_CONFIG.ENDPOINTS.REGISTER, userData);
      console.log('✅ [authService] Registration successful:', response);
      return response;
    } catch (error) {
      console.error('❌ [authService] Registration failed:', {
        message: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        headers: error.response?.headers,
        config: {
          url: error.config?.url,
          baseURL: error.config?.baseURL,
          method: error.config?.method,
        },
      });
      throw error;
    }
  }

  async refreshToken(refreshToken) {
    return await apiClient.post(API_CONFIG.ENDPOINTS.REFRESH, { 
      refresh_token: refreshToken
    });
  }

  async getCurrentUser() {
    return await apiClient.get(API_CONFIG.ENDPOINTS.ME);
  }

  async logout() {
    try {
      await apiClient.post(API_CONFIG.ENDPOINTS.LOGOUT);
    } catch (error) {
      // Continue with local logout even if server request fails
      console.warn('Server logout failed, continuing with local logout');
    }
  }

  async switchRole(newRole) {
    return await apiClient.post(API_CONFIG.ENDPOINTS.SWITCH_ROLE, { 
      new_role: newRole
    });
  }

  async verifyEmail(token) {
    return await apiClient.post(API_CONFIG.ENDPOINTS.VERIFY_EMAIL, { token });
  }

  async resendVerificationEmail() {
    return await apiClient.post(API_CONFIG.ENDPOINTS.RESEND_VERIFICATION);
  }

  async requestPasswordReset(email) {
    return await apiClient.post(API_CONFIG.ENDPOINTS.FORGOT_PASSWORD, { email });
  }

  async resetPassword(token, newPassword) {
    return await apiClient.post(API_CONFIG.ENDPOINTS.RESET_PASSWORD, { 
      token, 
      new_password: newPassword
    });
  }

  async changePassword(currentPassword, newPassword) {
    return await apiClient.post(API_CONFIG.ENDPOINTS.CHANGE_PASSWORD, {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  async updateProfile(profileData) {
    return await apiClient.put(API_CONFIG.ENDPOINTS.USER_PROFILE, profileData);
  }

  // Address management
  async getAddresses() {
    return await apiClient.get(API_CONFIG.ENDPOINTS.USER_ADDRESSES);
  }

  async createAddress(addressData) {
    return await apiClient.post(API_CONFIG.ENDPOINTS.USER_ADDRESSES, addressData);
  }

  async updateAddress(addressId, addressData) {
    return await apiClient.put(`${API_CONFIG.ENDPOINTS.USER_ADDRESSES}/${addressId}`, addressData);
  }

  async deleteAddress(addressId) {
    return await apiClient.delete(`${API_CONFIG.ENDPOINTS.USER_ADDRESSES}/${addressId}`);
  }

  async setDefaultAddress(addressId) {
    return await apiClient.post(`${API_CONFIG.ENDPOINTS.USER_ADDRESSES}/${addressId}/set-default`);
  }
}

export const authService = new AuthService();