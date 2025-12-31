const detox = require('detox');
const adapter = require('detox/runners/jest/adapter');
const specReporter = require('detox/runners/jest/specReporter');
const config = require('../.detoxrc');

// Set E2E mode flag
global.__E2E__ = true;

// Longer timeout for slow operations
jest.setTimeout(120000);
jasmine.getEnv().addReporter(adapter);
jasmine.getEnv().addReporter(specReporter);

beforeAll(async () => {
  // Initialize Detox
  await detox.init(config, {
    launchApp: false, // Don't auto-launch
    initGlobals: true
  });

  console.log('Detox initialized successfully');
});

beforeEach(async () => {
  await adapter.beforeEach();

  // Launch app with new instance and disable synchronization
  await device.launchApp({
    newInstance: true,
    permissions: { notifications: 'YES' },
    launchArgs: { detoxPrintBusyIdleResources: 'YES' }
  });

  // CRITICAL: Disable synchronization because HomeScreen makes API calls
  await device.disableSynchronization();

  console.log('App launched, synchronization disabled');
});

afterEach(async () => {
  await adapter.afterAll();
});

afterAll(async () => {
  await detox.cleanup();
});

// Helper to wait for element with manual timeout
global.waitForElementSafe = async (matcher, timeout = 10000) => {
  try {
    await waitFor(element(matcher))
      .toBeVisible()
      .withTimeout(timeout);
    return true;
  } catch (error) {
    console.log(`Element not found after ${timeout}ms`);
    return false;
  }
};

// Helper to wait a specific time (use sparingly!)
global.sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
