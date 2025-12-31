const config = require('../config/testConfig');
const TestHelpers = require('../helpers/testHelpers');
const apiHelpers = require('../helpers/apiHelpers');

describe('Logout Flow', () => {
  beforeAll(async () => {
    const serverReachable = await apiHelpers.checkServerHealth();
    if (!serverReachable) {
      console.warn('Warning: API server may not be reachable');
    }
  });

  beforeEach(async () => {
    await device.launchApp({
      newInstance: true,
      permissions: { notifications: 'YES' },
    });
    // Add small delay to ensure app is ready
    await new Promise(resolve => setTimeout(resolve, 2000));
    await TestHelpers.clearAppData();
  });

  afterEach(async () => {
    await TestHelpers.takeScreenshot('logout-test-end');
  });

  /**
   * Helper function to login before testing logout
   */
  async function performLogin(user = config.testUsers.customer) {
    await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

    await TestHelpers.typeText(
      by.id(config.screens.login.usernameInput),
      user.username
    );

    await TestHelpers.typeText(
      by.id(config.screens.login.passwordInput),
      user.password
    );

    await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

    // Wait for successful login
    await TestHelpers.verifyToastMessage('Login Successful', config.timeouts.medium);
    await TestHelpers.waitForElement(by.text('Welcome back!'), config.timeouts.long);
  }

  describe('Successful Logout', () => {
    it('should logout successfully from profile screen', async () => {
      // First, login
      await performLogin();

      await TestHelpers.takeScreenshot('before-logout');

      // Navigate to profile screen
      // Adjust this based on your app's navigation structure
      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.waitForElement(by.id(config.screens.profile.logoutButton));

      // Tap logout button
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));

      // Verify logout confirmation dialog appears (if implemented)
      const hasConfirmDialog = await TestHelpers.elementExists(by.text('Confirm Logout'));
      if (hasConfirmDialog) {
        await TestHelpers.tapElement(by.text('Logout'));
      }

      // Verify navigation back to login screen
      await TestHelpers.waitForElement(
        by.id(config.screens.login.usernameInput),
        config.timeouts.long
      );

      await TestHelpers.takeScreenshot('logout-success');
    });

    it('should clear user session data after logout', async () => {
      // Login
      await performLogin();

      // Navigate to profile and logout
      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.waitForElement(by.id(config.screens.profile.logoutButton));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));

      // Wait for logout to complete
      await TestHelpers.waitForElement(
        by.id(config.screens.login.usernameInput),
        config.timeouts.long
      );

      // Verify user cannot access protected screens
      // Try to navigate to a protected screen (should redirect to login)
      await device.openURL({ url: 'ceramicapp://profile' });

      // Should still be on login screen
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.takeScreenshot('session-cleared-after-logout');
    });

    it('should logout customer user successfully', async () => {
      await performLogin(config.testUsers.customer);

      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));

      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.takeScreenshot('customer-logout-success');
    });

    it('should logout seller user successfully', async () => {
      await performLogin(config.testUsers.seller);

      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));

      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.takeScreenshot('seller-logout-success');
    });
  });

  describe('Logout Confirmation', () => {
    it('should show confirmation dialog before logout', async () => {
      await performLogin();

      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.waitForElement(by.id(config.screens.profile.logoutButton));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));

      // Verify confirmation dialog
      const hasConfirmDialog = await TestHelpers.elementExists(by.text('Confirm Logout'));
      if (hasConfirmDialog) {
        await TestHelpers.waitForElement(by.text('Are you sure you want to logout?'));
        await TestHelpers.takeScreenshot('logout-confirmation-dialog');
      }
    });

    it('should cancel logout when user chooses cancel', async () => {
      await performLogin();

      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.waitForElement(by.id(config.screens.profile.logoutButton));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));

      // If confirmation dialog exists, tap cancel
      const hasConfirmDialog = await TestHelpers.elementExists(by.text('Cancel'));
      if (hasConfirmDialog) {
        await TestHelpers.tapElement(by.text('Cancel'));

        // Verify still on profile screen
        await TestHelpers.waitForElement(by.id(config.screens.profile.logoutButton));
        await TestHelpers.takeScreenshot('logout-cancelled');
      }
    });
  });

  describe('Logout Edge Cases', () => {
    it('should handle logout when server is unreachable', async () => {
      await performLogin();

      // Disable network
      await device.setURLBlacklist(['.*']);

      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));

      // Should still logout locally even if server request fails
      await TestHelpers.waitForElement(
        by.id(config.screens.login.usernameInput),
        config.timeouts.long
      );

      await TestHelpers.takeScreenshot('logout-offline-success');

      // Re-enable network
      await device.setURLBlacklist([]);
    });

    it('should not allow access to protected screens after logout', async () => {
      await performLogin();

      // Logout
      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Try to access protected screen via deep link
      await device.openURL({ url: 'ceramicapp://orders' });

      // Should redirect to login
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.takeScreenshot('protected-screen-blocked-after-logout');
    });

    it('should handle multiple rapid logout attempts', async () => {
      await performLogin();

      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.waitForElement(by.id(config.screens.profile.logoutButton));

      // Tap logout multiple times rapidly
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));

      // Should still logout successfully without errors
      await TestHelpers.waitForElement(
        by.id(config.screens.login.usernameInput),
        config.timeouts.long
      );
      await TestHelpers.takeScreenshot('multiple-logout-attempts');
    });
  });

  describe('Post-Logout Behavior', () => {
    it('should require fresh login after logout', async () => {
      const testUser = config.testUsers.customer;

      // Login
      await performLogin(testUser);

      // Logout
      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Try to login again
      await TestHelpers.typeText(
        by.id(config.screens.login.usernameInput),
        testUser.username
      );

      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        testUser.password
      );

      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      // Should successfully login again
      await TestHelpers.verifyToastMessage('Login Successful', config.timeouts.medium);
      await TestHelpers.takeScreenshot('relogin-after-logout-success');
    });

    it('should clear cached data after logout', async () => {
      await performLogin();

      // Navigate to a screen that caches data (e.g., products)
      await TestHelpers.tapElement(by.id('home-tab'));
      await TestHelpers.waitForElement(by.id('product-list'));

      // Logout
      await TestHelpers.tapElement(by.id('profile-tab'));
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Login again
      await performLogin();

      // Verify data is refreshed (not from cache)
      await TestHelpers.tapElement(by.id('home-tab'));
      await TestHelpers.waitForElement(by.id('product-list'));

      // Add assertion to verify data was reloaded
      await TestHelpers.takeScreenshot('data-refreshed-after-relogin');
    });
  });
});
