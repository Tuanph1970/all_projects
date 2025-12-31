const config = require('../config/testConfig');
const TestHelpers = require('../helpers/testHelpers');
const apiHelpers = require('../helpers/apiHelpers');

describe('Reset Password Flow', () => {
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
    await TestHelpers.takeScreenshot('reset-password-test-end');
  });

  describe('Forgot Password - Request Reset', () => {
    it('should send password reset email successfully', async () => {
      // Navigate to forgot password screen
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.tapElement(by.id(config.screens.login.forgotPasswordLink));

      // Wait for forgot password screen
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));

      // Enter email
      await TestHelpers.typeText(
        by.id(config.screens.forgotPassword.emailInput),
        config.testUsers.customer.email
      );

      await TestHelpers.takeScreenshot('forgot-password-before-submit');

      // Submit
      await TestHelpers.tapElement(by.id(config.screens.forgotPassword.submitButton));

      // Verify success message
      await TestHelpers.verifyToastMessage('Reset Email Sent', config.timeouts.medium);
      await TestHelpers.waitForText('Please check your email for password reset instructions');

      await TestHelpers.takeScreenshot('forgot-password-success');

      // Verify navigation back to login
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
    });

    it('should handle valid email format variations', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.tapElement(by.id(config.screens.login.forgotPasswordLink));
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));

      // Test with different valid email formats
      const validEmails = [
        'user@example.com',
        'user.name@example.co.uk',
        'user+tag@example.com',
      ];

      for (const email of validEmails) {
        await element(by.id(config.screens.forgotPassword.emailInput)).clearText();
        await TestHelpers.typeText(by.id(config.screens.forgotPassword.emailInput), email);

        await TestHelpers.tapElement(by.id(config.screens.forgotPassword.submitButton));
        await TestHelpers.waitForNetworkIdle(1000);

        await TestHelpers.takeScreenshot(`forgot-password-valid-email-${email.split('@')[0]}`);

        // Navigate back to forgot password for next test
        if (validEmails.indexOf(email) < validEmails.length - 1) {
          await TestHelpers.tapElement(by.id(config.screens.login.forgotPasswordLink));
        }
      }
    });
  });

  describe('Forgot Password - Validation', () => {
    beforeEach(async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.tapElement(by.id(config.screens.login.forgotPasswordLink));
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));
    });

    it('should show error for empty email', async () => {
      // Try to submit without entering email
      await TestHelpers.tapElement(by.id(config.screens.forgotPassword.submitButton));

      await TestHelpers.waitForText('Email is required');
      await TestHelpers.takeScreenshot('forgot-password-empty-email-error');
    });

    it('should show error for invalid email format', async () => {
      // Enter invalid email
      await TestHelpers.typeText(
        by.id(config.screens.forgotPassword.emailInput),
        'invalid-email'
      );

      await TestHelpers.waitForText('Invalid email address');
      await TestHelpers.takeScreenshot('forgot-password-invalid-email-error');
    });

    it('should show error for non-existent email', async () => {
      // Enter email that doesn't exist
      await TestHelpers.typeText(
        by.id(config.screens.forgotPassword.emailInput),
        'nonexistent@example.com'
      );

      await TestHelpers.tapElement(by.id(config.screens.forgotPassword.submitButton));

      await TestHelpers.verifyToastMessage('Email not found', config.timeouts.medium);
      await TestHelpers.takeScreenshot('forgot-password-nonexistent-email-error');
    });
  });

  describe('Forgot Password - UI Interactions', () => {
    it('should navigate back to login screen', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.tapElement(by.id(config.screens.login.forgotPasswordLink));
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));

      // Tap back button
      await TestHelpers.tapElement(by.id(config.screens.forgotPassword.backButton));

      // Verify navigation to login screen
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.takeScreenshot('forgot-password-back-to-login');
    });

    it('should show loading state during submission', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.tapElement(by.id(config.screens.login.forgotPasswordLink));
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));

      await TestHelpers.typeText(
        by.id(config.screens.forgotPassword.emailInput),
        config.testUsers.customer.email
      );

      await TestHelpers.tapElement(by.id(config.screens.forgotPassword.submitButton));

      // Verify loading indicator
      await TestHelpers.waitForElement(by.id('forgot-password-loading-indicator'));
      await TestHelpers.takeScreenshot('forgot-password-loading-state');
    });
  });

  describe('Reset Password - With Token', () => {
    it('should reset password successfully with valid token', async () => {
      // First, request password reset
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.tapElement(by.id(config.screens.login.forgotPasswordLink));
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));

      await TestHelpers.typeText(
        by.id(config.screens.forgotPassword.emailInput),
        config.testUsers.customer.email
      );
      await TestHelpers.tapElement(by.id(config.screens.forgotPassword.submitButton));

      // Wait for success
      await TestHelpers.verifyToastMessage('Reset Email Sent', config.timeouts.medium);

      // Get reset token (in real testing, you'd get this from email service)
      const resetToken = await apiHelpers.getResetTokenFromEmail(
        config.testUsers.customer.email
      );

      // Navigate to reset password screen with token
      await device.openURL({
        url: `ceramicapp://reset-password?token=${resetToken}`,
      });

      // Wait for reset password screen
      await TestHelpers.waitForElement(by.id(config.screens.resetPassword.passwordInput));

      const newPassword = 'NewResetPass123!';

      // Enter new password
      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.passwordInput),
        newPassword
      );

      // Confirm new password
      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.confirmPasswordInput),
        newPassword
      );

      await TestHelpers.takeScreenshot('reset-password-before-submit');

      // Submit
      await TestHelpers.tapElement(by.id(config.screens.resetPassword.submitButton));

      // Verify success
      await TestHelpers.verifyToastMessage('Password Reset Successful', config.timeouts.medium);
      await TestHelpers.takeScreenshot('reset-password-success');

      // Verify navigation to login
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Verify can login with new password
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
      await TestHelpers.takeScreenshot('login-with-reset-password-success');
    });

    it('should show error for expired or invalid token', async () => {
      // Navigate with invalid token
      await device.openURL({
        url: 'ceramicapp://reset-password?token=invalid-token-12345',
      });

      // Should show error and redirect
      await TestHelpers.verifyToastMessage('Invalid Reset Link', config.timeouts.medium);
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));

      await TestHelpers.takeScreenshot('reset-password-invalid-token-error');
    });

    it('should show error for missing token', async () => {
      // Navigate without token
      await device.openURL({
        url: 'ceramicapp://reset-password',
      });

      // Should show error and redirect
      await TestHelpers.verifyToastMessage('Invalid Reset Link', config.timeouts.medium);
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));

      await TestHelpers.takeScreenshot('reset-password-missing-token-error');
    });
  });

  describe('Reset Password - Validation', () => {
    beforeEach(async () => {
      // Get a valid reset token
      const resetToken = 'test-valid-token'; // In real tests, get from API
      await device.openURL({
        url: `ceramicapp://reset-password?token=${resetToken}`,
      });
      await TestHelpers.waitForElement(by.id(config.screens.resetPassword.passwordInput));
    });

    it('should show error for empty password', async () => {
      await TestHelpers.tapElement(by.id(config.screens.resetPassword.submitButton));

      await TestHelpers.waitForText('Password is required');
      await TestHelpers.takeScreenshot('reset-password-empty-password-error');
    });

    it('should show error for password mismatch', async () => {
      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.passwordInput),
        'NewTestPass123!'
      );
      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.confirmPasswordInput),
        'DifferentPass123!'
      );

      await TestHelpers.tapElement(by.id(config.screens.resetPassword.submitButton));

      await TestHelpers.waitForText('Passwords do not match');
      await TestHelpers.takeScreenshot('reset-password-mismatch-error');
    });

    it('should show error for weak password', async () => {
      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.passwordInput),
        'weak'
      );

      await TestHelpers.waitForText('Password must be at least 8 characters');
      await TestHelpers.takeScreenshot('reset-password-weak-password-error');
    });

    it('should show error for password without uppercase', async () => {
      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.passwordInput),
        'testpass123'
      );

      await TestHelpers.waitForText('Password must contain at least one uppercase letter');
      await TestHelpers.takeScreenshot('reset-password-no-uppercase-error');
    });

    it('should show error for password without number', async () => {
      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.passwordInput),
        'TestPassword'
      );

      await TestHelpers.waitForText('Password must contain at least one number');
      await TestHelpers.takeScreenshot('reset-password-no-number-error');
    });
  });

  describe('Reset Password - UI Interactions', () => {
    it('should toggle password visibility', async () => {
      const resetToken = 'test-valid-token';
      await device.openURL({
        url: `ceramicapp://reset-password?token=${resetToken}`,
      });
      await TestHelpers.waitForElement(by.id(config.screens.resetPassword.passwordInput));

      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.passwordInput),
        'NewTestPass123!'
      );

      // Toggle visibility
      await TestHelpers.tapElement(by.id('reset-password-toggle'));
      await TestHelpers.takeScreenshot('reset-password-visible');

      await TestHelpers.tapElement(by.id('reset-password-toggle'));
      await TestHelpers.takeScreenshot('reset-password-hidden');
    });

    it('should navigate back to login', async () => {
      const resetToken = 'test-valid-token';
      await device.openURL({
        url: `ceramicapp://reset-password?token=${resetToken}`,
      });
      await TestHelpers.waitForElement(by.id(config.screens.resetPassword.passwordInput));

      // Tap back button
      await TestHelpers.tapElement(by.id(config.screens.resetPassword.backButton));

      // Verify navigation to login
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.takeScreenshot('reset-password-back-to-login');
    });
  });

  describe('Reset Password - Edge Cases', () => {
    it('should prevent reuse of reset token', async () => {
      // This test requires full flow implementation
      // Request reset, use token, then try to use same token again
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.tapElement(by.id(config.screens.login.forgotPasswordLink));
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));

      await TestHelpers.typeText(
        by.id(config.screens.forgotPassword.emailInput),
        config.testUsers.customer.email
      );
      await TestHelpers.tapElement(by.id(config.screens.forgotPassword.submitButton));

      // Get token and use it
      const resetToken = await apiHelpers.getResetTokenFromEmail(
        config.testUsers.customer.email
      );

      // First use - should succeed
      await device.openURL({
        url: `ceramicapp://reset-password?token=${resetToken}`,
      });
      await TestHelpers.waitForElement(by.id(config.screens.resetPassword.passwordInput));

      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.passwordInput),
        'NewTestPass123!'
      );
      await TestHelpers.typeText(
        by.id(config.screens.resetPassword.confirmPasswordInput),
        'NewTestPass123!'
      );
      await TestHelpers.tapElement(by.id(config.screens.resetPassword.submitButton));

      await TestHelpers.verifyToastMessage('Password Reset Successful', config.timeouts.medium);

      // Try to reuse same token - should fail
      await device.openURL({
        url: `ceramicapp://reset-password?token=${resetToken}`,
      });

      await TestHelpers.verifyToastMessage('Invalid Reset Link', config.timeouts.medium);
      await TestHelpers.takeScreenshot('reset-password-token-reuse-error');
    });
  });
});
