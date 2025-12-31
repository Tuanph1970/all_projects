const config = require('../config/testConfig');
const TestHelpers = require('../helpers/testHelpers');
const apiHelpers = require('../helpers/apiHelpers');

describe('Change Password Flow', () => {
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
    await TestHelpers.takeScreenshot('change-password-test-end');
  });

  /**
   * Helper function to login and navigate to change password screen
   */
  async function navigateToChangePassword(user = config.testUsers.customer) {
    // Login
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
    await TestHelpers.verifyToastMessage('Login Successful', config.timeouts.medium);

    // Navigate to profile
    await TestHelpers.tapElement(by.id('profile-tab'));
    await TestHelpers.waitForElement(by.id(config.screens.profile.changePasswordButton));

    // Navigate to change password screen
    await TestHelpers.tapElement(by.id(config.screens.profile.changePasswordButton));
    await TestHelpers.waitForElement(by.id(config.screens.changePassword.currentPasswordInput));
  }

  describe('Successful Password Change', () => {
    it('should change password successfully with valid inputs', async () => {
      await navigateToChangePassword();

      const currentPassword = config.testUsers.customer.password;
      const newPassword = 'NewTestPass123!';

      // Enter current password
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        currentPassword
      );

      // Enter new password
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        newPassword
      );

      // Confirm new password
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.confirmPasswordInput),
        newPassword
      );

      await TestHelpers.takeScreenshot('change-password-before-submit');

      // Submit
      await TestHelpers.tapElement(by.id(config.screens.changePassword.submitButton));

      // Verify success message
      await TestHelpers.verifyToastMessage(
        'Password Changed Successfully',
        config.timeouts.medium
      );

      await TestHelpers.takeScreenshot('change-password-success');

      // Verify can login with new password
      // Logout first
      await TestHelpers.tapElement(by.id(config.screens.profile.logoutButton));
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Login with new password
      await TestHelpers.typeText(
        by.id(config.screens.login.usernameInput),
        config.testUsers.customer.username
      );
      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        newPassword
      );
      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      await TestHelpers.verifyToastMessage('Login Successful', config.timeouts.medium);
      await TestHelpers.takeScreenshot('login-with-new-password-success');

      // Change password back to original for other tests
      await navigateToChangePassword();
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        newPassword
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        currentPassword
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.confirmPasswordInput),
        currentPassword
      );
      await TestHelpers.tapElement(by.id(config.screens.changePassword.submitButton));
    });
  });

  describe('Password Change Validation', () => {
    it('should show error for empty current password', async () => {
      await navigateToChangePassword();

      // Leave current password empty
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        'NewTestPass123!'
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.confirmPasswordInput),
        'NewTestPass123!'
      );

      await TestHelpers.tapElement(by.id(config.screens.changePassword.submitButton));

      await TestHelpers.waitForText('Current password is required');
      await TestHelpers.takeScreenshot('change-password-empty-current-error');
    });

    it('should show error for empty new password', async () => {
      await navigateToChangePassword();

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        config.testUsers.customer.password
      );

      // Leave new password empty
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.confirmPasswordInput),
        'NewTestPass123!'
      );

      await TestHelpers.tapElement(by.id(config.screens.changePassword.submitButton));

      await TestHelpers.waitForText('New password is required');
      await TestHelpers.takeScreenshot('change-password-empty-new-error');
    });

    it('should show error for password mismatch', async () => {
      await navigateToChangePassword();

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        config.testUsers.customer.password
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        'NewTestPass123!'
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.confirmPasswordInput),
        'DifferentPass123!'
      );

      await TestHelpers.tapElement(by.id(config.screens.changePassword.submitButton));

      await TestHelpers.waitForText('Passwords do not match');
      await TestHelpers.takeScreenshot('change-password-mismatch-error');
    });

    it('should show error for incorrect current password', async () => {
      await navigateToChangePassword();

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        'WrongPassword123!'
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        'NewTestPass123!'
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.confirmPasswordInput),
        'NewTestPass123!'
      );

      await TestHelpers.tapElement(by.id(config.screens.changePassword.submitButton));

      await TestHelpers.verifyToastMessage('Incorrect current password', config.timeouts.medium);
      await TestHelpers.takeScreenshot('change-password-incorrect-current-error');
    });

    it('should show error for weak new password', async () => {
      await navigateToChangePassword();

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        config.testUsers.customer.password
      );

      // Enter weak password (less than 8 characters)
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        'weak'
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.confirmPasswordInput),
        'weak'
      );

      await TestHelpers.waitForText('Password must be at least 8 characters');
      await TestHelpers.takeScreenshot('change-password-weak-password-error');
    });

    it('should show error for new password without uppercase', async () => {
      await navigateToChangePassword();

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        config.testUsers.customer.password
      );

      // Password without uppercase
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        'testpass123!'
      );

      await TestHelpers.waitForText('Password must contain at least one uppercase letter');
      await TestHelpers.takeScreenshot('change-password-no-uppercase-error');
    });

    it('should show error for new password without number', async () => {
      await navigateToChangePassword();

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        config.testUsers.customer.password
      );

      // Password without number
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        'TestPassword!'
      );

      await TestHelpers.waitForText('Password must contain at least one number');
      await TestHelpers.takeScreenshot('change-password-no-number-error');
    });
  });

  describe('Password Change UI Interactions', () => {
    it('should toggle current password visibility', async () => {
      await navigateToChangePassword();

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        config.testUsers.customer.password
      );

      // Toggle visibility
      await TestHelpers.tapElement(by.id('change-password-current-toggle'));
      await TestHelpers.takeScreenshot('change-password-current-visible');

      await TestHelpers.tapElement(by.id('change-password-current-toggle'));
      await TestHelpers.takeScreenshot('change-password-current-hidden');
    });

    it('should toggle new password visibility', async () => {
      await navigateToChangePassword();

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        'NewTestPass123!'
      );

      // Toggle visibility
      await TestHelpers.tapElement(by.id('change-password-new-toggle'));
      await TestHelpers.takeScreenshot('change-password-new-visible');

      await TestHelpers.tapElement(by.id('change-password-new-toggle'));
      await TestHelpers.takeScreenshot('change-password-new-hidden');
    });

    it('should navigate back without changing password', async () => {
      await navigateToChangePassword();

      // Enter some data
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        config.testUsers.customer.password
      );

      // Navigate back
      await device.pressBack(); // For Android
      // For iOS, use: await TestHelpers.tapElement(by.id('back-button'));

      // Verify back on profile screen
      await TestHelpers.waitForElement(by.id(config.screens.profile.changePasswordButton));
      await TestHelpers.takeScreenshot('change-password-navigated-back');
    });
  });

  describe('Password Change Edge Cases', () => {
    it('should handle password change when server is slow', async () => {
      await navigateToChangePassword();

      const newPassword = 'NewTestPass123!';

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        config.testUsers.customer.password
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        newPassword
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.confirmPasswordInput),
        newPassword
      );

      await TestHelpers.tapElement(by.id(config.screens.changePassword.submitButton));

      // Verify loading state appears
      await TestHelpers.waitForElement(by.id('change-password-loading-indicator'));
      await TestHelpers.takeScreenshot('change-password-loading-state');

      // Wait for completion
      await TestHelpers.verifyToastMessage(
        'Password Changed Successfully',
        config.timeouts.extraLong
      );
    });

    it('should handle same password as new password', async () => {
      await navigateToChangePassword();

      const currentPassword = config.testUsers.customer.password;

      await TestHelpers.typeText(
        by.id(config.screens.changePassword.currentPasswordInput),
        currentPassword
      );

      // Use same password as new password
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.newPasswordInput),
        currentPassword
      );
      await TestHelpers.typeText(
        by.id(config.screens.changePassword.confirmPasswordInput),
        currentPassword
      );

      await TestHelpers.tapElement(by.id(config.screens.changePassword.submitButton));

      // Should show error (if implemented) or succeed
      const hasError = await TestHelpers.elementExists(
        by.text('New password must be different from current password')
      );

      await TestHelpers.takeScreenshot(
        hasError ? 'change-password-same-password-error' : 'change-password-same-password-success'
      );
    });
  });
});
