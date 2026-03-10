/**
 * API E2E Tests for Problem Service
 * Tests problem management endpoints against Mathematics Solver API
 *
 * Run with: npm run test:api
 *
 * API Contract (ProblemController.cs):
 *   Route prefix: /api/v1/problems
 *   Auth: Bearer token required for all endpoints
 *   Response envelope: { success, message?, data }
 *   Create: 201 Created
 *   List:   200 { data: { items, total, page, pageSize } }
 */

const axios = require('axios');

// Configuration
const AUTH_BASE_URL = process.env.AUTH_BASE_URL || process.env.API_BASE_URL || 'http://localhost:8001';
const PROBLEM_BASE_URL = process.env.PROBLEM_BASE_URL || 'http://localhost:8002';
const API_TIMEOUT = 15000;

const authApi = axios.create({
  baseURL: AUTH_BASE_URL,
  timeout: API_TIMEOUT,
  headers: { 'Content-Type': 'application/json' }
});

const problemApi = axios.create({
  baseURL: PROBLEM_BASE_URL,
  timeout: API_TIMEOUT,
  headers: { 'Content-Type': 'application/json' }
});

// ──────────────────────────────────────────────────────────────
// Setup: Auth helpers
// ──────────────────────────────────────────────────────────────

const generateTestUser = () => {
  const ts = Date.now();
  return {
    username: `prob_tester_${ts}`,
    email: `prob_tester_${ts}@test.com`,
    password: 'Test@12345678',
    fullName: 'Problem Tester'
  };
};

async function getAuthToken() {
  const user = generateTestUser();
  await authApi.post('/api/v1/auth/register', user);
  const loginRes = await authApi.post('/api/v1/auth/login', {
    usernameOrEmail: user.username,
    password: user.password
  });
  return loginRes.data.data.token;
}

const authHeader = (token) => ({ Authorization: `Bearer ${token}` });

// ──────────────────────────────────────────────────────────────
// Test Suite
// ──────────────────────────────────────────────────────────────

