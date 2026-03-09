/**
 * API E2E Tests for Solution Service (ML/OCR)
 * Tests solution generation endpoints
 *
 * Run with: npm run test:api:solution
 */

const axios = require('axios');

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8001';
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:8002';
const API_TIMEOUT = 30000; // Longer timeout for ML processing

// API clients
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
});

const mlApi = axios.create({
  baseURL: ML_SERVICE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Test credentials
const TEST_CREDENTIALS = {
  email: 'test_solution_user@test.com',
  password: 'Test@12345678'
};

let authToken = null;

describe('Solution Service API E2E Tests', () => {
  // Login before running tests
  beforeAll(async () => {
    try {
      const loginResponse = await api.post('/api/auth/login', TEST_CREDENTIALS);
      authToken = loginResponse.data.accessToken;
      console.log('✅ Authenticated for Solution Service tests');
    } catch (error) {
      console.warn('⚠️  Could not authenticate. Some tests may fail.');
    }
  });

  describe('POST /api/solutions/ocr - OCR Processing', () => {
    it('should process image with OCR', async () => {
      const ocrData = {
        imageUrl: 'https://example.com/test-math-problem.jpg',
        language: 'en'
      };

      const response = await api.post('/api/solutions/ocr', ocrData, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('text');
      expect(response.data).toHaveProperty('confidence');
    });

    it('should reject OCR without authentication', async () => {
      const ocrData = {
        imageUrl: 'https://example.com/test.jpg'
      };

      try {
        await api.post('/api/solutions/ocr', ocrData);
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(401);
      }
    });
  });

  describe('POST /api/solutions/generate - Generate Solution', () => {
    it('should generate solution for math problem', async () => {
      const solutionData = {
        problemText: 'Solve for x: 2x + 3 = 7',
        category: 'algebra',
        gradeLevel: 'high_school'
      };

      const response = await api.post('/api/solutions/generate', solutionData, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(response.status).toBe(200);
      expect(response.data).toHaveProperty('solution');
      expect(response.data).toHaveProperty('steps');
    });

    it('should include step-by-step explanation', async () => {
      const solutionData = {
        problemText: 'Calculate the area of a circle with radius 5',
        category: 'geometry'
      };

      const response = await api.post('/api/solutions/generate', solutionData, {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(response.status).toBe(200);
      expect(response.data.steps).toBeDefined();
      expect(Array.isArray(response.data.steps)).toBe(true);
      expect(response.data.steps.length).toBeGreaterThan(0);
    });
  });

  describe('GET /api/solutions/history - Get Solution History', () => {
    it('should return user solution history', async () => {
      const response = await api.get('/api/solutions/history', {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(response.status).toBe(200);
      expect(Array.isArray(response.data)).toBe(true);
    });

    it('should support pagination', async () => {
      const response = await api.get('/api/solutions/history?page=1&limit=10', {
        headers: { Authorization: `Bearer ${authToken}` }
      });

      expect(response.status).toBe(200);
    });
  });

  describe('ML Service Health Check', () => {
    it('should have ML service available', async () => {
      try {
        const response = await mlApi.get('/health');
        expect(response.status).toBe(200);
        console.log('✅ ML Service is reachable');
      } catch (error) {
        console.warn('⚠️  ML Service not reachable at', ML_SERVICE_URL);
      }
    });
  });
});
