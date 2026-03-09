/**
 * API E2E Tests for Problem Service
 * Tests problem management endpoints
 *
 * Run with: npm run test:api:problem
 */

const axios = require('axios');

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8001';
const API_TIMEOUT = 15000;

// API client
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Test credentials (should be created in test setup)
const TEST_CREDENTIALS = {
  email: 'test_problem_user@test.com',
  password: 'Test@12345678'
};

let authToken = null;
let createdProblems = [];

describe('Problem Service API E2E Tests', () => {
  // Login before running tests
  beforeAll(async () => {
    try {
      const loginResponse = await api.post('/api/auth/login', TEST_CREDENTIALS);
      authToken = loginResponse.data.accessToken;
      console.log('✅ Authenticated for Problem Service tests');
    } catch (error) {
      console.warn('⚠️  Could not authenticate. Some tests may fail.');
    }
  });

  describe('POST /api/problems - Create Problem', () => {
    it('should create a new problem with image', async () => {
      const problemData = {
        title: 'Test Problem ' + Date.now(),
        description: 'This is a test mathematical problem',
        category: 'algebra',
        imageUrl: 'https://example.com/test-problem.jpg'
      };

      const response = await api.post('/api/problems', problemData, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('id');
      expect(response.data.title).toBe(problemData.title);

      createdProblems.push(response.data.id);
    });

    it('should reject problem creation without authentication', async () => {
      const problemData = {
        title: 'Unauthorized Problem',
        description: 'This should fail'
      };

      try {
        await api.post('/api/problems', problemData);
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(401);
      }
    });
  });

  describe('GET /api/problems - List Problems', () => {
    it('should return list of problems', async () => {
      const response = await api.get('/api/problems', {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(response.status).toBe(200);
      expect(Array.isArray(response.data)).toBe(true);
    });

    it('should support pagination', async () => {
      const response = await api.get('/api/problems?page=1&limit=10', {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/problems/:id - Get Problem', () => {
    it('should return a specific problem', async () => {
      // First create a problem
      const problemData = {
        title: 'Test Problem for GET ' + Date.now(),
        description: 'Problem to retrieve',
        category: 'geometry'
      };

      const createResponse = await api.post('/api/problems', problemData, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      const problemId = createResponse.data.id;
      createdProblems.push(problemId);

      const response = await api.get(`/api/problems/${problemId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(response.status).toBe(200);
      expect(response.data.id).toBe(problemId);
    });

    it('should return 404 for non-existent problem', async () => {
      try {
        await api.get('/api/problems/non-existent-id', {
          headers: { Authorization: `Bearer ${authToken}` }
        });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(404);
      }
    });
  });

  describe('DELETE /api/problems/:id - Delete Problem', () => {
    it('should delete a problem', async () => {
      // Create a problem to delete
      const problemData = {
        title: 'Problem to Delete ' + Date.now(),
        description: 'This problem will be deleted'
      };

      const createResponse = await api.post('/api/problems', problemData, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      const problemId = createResponse.data.id;

      const deleteResponse = await api.delete(`/api/problems/${problemId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(deleteResponse.status).toBe(200);

      // Verify it's deleted
      try {
        await api.get(`/api/problems/${problemId}`, {
          headers: { Authorization: `Bearer ${authToken}` }
        });
        fail('Problem should have been deleted');
      } catch (error) {
        expect(error.response.status).toBe(404);
      }
    });
  });

  // Cleanup
  afterAll(async () => {
    // Clean up created problems
    for (const problemId of createdProblems) {
      try {
        await api.delete(`/api/problems/${problemId}`, {
          headers: { Authorization: `Bearer ${authToken}` }
        });
      } catch (error) {
        // Ignore cleanup errors
      }
    }
  });
});
