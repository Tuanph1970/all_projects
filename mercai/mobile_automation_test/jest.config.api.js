/** Jest configuration for API E2E tests (no device required, runs against live services) */
module.exports = {
  rootDir: '.',
  testMatch: [
    '<rootDir>/__tests__/api/**/*.test.js',
    '<rootDir>/__tests__/api/**/*.api.test.js'
  ],
  testPathIgnorePatterns: [
    '/node_modules/'
  ],
  testEnvironment: 'node',
  testTimeout: 30000, // 30 seconds for API calls
  verbose: true,
  collectCoverage: false,
  coveragePathIgnorePatterns: ['/node_modules/'],
  // Run tests sequentially to avoid rate limiting issues
  maxConcurrency: 1,
  maxWorkers: 1,
  // Setup and teardown
  setupFilesAfterEnv: ['<rootDir>/__tests__/api/setup.js'],
};
