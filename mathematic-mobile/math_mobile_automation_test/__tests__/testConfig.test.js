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
    it('should have test user configuration', () => {
      expect(config.testUsers.default).toBeDefined();
      expect(config.testUsers.default.email).toContain('@');
      expect(config.testUsers.default.password).toBeDefined();
    });

    it('should have secure password configuration', () => {
      expect(config.testUsers.default.password.length).toBeGreaterThanOrEqual(8);
    });
  });

  describe('Timeout Configuration', () => {
    it('should have all timeout levels defined', () => {
      expect(config.timeouts.short).toBeDefined();
      expect(config.timeouts.medium).toBeDefined();
      expect(config.timeouts.long).toBeDefined();
    });

    it('should have increasing timeout values', () => {
      expect(config.timeouts.short).toBeLessThan(config.timeouts.medium);
      expect(config.timeouts.medium).toBeLessThan(config.timeouts.long);
    });
  });

  describe('Screen Identifiers', () => {
    it('should have login screen identifiers', () => {
      expect(config.screens.login).toBeDefined();
      expect(config.screens.login.emailInput).toBe('login-email-input');
      expect(config.screens.login.passwordInput).toBe('login-password-input');
      expect(config.screens.login.loginButton).toBe('login-button');
    });

    it('should have home screen identifier', () => {
      expect(config.screens.home).toBeDefined();
      expect(config.screens.home.screen).toBe('home-screen');
    });

    it('should have consistent testID naming convention', () => {
      const testIds = [
        config.screens.login.emailInput,
        config.screens.login.passwordInput,
        config.screens.home.screen,
      ];

      testIds.forEach(id => {
        expect(id).toMatch(/^[a-z-]+$/); // lowercase with hyphens
      });
    });
  });
});
