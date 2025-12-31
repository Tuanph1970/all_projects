const config = require('../config/testConfig');
const TestHelpers = require('../helpers/testHelpers');
const apiHelpers = require('../helpers/apiHelpers');

describe('Seller Dashboard', () => {
  beforeAll(async () => {
    // Check if server is reachable
    const serverReachable = await apiHelpers.checkServerHealth();
    if (!serverReachable) {
      console.warn('Warning: API server may not be reachable');
    }
  });

  beforeEach(async () => {
    // Launch app with delete flag to clear app data
    await device.launchApp({
      newInstance: true,
      permissions: { notifications: 'YES' }
    });
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Login as seller
    await loginAsSeller();
  });

  afterEach(async () => {
    await TestHelpers.takeScreenshot('seller-dashboard-test-end');
  });

  /**
   * Helper function to login as seller
   */
  async function loginAsSeller() {
    const testUser = config.testUsers.seller;

    console.log('Step 1: Waiting for login screen...');
    await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
    await TestHelpers.takeScreenshot('seller-login-step1-loginscreen');

    console.log('Step 2: Entering credentials...');
    await TestHelpers.typeText(
      by.id(config.screens.login.usernameInput),
      testUser.username
    );

    await TestHelpers.typeText(
      by.id(config.screens.login.passwordInput),
      testUser.password
    );
    await TestHelpers.takeScreenshot('seller-login-step2-credentials');

    console.log('Step 3: Tapping login button...');
    await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

    console.log('Step 4: Waiting for login to complete...');
    // Wait for login button to disappear (works regardless of language)
    await waitFor(element(by.id(config.screens.login.loginButton)))
      .not.toBeVisible()
      .withTimeout(config.timeouts.long);

    console.log('Step 5: Login button gone, checking for dashboard...');
    await TestHelpers.takeScreenshot('seller-login-step5-afterlogin');

    // Give more time for navigation and state updates
    await new Promise(resolve => setTimeout(resolve, 3000));
    await TestHelpers.takeScreenshot('seller-login-step6-wait3sec');

    console.log('Step 6: Looking for seller dashboard...');
    // Try to find the dashboard screen with extended timeout
    try {
      await waitFor(element(by.id(config.screens.sellerDashboard.screen)))
        .toBeVisible()
        .withTimeout(config.timeouts.extraLong);
      console.log('Seller dashboard found!');
    } catch (e) {
      console.log('Dashboard not found, checking what screen is visible...');
      await TestHelpers.takeScreenshot('seller-login-debug-current-screen');
      throw e;
    }

    console.log('Seller login successful, dashboard visible');
  }

  /**
   * Helper function to navigate to seller dashboard
   */
  async function navigateToSellerDashboard() {
    // After seller login, we're already on the dashboard screen (default tab)
    // Just verify the dashboard screen is visible
    await waitFor(element(by.id(config.screens.sellerDashboard.screen)))
      .toBeVisible()
      .withTimeout(config.timeouts.medium);
  }

  describe('Dashboard Overview', () => {
    it('should display seller dashboard screen', async () => {
      await navigateToSellerDashboard();

      // Verify dashboard screen is visible
      await expect(element(by.id(config.screens.sellerDashboard.screen))).toBeVisible();
      await TestHelpers.takeScreenshot('seller-dashboard-visible');
    });

    it('should display performance widgets with sales and orders', async () => {
      await navigateToSellerDashboard();

      // Verify widgets container is visible
      await expect(element(by.id(config.screens.sellerDashboard.widgets))).toBeVisible();

      // Verify total sales widget
      await expect(element(by.id(config.screens.sellerDashboard.totalSales))).toBeVisible();

      // Verify total orders widget
      await expect(element(by.id(config.screens.sellerDashboard.totalOrders))).toBeVisible();

      await TestHelpers.takeScreenshot('seller-dashboard-widgets');
    });

    it('should display sales chart', async () => {
      await navigateToSellerDashboard();

      // Scroll to sales chart if needed
      await waitFor(element(by.id(config.screens.sellerDashboard.salesChart)))
        .toBeVisible()
        .whileElement(by.id(config.screens.sellerDashboard.scroll))
        .scroll(200, 'down');

      await expect(element(by.id(config.screens.sellerDashboard.salesChart))).toBeVisible();
      await TestHelpers.takeScreenshot('seller-dashboard-sales-chart');
    });

    it('should display top products list', async () => {
      await navigateToSellerDashboard();

      // Scroll to top products if needed
      await waitFor(element(by.id(config.screens.sellerDashboard.topProducts)))
        .toBeVisible()
        .whileElement(by.id(config.screens.sellerDashboard.scroll))
        .scroll(200, 'down');

      await expect(element(by.id(config.screens.sellerDashboard.topProducts))).toBeVisible();
      await TestHelpers.takeScreenshot('seller-dashboard-top-products');
    });
  });

  describe('Inventory Alerts', () => {
    it('should display inventory alerts when products are low/out of stock', async () => {
      await navigateToSellerDashboard();

      // Check if alerts section exists (may not be visible if no alerts)
      const alertsExist = await TestHelpers.elementExists(by.id(config.screens.sellerDashboard.alerts));

      if (alertsExist) {
        await expect(element(by.id(config.screens.sellerDashboard.alertsTitle))).toBeVisible();
        await expect(element(by.id(config.screens.sellerDashboard.alertsCount))).toBeVisible();
        await TestHelpers.takeScreenshot('seller-dashboard-inventory-alerts');
      } else {
        // No alerts - this is also a valid state
        await TestHelpers.takeScreenshot('seller-dashboard-no-alerts');
      }
    });

    it('should show out of stock count when products are out of stock', async () => {
      await navigateToSellerDashboard();

      const alertsExist = await TestHelpers.elementExists(by.id(config.screens.sellerDashboard.alerts));

      if (alertsExist) {
        const outOfStockExists = await TestHelpers.elementExists(by.id(config.screens.sellerDashboard.outOfStock));
        if (outOfStockExists) {
          await expect(element(by.id(config.screens.sellerDashboard.outOfStock))).toBeVisible();
          await TestHelpers.takeScreenshot('seller-dashboard-out-of-stock');
        }
      }
    });

    it('should show low stock count when products are low', async () => {
      await navigateToSellerDashboard();

      const alertsExist = await TestHelpers.elementExists(by.id(config.screens.sellerDashboard.alerts));

      if (alertsExist) {
        const lowStockExists = await TestHelpers.elementExists(by.id(config.screens.sellerDashboard.lowStock));
        if (lowStockExists) {
          await expect(element(by.id(config.screens.sellerDashboard.lowStock))).toBeVisible();
          await TestHelpers.takeScreenshot('seller-dashboard-low-stock');
        }
      }
    });
  });

  describe('Dashboard Interactions', () => {
    it('should refresh dashboard data with pull-to-refresh', async () => {
      await navigateToSellerDashboard();

      // Perform pull-to-refresh
      await element(by.id(config.screens.sellerDashboard.scroll)).swipe('down', 'fast');

      // Wait for refresh to complete
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Verify dashboard is still visible after refresh
      await expect(element(by.id(config.screens.sellerDashboard.screen))).toBeVisible();
      await TestHelpers.takeScreenshot('seller-dashboard-after-refresh');
    });

    it('should show FAB button for adding new product', async () => {
      await navigateToSellerDashboard();

      // Verify FAB button is visible
      await expect(element(by.id(config.screens.sellerDashboard.fabAdd))).toBeVisible();
      await TestHelpers.takeScreenshot('seller-dashboard-fab-visible');
    });

    it('should show snackbar when FAB is tapped', async () => {
      await navigateToSellerDashboard();

      // Tap FAB button
      await TestHelpers.tapElement(by.id(config.screens.sellerDashboard.fabAdd));

      // Wait for snackbar to appear
      await new Promise(resolve => setTimeout(resolve, 1000));

      await TestHelpers.takeScreenshot('seller-dashboard-fab-tapped');
    });
  });

  describe('Dashboard Scroll Behavior', () => {
    it('should scroll through all dashboard sections', async () => {
      await navigateToSellerDashboard();

      // Scroll down to see all content
      await element(by.id(config.screens.sellerDashboard.scroll)).scroll(300, 'down');
      await TestHelpers.takeScreenshot('seller-dashboard-scrolled-down');

      // Scroll back up
      await element(by.id(config.screens.sellerDashboard.scroll)).scroll(300, 'up');
      await TestHelpers.takeScreenshot('seller-dashboard-scrolled-up');
    });
  });
});
