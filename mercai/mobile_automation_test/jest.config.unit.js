/** Jest configuration for unit tests (no device required) */
module.exports = {
  rootDir: '.',
  testMatch: [
    '<rootDir>/__tests__/**/*.test.js',
    '<rootDir>/e2e/helpers/**/*.test.js',
    '<rootDir>/e2e/config/**/*.test.js'
  ],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/e2e/auth/', // Ignore E2E tests
    '/e2e/.*\\.test\\.js$' // Ignore all E2E test files
  ],
  testEnvironment: 'node',
  testTimeout: 10000,
  verbose: true,
  collectCoverage: false,
  coveragePathIgnorePatterns: ['/node_modules/'],
};
