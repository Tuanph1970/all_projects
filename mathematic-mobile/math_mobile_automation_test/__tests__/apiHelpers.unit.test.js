/**
 * Unit tests for API helpers
 */

const {
  createApiClient,
  generateTestUser,
  sleep,
} = require('./apiHelpers');

describe('API Helpers - Unit Tests', () => {
  describe('createApiClient', () => {
    it('should create an axios instance with correct defaults', () => {
      const client = createApiClient('http://localhost:8001');

      expect(client.defaults.baseURL).toBe('http://localhost:8001');
      expect(client.defaults.timeout).toBe(10000);
      expect(client.defaults.headers.common['Content-Type']).toBe('application/json');
    });

    it('should include authorization header when token provided', () => {
      const client = createApiClient('http://localhost:8001', 'test-token');

      expect(client.defaults.headers.common.Authorization).toBe('Bearer test-token');
    });

    it('should use custom timeout from environment', () => {
      process.env.API_TIMEOUT = '20000';
      const client = createApiClient('http://localhost:8001');

      expect(client.defaults.timeout).toBe(20000);

      // Cleanup
      delete process.env.API_TIMEOUT;
    });
  });

  describe('generateTestUser', () => {
    it('should generate unique user data', () => {
      const user1 = generateTestUser();
      const user2 = generateTestUser();

      expect(user1.email).not.toBe(user2.email);
      expect(user1.fullName).not.toBe(user2.fullName);
    });

    it('should generate valid email format', () => {
      const user = generateTestUser();

      expect(user.email).toMatch(/^[^\s@]+@[^\s@]+\.[^\s@]+$/);
    });

    it('should include required fields', () => {
      const user = generateTestUser();

      expect(user).toHaveProperty('email');
      expect(user).toHaveProperty('password');
      expect(user).toHaveProperty('fullName');
      expect(user).toHaveProperty('phoneNumber');
    });

    it('should have secure password', () => {
      const user = generateTestUser();

      expect(user.password.length).toBeGreaterThanOrEqual(8);
      expect(user.password).toMatch(/[A-Z]/);
      expect(user.password).toMatch(/[a-z]/);
      expect(user.password).toMatch(/[0-9]/);
    });
  });

  describe('sleep', () => {
    it('should wait for specified duration', async () => {
      const start = Date.now();
      await sleep(100);
      const end = Date.now();

      expect(end - start).toBeGreaterThanOrEqual(95); // Allow 5ms tolerance
    });
  });
});
