// Set E2E mode flag
global.__E2E__ = true;

// Longer timeout for slow operations
jest.setTimeout(120000);

beforeAll(async () => {
  console.log('Detox initialized successfully');
});

beforeEach(async () => {
  // Launch app with cleared data to ensure we start at LoginScreen
  console.log('Launching app with clear data...');
  try {
    await device.launchApp({
      newInstance: true,
      permissions: { notifications: 'YES' },
      delete: true  // Clear app data before launch
    });
    console.log('App launched');
  } catch (error) {
    console.log('Launch error (expected):', error.message);
  }

  // Wait for app to stabilize after launch
  await new Promise(resolve => setTimeout(resolve, 2000));

  // CRITICAL: Disable synchronization immediately after launch
  // because screens may make API calls
  await device.disableSynchronization();
  console.log('Synchronization disabled');
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
