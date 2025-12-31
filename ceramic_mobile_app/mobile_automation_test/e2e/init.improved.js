const detox = require('detox');
const adapter = require('detox/runners/jest/adapter');
const specReporter = require('detox/runners/jest/specReporter');
const config = require('../.detoxrc');

// Set E2E mode flag
global.__E2E__ = true;

// Set the default timeout
jest.setTimeout(120000);
jasmine.getEnv().addReporter(adapter);
jasmine.getEnv().addReporter(specReporter);

beforeAll(async () => {
  // Initialize Detox with proper synchronization
  await detox.init(config, {
    launchApp: false, // Don't launch here, let individual tests control it
    initGlobals: true
  });

  // Configure synchronization settings
  // Only disable for specific problematic animations
  try {
    // Set URL blacklist for specific endpoints that cause issues
    // Only blacklist long-polling or streaming endpoints
    const blacklistUrls = [
      '.*socket\\.io.*',  // WebSocket connections
      '.*\\.hot-update\\..*', // Hot reload in development
    ];

    if (blacklistUrls.length > 0) {
      await device.setURLBlacklist(blacklistUrls);
      console.log('Detox: Blacklisted problematic network endpoints');
    }
  } catch (e) {
    console.log('Detox: Could not set URL blacklist:', e.message);
  }

  // Keep synchronization ENABLED by default
  // Only disable for specific tests that need it
  console.log('Detox: Synchronization enabled (default)');
});

beforeEach(async () => {
  await adapter.beforeEach();
});

afterAll(async () => {
  await adapter.afterAll();
  await detox.cleanup();
});

// Helper function for tests to temporarily disable synchronization
global.withoutSynchronization = async (callback) => {
  await device.disableSynchronization();
  try {
    await callback();
  } finally {
    await device.enableSynchronization();
  }
};

// Helper function to wait for element with retry
global.waitForElementWithRetry = async (matcher, timeout = 10000, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      await waitFor(element(matcher))
        .toBeVisible()
        .withTimeout(timeout);
      return true;
    } catch (error) {
      if (i === retries - 1) throw error;
      console.log(`Retry ${i + 1}/${retries} waiting for element`);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
};
