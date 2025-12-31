const axios = require('axios');
const config = require('../config/testConfig');

class ApiHelpers {
  constructor() {
    this.baseUrl = config.api.baseUrl;
    this.timeout = config.api.timeout;
  }

  /**
   * Create test user via API (for setup)
   */
  async createTestUser(userData) {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/v1/auth/register`,
        userData,
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to create test user: ${error.message}`);
    }
  }

  /**
   * Login user via API
   */
  async loginUser(credentials) {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/v1/auth/login`,
        credentials,
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to login user: ${error.message}`);
    }
  }

  /**
   * Delete test user via API (for cleanup)
   */
  async deleteTestUser(userId, token) {
    try {
      await axios.delete(`${this.baseUrl}/api/v1/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: this.timeout,
      });
    } catch (error) {
      console.warn('Failed to delete test user:', error.message);
    }
  }

  /**
   * Request password reset via API
   */
  async requestPasswordReset(email) {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/v1/auth/forgot-password`,
        { email },
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to request password reset: ${error.message}`);
    }
  }

  /**
   * Get reset token from email (mock for testing)
   * In production, you'd retrieve this from your email testing service
   */
  async getResetTokenFromEmail(email) {
    // This is a placeholder - in real testing you'd integrate with:
    // - Mailhog, Mailtrap, or similar email testing service
    // - Or have a test endpoint that returns the token
    try {
      const response = await axios.get(
        `${this.baseUrl}/api/v1/test/reset-token/${email}`,
        { timeout: this.timeout }
      );
      return response.data.token;
    } catch (error) {
      throw new Error(`Failed to get reset token: ${error.message}`);
    }
  }

  /**
   * Verify email via API (for test setup)
   */
  async verifyEmail(token) {
    try {
      const response = await axios.post(
        `${this.baseUrl}/api/v1/auth/verify-email`,
        { token },
        { timeout: this.timeout }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to verify email: ${error.message}`);
    }
  }

  /**
   * Check if server is reachable
   */
  async checkServerHealth() {
    try {
      await axios.get(`${this.baseUrl}/health`, {
        timeout: this.timeout,
      });
      return true;
    } catch (error) {
      return false;
    }
  }
}

module.exports = new ApiHelpers();
