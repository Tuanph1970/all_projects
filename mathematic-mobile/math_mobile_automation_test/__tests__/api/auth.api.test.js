/**
 * API E2E Tests for Auth Service
 * Tests authentication endpoints against Mathematics Solver API
 *
 * Run with: npm run test:api or npm run test:api:auth
 */

const axios = require('axios');

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8001';
const API_TIMEOUT = 10000;

// Test data
const TEST_USER_PREFIX = 'e2e_test_';
const generateTestUser = () => ({
  email: `${TEST_USER_PREFIX}${Date.now()}@test.com`,
  password: 'Test@12345678',
  fullName: 'E2E Test User',
  phoneNumber: '+84123456789'
});

// API client
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Helper to store created users for cleanup
const createdUsers = [];

describe('Auth Service API E2E Tests', () => {
  // Health check before running tests
  beforeAll(async () => {
    try {
      await api.get('/health', { validateStatus: () => true });
      console.log(`✅ Mathematics Solver API is reachable at ${API_BASE_URL}`);
    } catch (error) {
      console.error(`❌ API not reachable at ${API_BASE_URL}`);
      throw new Error(`Cannot connect to API: ${error.message}`);
    }
  });

  describe('POST /api/auth/register - User Registration', () => {
    it('should register a new user successfully', async () => {
      const testUser = generateTestUser();

      const response = await api.post('/api/auth/register', testUser);

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('id');
      expect(response.data).toHaveProperty('email', testUser.email);
      expect(response.data).toHaveProperty('fullName', testUser.fullName);

      createdUsers.push({ ...testUser, id: response.data.id });
    });

    it('should reject registration with existing email', async () => {
      const testUser = generateTestUser();

      // Register first user
      await api.post('/api/auth/register', testUser);
      createdUsers.push(testUser);

      // Try to register with same email
      const duplicateUser = {
        ...generateTestUser(),
        email: testUser.email
      };

      try {
        await api.post('/api/auth/register', duplicateUser);
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(400);
      }
    });

    it('should reject registration with invalid email', async () => {
      const testUser = generateTestUser();
      testUser.email = 'invalid-email';

      try {
        await api.post('/api/auth/register', testUser);
        fail('Should have thrown an error');
      } catch (error) {
        expect([400, 422]).toContain(error.response.status);
      }
    });

    it('should reject registration with weak password', async () => {
      const testUser = generateTestUser();
      testUser.password = 'weak';

      try {
        await api.post('/api/auth/register', testUser);
        fail('Should have thrown an error');
      } catch (error) {
        expect([400, 422]).toContain(error.response.status);
      }
    });
  });

  describe('POST /api/auth/login - User Login', () => {
    let registeredUser;

    beforeAll(async () => {
      // Register a user for login tests
      registeredUser = generateTestUser();
      await api.post('/api/auth/register', registeredUser);
      createdUsers.push(registeredUser);
    });

    it('should login successfully with valid credentials', async () => {
      const response = await api.post('/api/auth/login', {
        email: registeredUser.email,
        password: registeredUser.password
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('accessToken');
      expect(response.data).toHaveProperty('refreshToken');
      expect(typeof response.data.accessToken).toBe('string');
      expect(response.data.accessToken.length).toBeGreaterThan(0);
    });

    it('should reject login with incorrect password', async () => {
      try {
        await api.post('/api/auth/login', {
          email: registeredUser.email,
          password: 'WrongPassword123!'
        });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(401);
      }
    });

    it('should reject login with non-existent email', async () => {
      try {
        await api.post('/api/auth/login', {
          email: 'nonexistent@test.com',
          password: 'SomePassword123!'
        });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(401);
      }
    });
  });

  describe('POST /api/auth/refresh-token - Token Refresh', () => {
    let tokens;
    let registeredUser;

    beforeAll(async () => {
      // Register and login a user
      registeredUser = generateTestUser();
      await api.post('/api/auth/register', registeredUser);
      createdUsers.push(registeredUser);

      const loginResponse = await api.post('/api/auth/login', {
        email: registeredUser.email,
        password: registeredUser.password
      });
      tokens = loginResponse.data;
    });

    it('should refresh access token with valid refresh token', async () => {
      const response = await api.post('/api/auth/refresh-token', {
        refreshToken: tokens.refreshToken
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('accessToken');
      expect(response.data).toHaveProperty('refreshToken');
    });

    it('should reject refresh with invalid refresh token', async () => {
      try {
        await api.post('/api/auth/refresh-token', {
          refreshToken: 'invalid_refresh_token'
        });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(401);
      }
    });
  });

  describe('GET /api/auth/me - Get Current User', () => {
    let tokens;
    let registeredUser;

    beforeAll(async () => {
      // Register and login a user
      registeredUser = generateTestUser();
      await api.post('/api/auth/register', registeredUser);
      createdUsers.push(registeredUser);

      const loginResponse = await api.post('/api/auth/login', {
        email: registeredUser.email,
        password: registeredUser.password
      });
      tokens = loginResponse.data;
    });

    it('should return current user info with valid token', async () => {
      const response = await api.get('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${tokens.accessToken}`
        }
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('email', registeredUser.email);
      expect(response.data).toHaveProperty('fullName', registeredUser.fullName);
    });

    it('should reject request without token', async () => {
      try {
        await api.get('/api/auth/me');
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(401);
      }
    });

    it('should reject request with invalid token', async () => {
      try {
        await api.get('/api/auth/me', {
          headers: {
            Authorization: 'Bearer invalid_token'
          }
        });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(401);
      }
    });
  });

  describe('Authentication Flow - Complete Journey', () => {
    it('should complete full auth flow: register -> login -> access protected route -> refresh -> logout', async () => {
      // Step 1: Register
      const testUser = generateTestUser();
      const registerResponse = await api.post('/api/auth/register', testUser);
      expect(registerResponse.status).toBe(200);
      createdUsers.push(testUser);
      console.log('  ✓ Registration successful');

      // Step 2: Login
      const loginResponse = await api.post('/api/auth/login', {
        email: testUser.email,
        password: testUser.password
      });
      expect(loginResponse.status).toBe(200);
      const { accessToken, refreshToken } = loginResponse.data;
      console.log('  ✓ Login successful');

      // Step 3: Access protected route
      const meResponse = await api.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      expect(meResponse.status).toBe(200);
      expect(meResponse.data.email).toBe(testUser.email);
      console.log('  ✓ Protected route access successful');

      // Step 4: Refresh token
      const refreshResponse = await api.post('/api/auth/refresh-token', {
        refreshToken
      });
      expect(refreshResponse.status).toBe(200);
      expect(refreshResponse.data).toHaveProperty('accessToken');
      console.log('  ✓ Token refresh successful');

      // Step 5: Logout
      const logoutResponse = await api.post('/api/auth/logout', null, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      expect(logoutResponse.status).toBe(200);
      console.log('  ✓ Logout successful');
    });
  });
});
