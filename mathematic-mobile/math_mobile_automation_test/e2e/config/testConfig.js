/**
 * Test Configuration for Mathematics Solver Mobile App
 * Centralized configuration for E2E and API tests
 */

module.exports = {
  // API Configuration
  api: {
    baseUrl: process.env.API_BASE_URL || 'http://localhost:8001',
    mlServiceUrl: process.env.ML_SERVICE_URL || 'http://localhost:8002',
    timeout: parseInt(process.env.API_TIMEOUT, 10) || 10000,
  },

  // Test Users Configuration
  testUsers: {
    default: {
      email: process.env.TEST_USER_EMAIL || 'test_user@test.com',
      password: process.env.TEST_USER_PASSWORD || 'Test@12345678',
    },
    customer: {
      email: process.env.TEST_CUSTOMER_EMAIL || 'test_customer@test.com',
      password: process.env.TEST_CUSTOMER_PASSWORD || 'Test@12345678',
    },
  },

  // Timeout Configuration (in milliseconds)
  timeouts: {
    short: 5000,
    medium: 10000,
    long: 20000,
    extraLong: 30000,
  },

  // Screen Identifiers (testIDs used in React Native components)
  screens: {
    login: {
      emailInput: 'login-email-input',
      passwordInput: 'login-password-input',
      loginButton: 'login-button',
      registerButton: 'register-button',
    },
    register: {
      screen: 'register-screen',
      nameInput: 'register-name-input',
      emailInput: 'register-email-input',
      passwordInput: 'register-password-input',
      confirmPasswordInput: 'register-confirm-password-input',
      submitButton: 'register-submit-button',
    },
    home: {
      screen: 'home-screen',
      scanButton: 'scan-button',
      historyButton: 'history-button',
      profileButton: 'profile-button',
    },
    scan: {
      screen: 'scan-screen',
      captureButton: 'capture-button',
      galleryButton: 'gallery-button',
    },
    solution: {
      screen: 'solution-screen',
      result: 'solution-result',
      steps: 'solution-steps',
      explanation: 'solution-explanation',
    },
  },

  // App Configuration
  app: {
    appId: 'com.mathematics.solver',
    bundleId: 'com.mathematics.solver',
  },

  // Test Data
  testData: {
    validEmail: 'test@example.com',
    invalidEmail: 'invalid-email',
    weakPassword: 'weak',
    strongPassword: 'Test@12345678',
  },
};
