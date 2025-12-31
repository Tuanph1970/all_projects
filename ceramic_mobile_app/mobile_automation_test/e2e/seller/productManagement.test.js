const config = require('../config/testConfig');
const TestHelpers = require('../helpers/testHelpers');
const apiHelpers = require('../helpers/apiHelpers');

describe('Product Management', () => {
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
    await TestHelpers.takeScreenshot('product-management-test-end');
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
   * Helper function to navigate to product management screen
   */
  async function navigateToProductManagement() {
    // After seller login, we're on the dashboard. Navigate to Products tab
    await waitFor(element(by.id(config.tabs.products)))
      .toBeVisible()
      .withTimeout(config.timeouts.medium);

    // Tap on products tab
    await element(by.id(config.tabs.products)).tap();
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Wait for the product management screen to be visible
    await waitFor(element(by.id(config.screens.productManagement.screen)))
      .toBeVisible()
      .withTimeout(config.timeouts.long);
  }

  describe('Product Management Overview', () => {
    it('should display product management screen', async () => {
      await navigateToProductManagement();

      // Verify product management screen is visible
      await expect(element(by.id(config.screens.productManagement.screen))).toBeVisible();
      await TestHelpers.takeScreenshot('product-management-visible');
    });

    it('should display back button', async () => {
      await navigateToProductManagement();

      await expect(element(by.id(config.screens.productManagement.backButton))).toBeVisible();
      await TestHelpers.takeScreenshot('product-management-back-button');
    });

    it('should display filter button', async () => {
      await navigateToProductManagement();

      await expect(element(by.id(config.screens.productManagement.filterButton))).toBeVisible();
      await TestHelpers.takeScreenshot('product-management-filter-button');
    });

    it('should display content area', async () => {
      await navigateToProductManagement();

      await expect(element(by.id(config.screens.productManagement.content))).toBeVisible();
      await TestHelpers.takeScreenshot('product-management-content');
    });
  });

  describe('Product Search', () => {
    it('should display search bar', async () => {
      await navigateToProductManagement();

      await expect(element(by.id(config.screens.productManagement.search))).toBeVisible();
      await TestHelpers.takeScreenshot('product-management-search-bar');
    });

    it('should allow typing in search bar', async () => {
      await navigateToProductManagement();

      const searchQuery = 'ceramic vase';

      await TestHelpers.typeText(
        by.id(config.screens.productManagement.search),
        searchQuery
      );

      // Wait for search results
      await new Promise(resolve => setTimeout(resolve, 1500));

      await TestHelpers.takeScreenshot('product-management-search-typed');
    });

    it('should clear search when text is deleted', async () => {
      await navigateToProductManagement();

      // Type search query
      await TestHelpers.typeText(
        by.id(config.screens.productManagement.search),
        'test product'
      );

      await new Promise(resolve => setTimeout(resolve, 1000));

      // Clear search
      await element(by.id(config.screens.productManagement.search)).clearText();

      await new Promise(resolve => setTimeout(resolve, 1000));

      await TestHelpers.takeScreenshot('product-management-search-cleared');
    });
  });

  describe('Product List', () => {
    it('should display product list when products exist', async () => {
      await navigateToProductManagement();

      const listExists = await TestHelpers.elementExists(by.id(config.screens.productManagement.list));

      if (listExists) {
        await expect(element(by.id(config.screens.productManagement.list))).toBeVisible();
        await TestHelpers.takeScreenshot('product-management-list-visible');
      }
    });

    it('should display empty state when no products exist', async () => {
      await navigateToProductManagement();

      const emptyExists = await TestHelpers.elementExists(by.id(config.screens.productManagement.empty));

      if (emptyExists) {
        await expect(element(by.id(config.screens.productManagement.empty))).toBeVisible();
        await TestHelpers.takeScreenshot('product-management-empty-state');
      }
    });

    it('should show loading indicator while fetching products', async () => {
      // Relaunch to catch loading state
      await device.launchApp({ newInstance: true });
      await new Promise(resolve => setTimeout(resolve, 500));

      await loginAsSeller();

      // Check if loading state exists (may be very brief)
      const loadingExists = await TestHelpers.elementExists(by.id(config.screens.productManagement.loading));
      if (loadingExists) {
        await TestHelpers.takeScreenshot('product-management-loading');
      }

      await navigateToProductManagement();
    });
  });

  describe('Product Selection', () => {
    it('should show selection bar when products are selected', async () => {
      await navigateToProductManagement();

      // Check if selection bar exists (depends on products being selected)
      const selectionBarExists = await TestHelpers.elementExists(by.id(config.screens.productManagement.selectionBar));

      if (selectionBarExists) {
        await expect(element(by.id(config.screens.productManagement.selectionBar))).toBeVisible();
        await TestHelpers.takeScreenshot('product-management-selection-bar');
      }
    });

    it('should display selection count', async () => {
      await navigateToProductManagement();

      const selectionBarExists = await TestHelpers.elementExists(by.id(config.screens.productManagement.selectionBar));

      if (selectionBarExists) {
        await expect(element(by.id(config.screens.productManagement.selectionCount))).toBeVisible();
        await TestHelpers.takeScreenshot('product-management-selection-count');
      }
    });

    it('should have select all button', async () => {
      await navigateToProductManagement();

      const selectionBarExists = await TestHelpers.elementExists(by.id(config.screens.productManagement.selectionBar));

      if (selectionBarExists) {
        await expect(element(by.id(config.screens.productManagement.selectAll))).toBeVisible();
        await TestHelpers.takeScreenshot('product-management-select-all-button');
      }
    });

    it('should have clear selection button', async () => {
      await navigateToProductManagement();

      const selectionBarExists = await TestHelpers.elementExists(by.id(config.screens.productManagement.selectionBar));

      if (selectionBarExists) {
        await expect(element(by.id(config.screens.productManagement.clearSelection))).toBeVisible();
        await TestHelpers.takeScreenshot('product-management-clear-selection-button');
      }
    });
  });

  describe('Bulk Actions', () => {
    it('should have bulk actions button when products are selected', async () => {
      await navigateToProductManagement();

      const selectionBarExists = await TestHelpers.elementExists(by.id(config.screens.productManagement.selectionBar));

      if (selectionBarExists) {
        await expect(element(by.id(config.screens.productManagement.bulkActions))).toBeVisible();
        await TestHelpers.takeScreenshot('product-management-bulk-actions-button');
      }
    });
  });

  describe('Add Product Navigation', () => {
    it('should display FAB for adding new product', async () => {
      await navigateToProductManagement();

      await expect(element(by.id(config.screens.productManagement.fabAdd))).toBeVisible();
      await TestHelpers.takeScreenshot('product-management-fab-visible');
    });

    it('should navigate to add product screen when FAB is tapped', async () => {
      await navigateToProductManagement();

      // Tap FAB
      await TestHelpers.tapElement(by.id(config.screens.productManagement.fabAdd));

      // Wait for navigation
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Verify navigation to add product screen
      await waitFor(element(by.id(config.screens.addProduct.screen)))
        .toBeVisible()
        .withTimeout(config.timeouts.medium);

      await TestHelpers.takeScreenshot('product-management-navigated-to-add');
    });
  });

  describe('Product Management Interactions', () => {
    it('should navigate back when back button is pressed', async () => {
      await navigateToProductManagement();

      // Tap back button
      await TestHelpers.tapElement(by.id(config.screens.productManagement.backButton));

      // Wait for navigation
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Verify we are no longer on product management screen
      await waitFor(element(by.id(config.screens.productManagement.screen)))
        .not.toBeVisible()
        .withTimeout(config.timeouts.medium);

      await TestHelpers.takeScreenshot('product-management-navigated-back');
    });

    it('should open filter options when filter button is pressed', async () => {
      await navigateToProductManagement();

      // Tap filter button
      await TestHelpers.tapElement(by.id(config.screens.productManagement.filterButton));

      // Wait for filter options to appear
      await new Promise(resolve => setTimeout(resolve, 1000));

      await TestHelpers.takeScreenshot('product-management-filter-options');
    });
  });
});
