/**
 * Unit tests for test configuration
 * These tests validate configuration structure without requiring device
 */

const config = require('../e2e/config/testConfig');

describe('Test Configuration - Unit Tests', () => {
  describe('API Configuration', () => {
    it('should have valid API base URL', () => {
      expect(config.api.baseUrl).toBeDefined();
      expect(typeof config.api.baseUrl).toBe('string');
      expect(config.api.baseUrl).toMatch(/^https?:\/\//);
    });

    it('should have timeout configuration', () => {
      expect(config.api.timeout).toBeDefined();
      expect(typeof config.api.timeout).toBe('number');
      expect(config.api.timeout).toBeGreaterThan(0);
    });
  });

  describe('Test Users Configuration', () => {
    it('should have customer test user', () => {
      expect(config.testUsers.customer).toBeDefined();
      expect(config.testUsers.customer.username).toBe('test_customer');
      expect(config.testUsers.customer.email).toContain('@');
      expect(config.testUsers.customer.password).toBeDefined();
      expect(config.testUsers.customer.role).toBe('customer');
    });

    it('should have seller test user', () => {
      expect(config.testUsers.seller).toBeDefined();
      expect(config.testUsers.seller.username).toBe('test_seller');
      expect(config.testUsers.seller.email).toContain('@');
      expect(config.testUsers.seller.password).toBeDefined();
      expect(config.testUsers.seller.role).toBe('seller');
    });

    it('should have dual role test user', () => {
      expect(config.testUsers.dual).toBeDefined();
      expect(config.testUsers.dual.username).toBe('test_dual');
      expect(config.testUsers.dual.role).toBe('dual');
    });

    it('should have consistent password length for security', () => {
      expect(config.testUsers.customer.password.length).toBeGreaterThanOrEqual(8);
      expect(config.testUsers.seller.password.length).toBeGreaterThanOrEqual(8);
      expect(config.testUsers.dual.password.length).toBeGreaterThanOrEqual(8);
    });
  });

  describe('Timeout Configuration', () => {
    it('should have all timeout levels defined', () => {
      expect(config.timeouts.short).toBeDefined();
      expect(config.timeouts.medium).toBeDefined();
      expect(config.timeouts.long).toBeDefined();
      expect(config.timeouts.extraLong).toBeDefined();
    });

    it('should have increasing timeout values', () => {
      expect(config.timeouts.short).toBeLessThan(config.timeouts.medium);
      expect(config.timeouts.medium).toBeLessThan(config.timeouts.long);
      expect(config.timeouts.long).toBeLessThan(config.timeouts.extraLong);
    });

    it('should have reasonable timeout values (in milliseconds)', () => {
      expect(config.timeouts.short).toBeGreaterThanOrEqual(1000);
      expect(config.timeouts.extraLong).toBeLessThanOrEqual(60000);
    });
  });

  describe('Screen Identifiers', () => {
    it('should have login screen identifiers', () => {
      expect(config.screens.login).toBeDefined();
      expect(config.screens.login.usernameInput).toBe('login-username-input');
      expect(config.screens.login.passwordInput).toBe('login-password-input');
      expect(config.screens.login.loginButton).toBe('login-submit-button');
    });

    it('should have register screen identifiers', () => {
      expect(config.screens.register).toBeDefined();
      expect(config.screens.register.firstNameInput).toBe('register-firstname-input');
      expect(config.screens.register.emailInput).toBe('register-email-input');
    });

    it('should have forgot password screen identifiers', () => {
      expect(config.screens.forgotPassword).toBeDefined();
      expect(config.screens.forgotPassword.emailInput).toBe('forgot-password-email-input');
    });

    it('should have consistent testID naming convention', () => {
      const testIds = [
        config.screens.login.usernameInput,
        config.screens.login.passwordInput,
        config.screens.register.emailInput,
      ];

      testIds.forEach(id => {
        expect(id).toMatch(/^[a-z-]+$/); // lowercase with hyphens
      });
    });
  });
});