describe('Problem Service API Tests', () => {
  let token;
  const createdProblemIds = [];

  beforeAll(async () => {
    try {
      token = await getAuthToken();
      console.log('✅ Authenticated for Problem Service tests');
    } catch (err) {
      console.error('❌ Could not obtain auth token:', err.message);
      throw err;
    }
  });

  afterAll(async () => {
    for (const id of createdProblemIds) {
      try {
        await problemApi.delete(`/api/v1/problems/${id}`, {
          headers: authHeader(token),
          validateStatus: () => true
        });
      } catch (_) { /* ignore cleanup errors */ }
    }
  });

  // ── CREATE PROBLEM ────────────────────────────────────────────

  describe('POST /api/v1/problems', () => {
    it('creates a problem and returns 201 with problem data', async () => {
      const payload = {
        title: `Algebra Test ${Date.now()}`,
        description: 'Solve for x: 2x + 3 = 7',
        category: 'Algebra',
        difficulty: 'Easy'
      };

      const res = await problemApi.post('/api/v1/problems', payload, {
        headers: authHeader(token),
        validateStatus: () => true
      });

      expect(res.status).toBe(201);
      expect(res.data.success).toBe(true);

      const data = res.data.data;
      expect(data).toHaveProperty('id');
      expect(data.title).toBe(payload.title);
      expect(data.category).toBe(payload.category);
      expect(data.status).toBe('Pending');

      createdProblemIds.push(data.id);
    });

    it('creates a problem with only required fields (title)', async () => {
      const payload = { title: `Minimal Problem ${Date.now()}` };

      const res = await problemApi.post('/api/v1/problems', payload, {
        headers: authHeader(token),
        validateStatus: () => true
      });

      expect(res.status).toBe(201);
      const data = res.data.data;
      expect(data.category).toBe('General'); // default
      expect(data.difficulty).toBe('Medium'); // default
      createdProblemIds.push(data.id);
    });

    it('returns 401 without authentication', async () => {
      const res = await problemApi.post('/api/v1/problems',
        { title: 'Unauthorized Problem' },
        { validateStatus: () => true }
      );
      expect(res.status).toBe(401);
    });

    it('returns 400 when title is missing', async () => {
      const res = await problemApi.post('/api/v1/problems',
        { description: 'No title provided' },
        { headers: authHeader(token), validateStatus: () => true }
      );
      expect([400, 422]).toContain(res.status);
    });

    it('returns 400 when title is empty', async () => {
      const res = await problemApi.post('/api/v1/problems',
        { title: '' },
        { headers: authHeader(token), validateStatus: () => true }
      );
      expect([400, 422]).toContain(res.status);
    });
  });

  // ── GET USER PROBLEMS ─────────────────────────────────────────

  describe('GET /api/v1/problems', () => {
    beforeAll(async () => {
      // Ensure there are at least 2 problems for this user
      for (let i = 0; i < 2; i++) {
        const res = await problemApi.post('/api/v1/problems',
          { title: `List Test Problem ${i} ${Date.now()}`, category: 'Geometry' },
          { headers: authHeader(token) }
        );
        createdProblemIds.push(res.data.data.id);
      }
    });

    it('returns paginated list of user problems', async () => {
      const res = await problemApi.get('/api/v1/problems', {
        headers: authHeader(token)
      });

      expect(res.status).toBe(200);
      expect(res.data.success).toBe(true);

      const data = res.data.data;
      expect(data).toHaveProperty('items');
      expect(data).toHaveProperty('total');
      expect(data).toHaveProperty('page');
      expect(data).toHaveProperty('pageSize');
      expect(Array.isArray(data.items)).toBe(true);
    });

    it('supports page and pageSize query params', async () => {
      const res = await problemApi.get('/api/v1/problems?page=1&pageSize=1', {
        headers: authHeader(token)
      });

      expect(res.status).toBe(200);
      const data = res.data.data;
      expect(data.page).toBe(1);
      expect(data.pageSize).toBe(1);
      expect(data.items.length).toBeLessThanOrEqual(1);
    });

    it('supports status filter', async () => {
      const res = await problemApi.get('/api/v1/problems?status=Pending', {
        headers: authHeader(token)
      });

      expect(res.status).toBe(200);
      const data = res.data.data;
      // All returned items should have Pending status
      data.items.forEach(item => {
        expect(item.status).toBe('Pending');
      });
    });

    it('returns 401 without authentication', async () => {
      const res = await problemApi.get('/api/v1/problems', { validateStatus: () => true });
      expect(res.status).toBe(401);
    });
  });

  // ── GET PROBLEM BY ID ─────────────────────────────────────────

  describe('GET /api/v1/problems/:id', () => {
    let problemId;

    beforeAll(async () => {
      const res = await problemApi.post('/api/v1/problems',
        { title: `Detail Test ${Date.now()}`, description: 'Test problem for GET', category: 'Calculus' },
        { headers: authHeader(token) }
      );
      problemId = res.data.data.id;
      createdProblemIds.push(problemId);
    });

    it('returns the specific problem by ID', async () => {
      const res = await problemApi.get(`/api/v1/problems/${problemId}`, {
        headers: authHeader(token)
      });

      expect(res.status).toBe(200);
      expect(res.data.success).toBe(true);

      const data = res.data.data;
      expect(data.id).toBe(problemId);
      expect(data).toHaveProperty('title');
      expect(data).toHaveProperty('status');
    });

    it('returns 404 for non-existent problem ID', async () => {
      const fakeId = '00000000-0000-0000-0000-000000000000';
      const res = await problemApi.get(`/api/v1/problems/${fakeId}`, {
        headers: authHeader(token),
        validateStatus: () => true
      });
      expect([404, 403]).toContain(res.status);
    });

    it('returns 401 without authentication', async () => {
      const res = await problemApi.get(`/api/v1/problems/${problemId}`, {
        validateStatus: () => true
      });
      expect(res.status).toBe(401);
    });
  });

  // ── UPDATE PROBLEM ────────────────────────────────────────────

  describe('PUT /api/v1/problems/:id', () => {
    let problemId;

    beforeAll(async () => {
      const res = await problemApi.post('/api/v1/problems',
        { title: `Update Me ${Date.now()}`, category: 'Statistics' },
        { headers: authHeader(token) }
      );
      problemId = res.data.data.id;
      createdProblemIds.push(problemId);
    });

    it('updates title and category successfully', async () => {
      const updates = { title: 'Updated Title', category: 'Trigonometry' };
      const res = await problemApi.put(`/api/v1/problems/${problemId}`, updates, {
        headers: authHeader(token)
      });

      expect(res.status).toBe(200);
      expect(res.data.success).toBe(true);
    });

    it('returns 404 for non-existent problem', async () => {
      const fakeId = '00000000-0000-0000-0000-000000000001';
      const res = await problemApi.put(`/api/v1/problems/${fakeId}`,
        { title: 'Ghost Problem' },
        { headers: authHeader(token), validateStatus: () => true }
      );
      expect([404, 403]).toContain(res.status);
    });

    it('returns 401 without authentication', async () => {
      const res = await problemApi.put(`/api/v1/problems/${problemId}`,
        { title: 'Unauthenticated Update' },
        { validateStatus: () => true }
      );
      expect(res.status).toBe(401);
    });
  });

  // ── DELETE PROBLEM ────────────────────────────────────────────

  describe('DELETE /api/v1/problems/:id', () => {
    it('deletes a problem and returns 200', async () => {
      // Create a problem specifically for deletion
      const createRes = await problemApi.post('/api/v1/problems',
        { title: `Delete Me ${Date.now()}` },
        { headers: authHeader(token) }
      );
      const problemId = createRes.data.data.id;

      const deleteRes = await problemApi.delete(`/api/v1/problems/${problemId}`, {
        headers: authHeader(token)
      });
      expect(deleteRes.status).toBe(200);
      expect(deleteRes.data.success).toBe(true);

      // Verify it's gone
      const getRes = await problemApi.get(`/api/v1/problems/${problemId}`, {
        headers: authHeader(token),
        validateStatus: () => true
      });
      expect([404, 403]).toContain(getRes.status);
    });

    it('returns 404 for non-existent problem', async () => {
      const fakeId = '00000000-0000-0000-0000-000000000002';
      const res = await problemApi.delete(`/api/v1/problems/${fakeId}`, {
        headers: authHeader(token),
        validateStatus: () => true
      });
      expect([404, 403]).toContain(res.status);
    });

    it('returns 401 without authentication', async () => {
      const fakeId = '00000000-0000-0000-0000-000000000003';
      const res = await problemApi.delete(`/api/v1/problems/${fakeId}`, {
        validateStatus: () => true
      });
      expect(res.status).toBe(401);
    });
  });

  // ── CROSS-USER ISOLATION ──────────────────────────────────────

  describe('Cross-user access isolation', () => {
    it('cannot access another user\'s problem', async () => {
      // Create a problem with user A
      const createRes = await problemApi.post('/api/v1/problems',
        { title: `User A Problem ${Date.now()}` },
        { headers: authHeader(token) }
      );
      const problemId = createRes.data.data.id;
      createdProblemIds.push(problemId);

      // Get token for user B
      const tokenB = await getAuthToken();

      // User B tries to access user A's problem
      const res = await problemApi.get(`/api/v1/problems/${problemId}`, {
        headers: authHeader(tokenB),
        validateStatus: () => true
      });
      expect([403, 404]).toContain(res.status);
    });
  });

  // ── COMPLETE PROBLEM LIFECYCLE ────────────────────────────────

  describe('Complete Problem Lifecycle', () => {
    it('create → read → update → delete', async () => {
      // Create
      const createRes = await problemApi.post('/api/v1/problems',
        { title: `Lifecycle Test ${Date.now()}`, category: 'Algebra', difficulty: 'Hard' },
        { headers: authHeader(token) }
      );
      expect(createRes.status).toBe(201);
      const { id } = createRes.data.data;
      console.log(`  ✓ Created problem ${id}`);

      // Read
      const getRes = await problemApi.get(`/api/v1/problems/${id}`, {
        headers: authHeader(token)
      });
      expect(getRes.status).toBe(200);
      expect(getRes.data.data.status).toBe('Pending');
      console.log('  ✓ Read problem');

      // Update
      const updateRes = await problemApi.put(`/api/v1/problems/${id}`,
        { title: 'Updated Lifecycle Title' },
        { headers: authHeader(token) }
      );
      expect(updateRes.status).toBe(200);
      console.log('  ✓ Updated problem');

      // Delete
      const deleteRes = await problemApi.delete(`/api/v1/problems/${id}`, {
        headers: authHeader(token)
      });
      expect(deleteRes.status).toBe(200);
      console.log('  ✓ Deleted problem');
    });
  });
});
