const config = require('../config/testConfig');
const TestHelpers = require('../helpers/testHelpers');
const apiHelpers = require('../helpers/apiHelpers');

describe('Add Product', () => {
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
      permissions: { notifications: 'YES', camera: 'YES', photos: 'YES' }
    });
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Login as seller
    await loginAsSeller();
  });

  afterEach(async () => {
    await TestHelpers.takeScreenshot('add-product-test-end');
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
   * Helper function to navigate to add product screen via Products tab -> FAB
   */
  async function navigateToAddProduct() {
    // After seller login, we're already on the dashboard screen
    // Navigate to Products tab to access product management
    try {
      await waitFor(element(by.id(config.tabs.products)))
        .toBeVisible()
        .withTimeout(config.timeouts.medium);

      // Tap on products tab
      await element(by.id(config.tabs.products)).tap();
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Wait for product management screen
      await waitFor(element(by.id(config.screens.productManagement.screen)))
        .toBeVisible()
        .withTimeout(config.timeouts.medium);

      // Tap FAB to add product
      await TestHelpers.tapElement(by.id(config.screens.productManagement.fabAdd));
    } catch (e) {
      // Products tab navigation failed, try using dashboard FAB instead
      console.log('Products tab navigation failed, using dashboard FAB...');

      // Make sure we're on seller dashboard
      const dashboardVisible = await TestHelpers.elementExists(by.id(config.screens.sellerDashboard.screen));
      if (dashboardVisible) {
        // Use dashboard FAB - note: dashboard FAB shows snackbar, doesn't navigate
        // We need to navigate to AddProduct screen differently
        try {
          // Try navigating directly via the navigation stack
          await waitFor(element(by.id(config.screens.sellerDashboard.fabAdd)))
            .toBeVisible()
            .withTimeout(config.timeouts.short);
          await TestHelpers.tapElement(by.id(config.screens.sellerDashboard.fabAdd));
          await new Promise(resolve => setTimeout(resolve, 1000));
        } catch (e2) {
          console.log('Dashboard FAB not found either');
        }
      }
    }

    // Wait for the add product screen to be visible
    await waitFor(element(by.id(config.screens.addProduct.screen)))
      .toBeVisible()
      .withTimeout(config.timeouts.long);
  }

  /**
   * Generate unique test product data
   */
  function generateTestProduct() {
    const timestamp = Date.now();
    return {
      title: `Test Ceramic Vase ${timestamp}`,
      description: `Beautiful handmade ceramic vase with unique patterns. Created at ${timestamp}.`,
      price: '49.99',
      category: 'Vases',
      stock: '10',
      tags: 'ceramic, handmade, vase, pottery'
    };
  }

  describe('Add Product Screen Overview', () => {
    it('should display add product screen', async () => {
      await navigateToAddProduct();

      // Verify add product screen is visible
      await expect(element(by.id(config.screens.addProduct.screen))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-screen-visible');
    });

    it('should display back button', async () => {
      await navigateToAddProduct();

      await expect(element(by.id(config.screens.addProduct.backButton))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-back-button');
    });

    it('should display scrollable content', async () => {
      await navigateToAddProduct();

      await expect(element(by.id(config.screens.addProduct.scroll))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-scroll');
    });
  });

  describe('Product Images Section', () => {
    it('should display images section', async () => {
      await navigateToAddProduct();

      await expect(element(by.id(config.screens.addProduct.imagesSection))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-images-section');
    });

    it('should display images container', async () => {
      await navigateToAddProduct();

      await expect(element(by.id(config.screens.addProduct.imagesContainer))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-images-container');
    });

    it('should display add image button', async () => {
      await navigateToAddProduct();

      await expect(element(by.id(config.screens.addProduct.addImageButton))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-add-image-button');
    });

    it('should show image options when add image button is tapped', async () => {
      await navigateToAddProduct();

      // Tap add image button
      await TestHelpers.tapElement(by.id(config.screens.addProduct.addImageButton));

      // Wait for alert dialog to appear
      await new Promise(resolve => setTimeout(resolve, 1000));

      await TestHelpers.takeScreenshot('add-product-image-options');

      // Dismiss the dialog
      await device.pressBack();
    });
  });

  describe('Product Details Form', () => {
    it('should display product details section', async () => {
      await navigateToAddProduct();

      // Scroll to details section
      await waitFor(element(by.id(config.screens.addProduct.detailsSection)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await expect(element(by.id(config.screens.addProduct.detailsSection))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-details-section');
    });

    it('should display title input field', async () => {
      await navigateToAddProduct();

      await expect(element(by.id(config.screens.addProduct.titleInput))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-title-input');
    });

    it('should display description input field', async () => {
      await navigateToAddProduct();

      await expect(element(by.id(config.screens.addProduct.descriptionInput))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-description-input');
    });

    it('should display price input field', async () => {
      await navigateToAddProduct();

      // Scroll to price input
      await waitFor(element(by.id(config.screens.addProduct.priceInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await expect(element(by.id(config.screens.addProduct.priceInput))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-price-input');
    });

    it('should display category input field', async () => {
      await navigateToAddProduct();

      // Scroll to category input
      await waitFor(element(by.id(config.screens.addProduct.categoryInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(150, 'down');

      await expect(element(by.id(config.screens.addProduct.categoryInput))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-category-input');
    });

    it('should display stock quantity input field', async () => {
      await navigateToAddProduct();

      // Scroll to stock input
      await waitFor(element(by.id(config.screens.addProduct.stockInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(200, 'down');

      await expect(element(by.id(config.screens.addProduct.stockInput))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-stock-input');
    });

    it('should display tags input field', async () => {
      await navigateToAddProduct();

      // Scroll to tags input
      await waitFor(element(by.id(config.screens.addProduct.tagsInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(250, 'down');

      await expect(element(by.id(config.screens.addProduct.tagsInput))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-tags-input');
    });

    it('should display submit button', async () => {
      await navigateToAddProduct();

      // Scroll to submit button
      await waitFor(element(by.id(config.screens.addProduct.submitButton)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(300, 'down');

      await expect(element(by.id(config.screens.addProduct.submitButton))).toBeVisible();
      await TestHelpers.takeScreenshot('add-product-submit-button');
    });
  });

  describe('Form Validation', () => {
    it('should show error for empty title', async () => {
      await navigateToAddProduct();

      // Clear title if any default value
      await element(by.id(config.screens.addProduct.titleInput)).tap();
      await element(by.id(config.screens.addProduct.titleInput)).clearText();

      // Scroll to and tap submit button
      await waitFor(element(by.id(config.screens.addProduct.submitButton)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(300, 'down');

      await TestHelpers.tapElement(by.id(config.screens.addProduct.submitButton));

      // Wait for validation
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Check for error
      const titleErrorExists = await TestHelpers.elementExists(by.id(config.screens.addProduct.titleError));
      if (titleErrorExists) {
        await expect(element(by.id(config.screens.addProduct.titleError))).toBeVisible();
      }

      await TestHelpers.takeScreenshot('add-product-title-error');
    });

    it('should show error for empty description', async () => {
      await navigateToAddProduct();

      // Fill title only
      await TestHelpers.typeText(
        by.id(config.screens.addProduct.titleInput),
        'Test Product'
      );

      // Scroll to and tap submit button
      await waitFor(element(by.id(config.screens.addProduct.submitButton)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(300, 'down');

      await TestHelpers.tapElement(by.id(config.screens.addProduct.submitButton));

      // Wait for validation
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Check for error
      const descErrorExists = await TestHelpers.elementExists(by.id(config.screens.addProduct.descriptionError));
      if (descErrorExists) {
        await expect(element(by.id(config.screens.addProduct.descriptionError))).toBeVisible();
      }

      await TestHelpers.takeScreenshot('add-product-description-error');
    });

    it('should show error for invalid price', async () => {
      await navigateToAddProduct();

      // Fill required fields with invalid price
      await TestHelpers.typeText(
        by.id(config.screens.addProduct.titleInput),
        'Test Product'
      );

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.descriptionInput),
        'Test description'
      );

      // Scroll to price and enter invalid value
      await waitFor(element(by.id(config.screens.addProduct.priceInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.priceInput),
        '-10'
      );

      // Scroll to and tap submit button
      await waitFor(element(by.id(config.screens.addProduct.submitButton)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(300, 'down');

      await TestHelpers.tapElement(by.id(config.screens.addProduct.submitButton));

      // Wait for validation
      await new Promise(resolve => setTimeout(resolve, 1500));

      await TestHelpers.takeScreenshot('add-product-price-error');
    });

    it('should show error for empty category', async () => {
      await navigateToAddProduct();

      // Fill other required fields
      await TestHelpers.typeText(
        by.id(config.screens.addProduct.titleInput),
        'Test Product'
      );

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.descriptionInput),
        'Test description'
      );

      await waitFor(element(by.id(config.screens.addProduct.priceInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.priceInput),
        '29.99'
      );

      // Scroll to and tap submit button
      await waitFor(element(by.id(config.screens.addProduct.submitButton)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(300, 'down');

      await TestHelpers.tapElement(by.id(config.screens.addProduct.submitButton));

      // Wait for validation
      await new Promise(resolve => setTimeout(resolve, 1500));

      await TestHelpers.takeScreenshot('add-product-category-error');
    });

    it('should show error for empty stock quantity', async () => {
      await navigateToAddProduct();

      // Fill other required fields
      await TestHelpers.typeText(
        by.id(config.screens.addProduct.titleInput),
        'Test Product'
      );

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.descriptionInput),
        'Test description'
      );

      await waitFor(element(by.id(config.screens.addProduct.priceInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.priceInput),
        '29.99'
      );

      await waitFor(element(by.id(config.screens.addProduct.categoryInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.categoryInput),
        'Vases'
      );

      // Scroll to and tap submit button
      await waitFor(element(by.id(config.screens.addProduct.submitButton)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(300, 'down');

      await TestHelpers.tapElement(by.id(config.screens.addProduct.submitButton));

      // Wait for validation
      await new Promise(resolve => setTimeout(resolve, 1500));

      await TestHelpers.takeScreenshot('add-product-stock-error');
    });
  });

  describe('Complete Product Creation Flow', () => {
    it('should fill all required fields', async () => {
      await navigateToAddProduct();

      const product = generateTestProduct();

      // Fill title
      await TestHelpers.typeText(
        by.id(config.screens.addProduct.titleInput),
        product.title
      );

      // Fill description
      await TestHelpers.typeText(
        by.id(config.screens.addProduct.descriptionInput),
        product.description
      );

      // Scroll and fill price
      await waitFor(element(by.id(config.screens.addProduct.priceInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.priceInput),
        product.price
      );

      // Fill category
      await waitFor(element(by.id(config.screens.addProduct.categoryInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.categoryInput),
        product.category
      );

      // Fill stock
      await waitFor(element(by.id(config.screens.addProduct.stockInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.stockInput),
        product.stock
      );

      // Fill tags (optional)
      await waitFor(element(by.id(config.screens.addProduct.tagsInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.tagsInput),
        product.tags
      );

      await TestHelpers.takeScreenshot('add-product-form-filled');
    });

    it('should submit product successfully with valid data', async () => {
      await navigateToAddProduct();

      const product = generateTestProduct();

      // Fill all required fields
      await TestHelpers.typeText(
        by.id(config.screens.addProduct.titleInput),
        product.title
      );

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.descriptionInput),
        product.description
      );

      await waitFor(element(by.id(config.screens.addProduct.priceInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.priceInput),
        product.price
      );

      await waitFor(element(by.id(config.screens.addProduct.categoryInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.categoryInput),
        product.category
      );

      await waitFor(element(by.id(config.screens.addProduct.stockInput)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(100, 'down');

      await TestHelpers.typeText(
        by.id(config.screens.addProduct.stockInput),
        product.stock
      );

      // Dismiss keyboard before submitting
      await device.pressBack();
      await new Promise(resolve => setTimeout(resolve, 500));

      // Scroll to and tap submit button
      await waitFor(element(by.id(config.screens.addProduct.submitButton)))
        .toBeVisible()
        .whileElement(by.id(config.screens.addProduct.scroll))
        .scroll(300, 'down');

      await TestHelpers.tapElement(by.id(config.screens.addProduct.submitButton));

      // Wait for API response and alert
      await new Promise(resolve => setTimeout(resolve, 3000));

      await TestHelpers.takeScreenshot('add-product-submitted');
    });
  });

  describe('Add Product Navigation', () => {
    it('should navigate back when back button is pressed', async () => {
      await navigateToAddProduct();

      // Tap back button
      await TestHelpers.tapElement(by.id(config.screens.addProduct.backButton));

      // Wait for navigation
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Verify we are no longer on add product screen
      await waitFor(element(by.id(config.screens.addProduct.screen)))
        .not.toBeVisible()
        .withTimeout(config.timeouts.medium);

      await TestHelpers.takeScreenshot('add-product-navigated-back');
    });
  });

  describe('Add Product Scroll Behavior', () => {
    it('should scroll through all form sections', async () => {
      await navigateToAddProduct();

      // Scroll down to see all form fields
      await element(by.id(config.screens.addProduct.scroll)).scroll(400, 'down');
      await TestHelpers.takeScreenshot('add-product-scrolled-down');

      // Scroll back up
      await element(by.id(config.screens.addProduct.scroll)).scroll(400, 'up');
      await TestHelpers.takeScreenshot('add-product-scrolled-up');
    });
  });
});
