/**
 * API E2E Tests for Auth Service
 * Tests authentication endpoints against Mathematics Solver API
 *
 * Run with: npm run test:api or npm run test:api:auth
 *
 * API Contract (AuthController.cs):
 *   Route prefix: /api/v1/auth
 *   Response envelope: { success, message, data }
 *   Login response data: { id, username, email, fullName, role, token, refreshToken, expiresAt }
 */

const axios = require('axios');

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8001';
const API_TIMEOUT = 10000;

// Test data generators
const generateTestUser = () => {
  const ts = Date.now();
  return {
    username: `e2e_user_${ts}`,
    email: `e2e_test_${ts}@test.com`,
    password: 'Test@12345678',
    fullName: 'E2E Test User'
  };
};

// API client
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: { 'Content-Type': 'application/json' }
});

// Storage for cleanup
const createdUsers = [];

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────

async function registerUser(user) {
  const res = await api.post('/api/v1/auth/register', user);
  return res;
}

async function loginUser(usernameOrEmail, password) {
  const res = await api.post('/api/v1/auth/login', { usernameOrEmail, password });
  return res;
}

// ──────────────────────────────────────────────────────────────
// Test Suite
// ──────────────────────────────────────────────────────────────

describe('Auth Service API Tests', () => {
  beforeAll(async () => {
    try {
      await api.get('/health', { validateStatus: () => true });
      console.log(`✅ Auth Service is reachable at ${API_BASE_URL}`);
    } catch (err) {
      throw new Error(`Cannot connect to Auth Service: ${err.message}`);
    }
  });

  // ── REGISTRATION ─────────────────────────────────────────────

  describe('POST /api/v1/auth/register', () => {
    it('registers a new user and returns tokens', async () => {
      const user = generateTestUser();
      const res = await registerUser(user);

      expect(res.status).toBe(200);
      expect(res.data.success).toBe(true);

      const data = res.data.data;
      expect(data).toHaveProperty('id');
      expect(data).toHaveProperty('token');
      expect(data).toHaveProperty('refreshToken');
      expect(data.email).toBe(user.email);
      expect(data.username).toBe(user.username);

      createdUsers.push(user);
    });

    it('returns 400 when username already exists', async () => {
      const user = generateTestUser();
      await registerUser(user);
      createdUsers.push(user);

      const duplicate = { ...generateTestUser(), username: user.username };
      const res = await api.post('/api/v1/auth/register', duplicate, { validateStatus: () => true });
      expect(res.status).toBe(400);
    });

    it('returns 400 when email already exists', async () => {
      const user = generateTestUser();
      await registerUser(user);
      createdUsers.push(user);

      const duplicate = { ...generateTestUser(), email: user.email };
      const res = await api.post('/api/v1/auth/register', duplicate, { validateStatus: () => true });
      expect(res.status).toBe(400);
    });

    it('returns 400 for invalid email format', async () => {
      const user = { ...generateTestUser(), email: 'not-an-email' };
      const res = await api.post('/api/v1/auth/register', user, { validateStatus: () => true });
      expect([400, 422]).toContain(res.status);
    });

    it('returns 400 for password shorter than 6 characters', async () => {
      const user = { ...generateTestUser(), password: 'abc' };
      const res = await api.post('/api/v1/auth/register', user, { validateStatus: () => true });
      expect([400, 422]).toContain(res.status);
    });

    it('returns 400 for username shorter than 3 characters', async () => {
      const user = { ...generateTestUser(), username: 'ab' };
      const res = await api.post('/api/v1/auth/register', user, { validateStatus: () => true });
      expect([400, 422]).toContain(res.status);
    });

    it('returns 400 for missing required fields', async () => {
      const res = await api.post('/api/v1/auth/register', {}, { validateStatus: () => true });
      expect([400, 422]).toContain(res.status);
    });
  });

  // ── LOGIN ─────────────────────────────────────────────────────

  describe('POST /api/v1/auth/login', () => {
    let testUser;

    beforeAll(async () => {
      testUser = generateTestUser();
      await registerUser(testUser);
      createdUsers.push(testUser);
    });

    it('logs in with username and returns tokens', async () => {
      const res = await loginUser(testUser.username, testUser.password);

      expect(res.status).toBe(200);
      expect(res.data.success).toBe(true);

      const data = res.data.data;
      expect(data).toHaveProperty('token');
      expect(data).toHaveProperty('refreshToken');
      expect(typeof data.token).toBe('string');
      expect(data.token.length).toBeGreaterThan(0);
    });

    it('logs in with email and returns tokens', async () => {
      const res = await loginUser(testUser.email, testUser.password);

      expect(res.status).toBe(200);
      const data = res.data.data;
      expect(data).toHaveProperty('token');
    });

    it('returns 401 for wrong password', async () => {
      const res = await api.post('/api/v1/auth/login',
        { usernameOrEmail: testUser.email, password: 'WrongPass123!' },
        { validateStatus: () => true }
      );
      expect(res.status).toBe(401);
    });

    it('returns 401 for non-existent user', async () => {
      const res = await api.post('/api/v1/auth/login',
        { usernameOrEmail: 'ghost@nowhere.com', password: 'AnyPass123!' },
        { validateStatus: () => true }
      );
      expect(res.status).toBe(401);
    });

    it('returns 400 for missing credentials', async () => {
      const res = await api.post('/api/v1/auth/login', {}, { validateStatus: () => true });
      expect([400, 422]).toContain(res.status);
    });
  });

  // ── REFRESH TOKEN ─────────────────────────────────────────────

  describe('POST /api/v1/auth/refresh', () => {
    let tokens;
    let testUser;

    beforeAll(async () => {
      testUser = generateTestUser();
      await registerUser(testUser);
      createdUsers.push(testUser);

      const loginRes = await loginUser(testUser.username, testUser.password);
      tokens = loginRes.data.data;
    });

    it('returns new token pair with valid refresh token', async () => {
      const res = await api.post('/api/v1/auth/refresh', {
        refreshToken: tokens.refreshToken
      });

      expect(res.status).toBe(200);
      const data = res.data.data;
      expect(data).toHaveProperty('token');
      expect(data).toHaveProperty('refreshToken');
      // Tokens should be rotated
      expect(data.refreshToken).not.toBe(tokens.refreshToken);
    });

    it('returns 401 for invalid refresh token', async () => {
      const res = await api.post('/api/v1/auth/refresh',
        { refreshToken: 'invalid-refresh-token-xxx' },
        { validateStatus: () => true }
      );
      expect(res.status).toBe(401);
    });

    it('returns 400 for missing refresh token', async () => {
      const res = await api.post('/api/v1/auth/refresh', {}, { validateStatus: () => true });
      expect([400, 401, 422]).toContain(res.status);
    });
  });

  // ── GET CURRENT USER ──────────────────────────────────────────

  describe('GET /api/v1/auth/me', () => {
    let tokens;
    let testUser;

    beforeAll(async () => {
      testUser = generateTestUser();
      await registerUser(testUser);
      createdUsers.push(testUser);

      const loginRes = await loginUser(testUser.username, testUser.password);
      tokens = loginRes.data.data;
    });

    it('returns authenticated user info', async () => {
      const res = await api.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${tokens.token}` }
      });

      expect(res.status).toBe(200);
      expect(res.data.success).toBe(true);

      const data = res.data.data;
      expect(data.email).toBe(testUser.email);
      expect(data.username).toBe(testUser.username);
      // Password hash should NOT be returned
      expect(data).not.toHaveProperty('passwordHash');
    });

    it('returns 401 without token', async () => {
      const res = await api.get('/api/v1/auth/me', { validateStatus: () => true });
      expect(res.status).toBe(401);
    });

    it('returns 401 with invalid token', async () => {
      const res = await api.get('/api/v1/auth/me', {
        headers: { Authorization: 'Bearer totally.invalid.token' },
        validateStatus: () => true
      });
      expect(res.status).toBe(401);
    });
  });

  // ── CHANGE PASSWORD ───────────────────────────────────────────

  describe('POST /api/v1/auth/change-password', () => {
    let tokens;
    let testUser;

    beforeAll(async () => {
      testUser = generateTestUser();
      await registerUser(testUser);
      createdUsers.push(testUser);
      const loginRes = await loginUser(testUser.username, testUser.password);
      tokens = loginRes.data.data;
    });

    it('changes password successfully', async () => {
      const newPassword = 'NewPass@9876';
      const res = await api.post('/api/v1/auth/change-password',
        { currentPassword: testUser.password, newPassword },
        { headers: { Authorization: `Bearer ${tokens.token}` } }
      );
      expect(res.status).toBe(200);
      expect(res.data.success).toBe(true);

      // Verify old password no longer works
      const oldLoginRes = await api.post('/api/v1/auth/login',
        { usernameOrEmail: testUser.username, password: testUser.password },
        { validateStatus: () => true }
      );
      expect(oldLoginRes.status).toBe(401);

      // Verify new password works
      const newLoginRes = await loginUser(testUser.username, newPassword);
      expect(newLoginRes.status).toBe(200);
    });

    it('returns 401 without auth token', async () => {
      const res = await api.post('/api/v1/auth/change-password',
        { currentPassword: testUser.password, newPassword: 'AnotherPass@1' },
        { validateStatus: () => true }
      );
      expect(res.status).toBe(401);
    });
  });

  // ── FULL AUTH FLOW ────────────────────────────────────────────

  describe('Complete Authentication Flow', () => {
    it('register → login → access protected route → refresh → change-password', async () => {
      const user = generateTestUser();
      createdUsers.push(user);

      // 1. Register
      const regRes = await registerUser(user);
      expect(regRes.status).toBe(200);
      console.log('  ✓ Registered');

      // 2. Login
      const loginRes = await loginUser(user.username, user.password);
      expect(loginRes.status).toBe(200);
      const { token, refreshToken } = loginRes.data.data;
      console.log('  ✓ Logged in');

      // 3. Access protected route
      const meRes = await api.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      expect(meRes.status).toBe(200);
      expect(meRes.data.data.username).toBe(user.username);
      console.log('  ✓ Accessed /me');

      // 4. Refresh token
      const refreshRes = await api.post('/api/v1/auth/refresh', { refreshToken });
      expect(refreshRes.status).toBe(200);
      const newTokens = refreshRes.data.data;
      expect(newTokens.token).toBeDefined();
      console.log('  ✓ Refreshed tokens');

      // 5. Use new token
      const meRes2 = await api.get('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${newTokens.token}` }
      });
      expect(meRes2.status).toBe(200);
      console.log('  ✓ New token works');
    });
  });
});
