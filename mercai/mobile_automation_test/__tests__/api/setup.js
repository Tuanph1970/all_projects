/**
 * Jest Setup for API E2E Tests
 * Runs before all test suites
 */

// Increase timeout for API tests
jest.setTimeout(30000);

// Global error handler for unhandled rejections
process.on('unhandledRejection', (error) => {
  console.error('Unhandled Promise Rejection:', error);
});

// Log test environment info
beforeAll(() => {
  const apiUrl = process.env.API_BASE_URL || 'http://localhost:8002';
  console.log('\n========================================');
  console.log('API E2E Test Suite');
  console.log('========================================');
  console.log(`API Base URL: ${apiUrl}`);
  console.log(`Test Timeout: 30000ms`);
  console.log(`Node Version: ${process.version}`);
  console.log('========================================\n');
});

// Clean up after all tests
afterAll(() => {
  console.log('\n========================================');
  console.log('API E2E Tests Complete');
  console.log('========================================\n');
});
