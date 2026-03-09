/**
 * API Test Helpers for Mathematics Solver
 * Reusable helper functions for API testing
 */

const axios = require('axios');

/**
 * Create an API client instance
 * @param {string} baseUrl - Base URL for the API
 * @param {string} authToken - Optional auth token
 * @returns {axios.AxiosInstance}
 */
function createApiClient(baseUrl, authToken = null) {
  const client = axios.create({
    baseURL: baseUrl,
    timeout: parseInt(process.env.API_TIMEOUT, 10) || 10000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (authToken) {
    client.defaults.headers.common.Authorization = `Bearer ${authToken}`;
  }

  return client;
}

/**
 * Generate a unique test user
 * @returns {Object} Test user data
 */
function generateTestUser() {
  const timestamp = Date.now();
  return {
    email: `test_${timestamp}@test.com`,
    password: 'Test@12345678',
    fullName: `Test User ${timestamp}`,
    phoneNumber: '+84123456789',
  };
}

/**
 * Register a new test user and return auth tokens
 * @param {axios.AxiosInstance} api - API client
 * @returns {Promise<Object>} Auth tokens and user data
 */
async function registerAndLogin(api) {
  const testUser = generateTestUser();

  // Register
  const registerResponse = await api.post('/api/auth/register', testUser);
  const userId = registerResponse.data.id;

  // Login
  const loginResponse = await api.post('/api/auth/login', {
    email: testUser.email,
    password: testUser.password,
  });

  return {
    user: { ...testUser, id: userId },
    tokens: loginResponse.data,
  };
}

/**
 * Wait for a specified time
 * @param {number} ms - Milliseconds to wait
 * @returns {Promise<void>}
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Check if API is healthy
 * @param {string} baseUrl - API base URL
 * @returns {Promise<boolean>}
 */
async function checkApiHealth(baseUrl) {
  try {
    const response = await axios.get(`${baseUrl}/health`, {
      timeout: 5000,
      validateStatus: () => true,
    });
    return response.status === 200;
  } catch (error) {
    return false;
  }
}

module.exports = {
  createApiClient,
  generateTestUser,
  registerAndLogin,
  sleep,
  checkApiHealth,
};
