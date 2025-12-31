const config = require('../config/testConfig');
const TestHelpers = require('../helpers/testHelpers');
const apiHelpers = require('../helpers/apiHelpers');

describe('Seller Analytics', () => {
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
    await TestHelpers.takeScreenshot('seller-analytics-test-end');
  });

  /**
   * Helper function to login as seller
   */
  async function loginAsSeller() {
    const testUser = config.testUsers.seller;

    await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

    await TestHelpers.typeText(
      by.id(config.screens.login.usernameInput),
      testUser.username
    );

    await TestHelpers.typeText(
      by.id(config.screens.login.passwordInput),
      testUser.password
    );

    await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

    // Wait for login button to disappear (works regardless of language)
    await waitFor(element(by.id(config.screens.login.loginButton)))
      .not.toBeVisible()
      .withTimeout(config.timeouts.long);

    // Give time for navigation and state updates
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Wait for seller dashboard screen to appear (default screen after seller login)
    await waitFor(element(by.id(config.screens.sellerDashboard.screen)))
      .toBeVisible()
      .withTimeout(config.timeouts.extraLong);

    console.log('Seller login successful, dashboard visible');
  }

  /**
   * Helper function to navigate to analytics screen
   */
  async function navigateToAnalytics() {
    // After seller login, we're on the dashboard. Navigate to Analytics tab
    await waitFor(element(by.id(config.tabs.analytics)))
      .toBeVisible()
      .withTimeout(config.timeouts.medium);

    // Tap on analytics tab
    await element(by.id(config.tabs.analytics)).tap();
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Wait for the analytics screen to be visible
    await waitFor(element(by.id(config.screens.analytics.screen)))
      .toBeVisible()
      .withTimeout(config.timeouts.long);
  }

  describe('Analytics Overview', () => {
    it('should display analytics screen', async () => {
      await navigateToAnalytics();

      // Verify analytics screen is visible
      await expect(element(by.id(config.screens.analytics.screen))).toBeVisible();
      await TestHelpers.takeScreenshot('analytics-screen-visible');
    });

    it('should show loading indicator while fetching data', async () => {
      // Relaunch to catch loading state
      await device.launchApp({ newInstance: true });
      await new Promise(resolve => setTimeout(resolve, 500));

      await loginAsSeller();

      // Check if loading state exists (may be very brief)
      const loadingExists = await TestHelpers.elementExists(by.id(config.screens.analytics.loading));
      if (loadingExists) {
        await expect(element(by.id(config.screens.analytics.loadingIndicator))).toBeVisible();
        await TestHelpers.takeScreenshot('analytics-loading');
      }

      // Wait for data to load
      await navigateToAnalytics();
    });

    it('should display back button', async () => {
      await navigateToAnalytics();

      await expect(element(by.id(config.screens.analytics.backButton))).toBeVisible();
      await TestHelpers.takeScreenshot('analytics-back-button');
    });
  });

  describe('Time Period Selection', () => {
    it('should display period selection chips', async () => {
      await navigateToAnalytics();

      // Verify period card is visible
      await expect(element(by.id(config.screens.analytics.periodCard))).toBeVisible();
      await expect(element(by.id(config.screens.analytics.periodChips))).toBeVisible();

      await TestHelpers.takeScreenshot('analytics-period-chips');
    });

    it('should select 7 days period', async () => {
      await navigateToAnalytics();

      // Tap 7 days chip
      await TestHelpers.tapElement(by.id(config.screens.analytics.period7));

      // Wait for data to reload
      await new Promise(resolve => setTimeout(resolve, 1500));

      await TestHelpers.takeScreenshot('analytics-7-days-selected');
    });

    it('should select 30 days period', async () => {
      await navigateToAnalytics();

      // Tap 30 days chip
      await TestHelpers.tapElement(by.id(config.screens.analytics.period30));

      // Wait for data to reload
      await new Promise(resolve => setTimeout(resolve, 1500));

      await TestHelpers.takeScreenshot('analytics-30-days-selected');
    });

    it('should select 90 days (3 months) period', async () => {
      await navigateToAnalytics();

      // Tap 90 days chip
      await TestHelpers.tapElement(by.id(config.screens.analytics.period90));

      // Wait for data to reload
      await new Promise(resolve => setTimeout(resolve, 1500));

      await TestHelpers.takeScreenshot('analytics-90-days-selected');
    });

    it('should select 365 days (1 year) period', async () => {
      await navigateToAnalytics();

      // Tap 365 days chip
      await TestHelpers.tapElement(by.id(config.screens.analytics.period365));

      // Wait for data to reload
      await new Promise(resolve => setTimeout(resolve, 1500));

      await TestHelpers.takeScreenshot('analytics-365-days-selected');
    });
  });

  describe('Sales Analytics', () => {
    it('should display sales analytics card', async () => {
      await navigateToAnalytics();

      await expect(element(by.id(config.screens.analytics.salesCard))).toBeVisible();
      await TestHelpers.takeScreenshot('analytics-sales-card');
    });

    it('should display total revenue metric', async () => {
      await navigateToAnalytics();

      // Scroll to sales metrics if needed
      await waitFor(element(by.id(config.screens.analytics.salesMetrics)))
        .toBeVisible()
        .whileElement(by.id(config.screens.analytics.scroll))
        .scroll(100, 'down');

      await expect(element(by.id(config.screens.analytics.revenueMetric))).toBeVisible();
      await expect(element(by.id(config.screens.analytics.revenueValue))).toBeVisible();
      await expect(element(by.id(config.screens.analytics.revenueGrowth))).toBeVisible();

      await TestHelpers.takeScreenshot('analytics-revenue-metric');
    });

    it('should display total orders metric', async () => {
      await navigateToAnalytics();

      // Scroll to sales metrics if needed
      await waitFor(element(by.id(config.screens.analytics.salesMetrics)))
        .toBeVisible()
        .whileElement(by.id(config.screens.analytics.scroll))
        .scroll(100, 'down');

      await expect(element(by.id(config.screens.analytics.ordersMetric))).toBeVisible();
      await expect(element(by.id(config.screens.analytics.ordersValue))).toBeVisible();
      await expect(element(by.id(config.screens.analytics.ordersGrowth))).toBeVisible();

      await TestHelpers.takeScreenshot('analytics-orders-metric');
    });
  });

  describe('Inventory Overview', () => {
    it('should display inventory overview card', async () => {
      await navigateToAnalytics();

      // Scroll to inventory card
      await waitFor(element(by.id(config.screens.analytics.inventoryCard)))
        .toBeVisible()
        .whileElement(by.id(config.screens.analytics.scroll))
        .scroll(200, 'down');

      await expect(element(by.id(config.screens.analytics.inventoryCard))).toBeVisible();
      await TestHelpers.takeScreenshot('analytics-inventory-card');
    });
  });

  describe('Top Products', () => {
    it('should display top products card', async () => {
      await navigateToAnalytics();

      // Scroll to top products card
      await waitFor(element(by.id(config.screens.analytics.topProductsCard)))
        .toBeVisible()
        .whileElement(by.id(config.screens.analytics.scroll))
        .scroll(200, 'down');

      await expect(element(by.id(config.screens.analytics.topProductsCard))).toBeVisible();
      await TestHelpers.takeScreenshot('analytics-top-products-card');
    });
  });

  describe('Customer Analytics', () => {
    it('should display customer insights card', async () => {
      await navigateToAnalytics();

      // Scroll to customer card
      await waitFor(element(by.id(config.screens.analytics.customerCard)))
        .toBeVisible()
        .whileElement(by.id(config.screens.analytics.scroll))
        .scroll(300, 'down');

      await expect(element(by.id(config.screens.analytics.customerCard))).toBeVisible();
      await TestHelpers.takeScreenshot('analytics-customer-card');
    });

    it('should display new customers metric when data available', async () => {
      await navigateToAnalytics();

      // Scroll to customer metrics
      await waitFor(element(by.id(config.screens.analytics.customerCard)))
        .toBeVisible()
        .whileElement(by.id(config.screens.analytics.scroll))
        .scroll(300, 'down');

      const customerMetricsExist = await TestHelpers.elementExists(by.id(config.screens.analytics.customerMetrics));

      if (customerMetricsExist) {
        await expect(element(by.id(config.screens.analytics.newCustomersMetric))).toBeVisible();
        await expect(element(by.id(config.screens.analytics.newCustomersValue))).toBeVisible();
        await TestHelpers.takeScreenshot('analytics-new-customers-metric');
      }
    });

    it('should display repeat rate metric when data available', async () => {
      await navigateToAnalytics();

      // Scroll to customer metrics
      await waitFor(element(by.id(config.screens.analytics.customerCard)))
        .toBeVisible()
        .whileElement(by.id(config.screens.analytics.scroll))
        .scroll(300, 'down');

      const customerMetricsExist = await TestHelpers.elementExists(by.id(config.screens.analytics.customerMetrics));

      if (customerMetricsExist) {
        await expect(element(by.id(config.screens.analytics.repeatRateMetric))).toBeVisible();
        await expect(element(by.id(config.screens.analytics.repeatRateValue))).toBeVisible();
        await TestHelpers.takeScreenshot('analytics-repeat-rate-metric');
      }
    });
  });

  describe('Analytics Interactions', () => {
    it('should refresh analytics data with pull-to-refresh', async () => {
      await navigateToAnalytics();

      // Perform pull-to-refresh
      await element(by.id(config.screens.analytics.scroll)).swipe('down', 'fast');

      // Wait for refresh to complete
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Verify analytics screen is still visible after refresh
      await expect(element(by.id(config.screens.analytics.screen))).toBeVisible();
      await TestHelpers.takeScreenshot('analytics-after-refresh');
    });

    it('should navigate back when back button is pressed', async () => {
      await navigateToAnalytics();

      // Tap back button
      await TestHelpers.tapElement(by.id(config.screens.analytics.backButton));

      // Wait for navigation
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Verify we are no longer on analytics screen
      await waitFor(element(by.id(config.screens.analytics.screen)))
        .not.toBeVisible()
        .withTimeout(config.timeouts.medium);

      await TestHelpers.takeScreenshot('analytics-navigated-back');
    });
  });

  describe('Analytics Error Handling', () => {
    it('should handle error state gracefully', async () => {
      // Note: This test depends on error state being triggered
      // In real scenarios, this would require mocking API failures
      await navigateToAnalytics();

      const errorExists = await TestHelpers.elementExists(by.id(config.screens.analytics.screenError));

      if (errorExists) {
        await expect(element(by.id(config.screens.analytics.errorContainer))).toBeVisible();
        await expect(element(by.id(config.screens.analytics.errorTitle))).toBeVisible();
        await expect(element(by.id(config.screens.analytics.errorText))).toBeVisible();
        await TestHelpers.takeScreenshot('analytics-error-state');
      } else {
        // No error - verify normal state
        await expect(element(by.id(config.screens.analytics.screen))).toBeVisible();
        await TestHelpers.takeScreenshot('analytics-no-error');
      }
    });
  });

  describe('Analytics Scroll Behavior', () => {
    it('should scroll through all analytics sections', async () => {
      await navigateToAnalytics();

      // Scroll down to see all content
      await element(by.id(config.screens.analytics.scroll)).scroll(500, 'down');
      await TestHelpers.takeScreenshot('analytics-scrolled-down');

      // Scroll back up
      await element(by.id(config.screens.analytics.scroll)).scroll(500, 'up');
      await TestHelpers.takeScreenshot('analytics-scrolled-up');
    });
  });
});
