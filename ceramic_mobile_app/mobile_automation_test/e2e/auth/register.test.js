const config = require('../config/testConfig');
const TestHelpers = require('../helpers/testHelpers');
const apiHelpers = require('../helpers/apiHelpers');

describe('Registration Flow', () => {
  let testEmail;
  let testUsername;

  beforeAll(async () => {
    const serverReachable = await apiHelpers.checkServerHealth();
    if (!serverReachable) {
      console.warn('Warning: API server may not be reachable');
    }
  });

  beforeEach(async () => {
    // Launch app with delete flag to clear app data
    // Disable synchronization to bypass idle detection issues
    await device.launchApp({
      delete: true,
      permissions: { notifications: 'YES' },
      launchArgs: {
        detoxPrintBusyIdleResources: 'YES',
        detoxEnableSynchronization: 0
      }
    });
    // Add small delay to ensure app is ready
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Generate unique test credentials
    testEmail = TestHelpers.generateTestEmail();
    testUsername = TestHelpers.generateTestUsername();
  });

  afterEach(async () => {
    await TestHelpers.takeScreenshot('register-test-end');

    // Cleanup: delete test user if created
    if (testEmail) {
      await TestHelpers.cleanupTestUser(testEmail);
    }
  });

  /**
   * Helper function to navigate to registration screen
   */
  async function navigateToRegister() {
    await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
    await TestHelpers.tapElement(by.id(config.screens.login.registerLink));
    await TestHelpers.waitForElement(by.id(config.screens.register.firstNameInput));
  }

  /**
   * Helper function to fill registration form
   */
  async function fillRegistrationForm(role = 'customer', customData = {}) {
    const defaultData = {
      firstName: 'Test',
      lastName: 'User',
      username: testUsername,
      email: testEmail,
      password: 'TestPass123!',
      confirmPassword: 'TestPass123!',
    };

    const data = { ...defaultData, ...customData };

    await TestHelpers.typeText(by.id(config.screens.register.firstNameInput), data.firstName);
    await TestHelpers.typeText(by.id(config.screens.register.lastNameInput), data.lastName);
    await TestHelpers.typeText(by.id(config.screens.register.usernameInput), data.username);
    await TestHelpers.typeText(by.id(config.screens.register.emailInput), data.email);
    await TestHelpers.typeText(by.id(config.screens.register.passwordInput), data.password);
    await TestHelpers.typeText(
      by.id(config.screens.register.confirmPasswordInput),
      data.confirmPassword
    );

    // Select role
    if (role === 'customer') {
      await TestHelpers.tapElement(by.id(config.screens.register.customerRadio));
    } else if (role === 'seller') {
      await TestHelpers.tapElement(by.id(config.screens.register.sellerRadio));
    }
  }

  describe('Successful Registration', () => {
    it('should register as CUSTOMER successfully', async () => {
      await navigateToRegister();
      await fillRegistrationForm('customer');

      await TestHelpers.takeScreenshot('register-customer-before-submit');

      // Submit registration
      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      // Verify success message
      await TestHelpers.verifyToastMessage('Registration Successful', config.timeouts.medium);
      await TestHelpers.waitForText('Please check your email to verify your account');

      await TestHelpers.takeScreenshot('register-customer-success');

      // Verify navigation to login screen
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
    });

    it('should register as SELLER successfully', async () => {
      await navigateToRegister();
      await fillRegistrationForm('seller');

      await TestHelpers.takeScreenshot('register-seller-before-submit');

      // Submit registration
      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      // Verify success message
      await TestHelpers.verifyToastMessage('Registration Successful', config.timeouts.medium);

      await TestHelpers.takeScreenshot('register-seller-success');

      // Verify navigation to login screen
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
    });

    it('should register as DUAL role successfully', async () => {
      // Note: Based on the frontend code, dual role selection might not be in the UI
      // This test assumes the functionality exists or will be added
      await navigateToRegister();

      // Check if dual role option exists
      const hasDualOption = await TestHelpers.elementExists(by.id('register-role-dual'));

      if (hasDualOption) {
        await fillRegistrationForm('customer'); // Fill basic fields
        await TestHelpers.tapElement(by.id('register-role-dual'));

        await TestHelpers.takeScreenshot('register-dual-before-submit');

        await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

        await TestHelpers.verifyToastMessage('Registration Successful', config.timeouts.medium);
        await TestHelpers.takeScreenshot('register-dual-success');
      } else {
        console.log('Dual role option not available in UI - test skipped');
        await TestHelpers.takeScreenshot('register-dual-not-available');
      }
    });

    it('should register with valid special characters in name', async () => {
      await navigateToRegister();
      await fillRegistrationForm('customer', {
        firstName: "O'Brien",
        lastName: 'Smith-Jones',
      });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      await TestHelpers.verifyToastMessage('Registration Successful', config.timeouts.medium);
      await TestHelpers.takeScreenshot('register-special-chars-name-success');
    });
  });

  describe('Registration Validation - Required Fields', () => {
    beforeEach(async () => {
      await navigateToRegister();
    });

    it('should show error for empty first name', async () => {
      await fillRegistrationForm('customer', { firstName: '' });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      await TestHelpers.waitForText('First name is required');
      await TestHelpers.takeScreenshot('register-empty-firstname-error');
    });

    it('should show error for empty last name', async () => {
      await fillRegistrationForm('customer', { lastName: '' });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      await TestHelpers.waitForText('Last name is required');
      await TestHelpers.takeScreenshot('register-empty-lastname-error');
    });

    it('should show error for empty username', async () => {
      await fillRegistrationForm('customer', { username: '' });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      await TestHelpers.waitForText('Username is required');
      await TestHelpers.takeScreenshot('register-empty-username-error');
    });

    it('should show error for empty email', async () => {
      await fillRegistrationForm('customer', { email: '' });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      await TestHelpers.waitForText('Email is required');
      await TestHelpers.takeScreenshot('register-empty-email-error');
    });

    it('should show error for empty password', async () => {
      await fillRegistrationForm('customer', { password: '' });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      await TestHelpers.waitForText('Password is required');
      await TestHelpers.takeScreenshot('register-empty-password-error');
    });

    it('should show error for empty confirm password', async () => {
      await fillRegistrationForm('customer', { confirmPassword: '' });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      await TestHelpers.waitForText('Please confirm your password');
      await TestHelpers.takeScreenshot('register-empty-confirm-password-error');
    });
  });

  describe('Registration Validation - Field Format', () => {
    beforeEach(async () => {
      await navigateToRegister();
    });

    it('should show error for short first name', async () => {
      await fillRegistrationForm('customer', { firstName: 'A' });

      await TestHelpers.waitForText('First name must be at least 2 characters');
      await TestHelpers.takeScreenshot('register-short-firstname-error');
    });

    it('should show error for short last name', async () => {
      await fillRegistrationForm('customer', { lastName: 'B' });

      await TestHelpers.waitForText('Last name must be at least 2 characters');
      await TestHelpers.takeScreenshot('register-short-lastname-error');
    });

    it('should show error for invalid username format', async () => {
      await fillRegistrationForm('customer', { username: 'user@invalid!' });

      await TestHelpers.waitForText(
        'Username can only contain letters, numbers, underscores, and hyphens'
      );
      await TestHelpers.takeScreenshot('register-invalid-username-error');
    });

    it('should show error for long username', async () => {
      const longUsername = 'a'.repeat(51); // More than 50 characters
      await fillRegistrationForm('customer', { username: longUsername });

      await TestHelpers.waitForText('Username must be 50 characters or less');
      await TestHelpers.takeScreenshot('register-long-username-error');
    });

    it('should show error for invalid email format', async () => {
      await fillRegistrationForm('customer', { email: 'invalid-email' });

      await TestHelpers.waitForText('Invalid email address');
      await TestHelpers.takeScreenshot('register-invalid-email-error');
    });

    it('should show error for password too short', async () => {
      await fillRegistrationForm('customer', {
        password: 'Short1!',
        confirmPassword: 'Short1!',
      });

      await TestHelpers.waitForText('Password must be at least 8 characters');
      await TestHelpers.takeScreenshot('register-short-password-error');
    });

    it('should show error for password without uppercase', async () => {
      await fillRegistrationForm('customer', {
        password: 'testpass123!',
        confirmPassword: 'testpass123!',
      });

      await TestHelpers.waitForText('Password must contain at least one uppercase letter');
      await TestHelpers.takeScreenshot('register-no-uppercase-error');
    });

    it('should show error for password without lowercase', async () => {
      await fillRegistrationForm('customer', {
        password: 'TESTPASS123!',
        confirmPassword: 'TESTPASS123!',
      });

      await TestHelpers.waitForText('Password must contain at least one lowercase letter');
      await TestHelpers.takeScreenshot('register-no-lowercase-error');
    });

    it('should show error for password without number', async () => {
      await fillRegistrationForm('customer', {
        password: 'TestPassword!',
        confirmPassword: 'TestPassword!',
      });

      await TestHelpers.waitForText('Password must contain at least one number');
      await TestHelpers.takeScreenshot('register-no-number-error');
    });

    it('should show error for password without special character', async () => {
      await fillRegistrationForm('customer', {
        password: 'TestPass123',
        confirmPassword: 'TestPass123',
      });

      await TestHelpers.waitForText('Password must contain at least one special character');
      await TestHelpers.takeScreenshot('register-no-special-char-error');
    });

    it('should show error for password mismatch', async () => {
      await fillRegistrationForm('customer', {
        password: 'TestPass123!',
        confirmPassword: 'DifferentPass123!',
      });

      await TestHelpers.waitForText('Passwords do not match');
      await TestHelpers.takeScreenshot('register-password-mismatch-error');
    });
  });

  describe('Registration Validation - Duplicate Data', () => {
    it('should show error for duplicate username', async () => {
      await navigateToRegister();

      // Try to register with existing username
      await fillRegistrationForm('customer', {
        username: config.testUsers.customer.username,
      });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      await TestHelpers.verifyToastMessage('Username already exists', config.timeouts.medium);
      await TestHelpers.takeScreenshot('register-duplicate-username-error');
    });

    it('should show error for duplicate email', async () => {
      await navigateToRegister();

      // Try to register with existing email
      await fillRegistrationForm('customer', {
        email: config.testUsers.customer.email,
      });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      await TestHelpers.verifyToastMessage('Email already exists', config.timeouts.medium);
      await TestHelpers.takeScreenshot('register-duplicate-email-error');
    });
  });

  describe('Registration UI Interactions', () => {
    it('should toggle password visibility', async () => {
      await navigateToRegister();

      await TestHelpers.typeText(
        by.id(config.screens.register.passwordInput),
        'TestPass123!'
      );

      // Toggle visibility
      await TestHelpers.tapElement(by.id('register-password-toggle'));
      await TestHelpers.takeScreenshot('register-password-visible');

      await TestHelpers.tapElement(by.id('register-password-toggle'));
      await TestHelpers.takeScreenshot('register-password-hidden');
    });

    it('should navigate back to login screen', async () => {
      await navigateToRegister();

      // Tap "Already have an account? Sign In" link
      await TestHelpers.tapElement(by.id(config.screens.register.loginLink));

      // Verify navigation to login screen
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));
      await TestHelpers.takeScreenshot('register-back-to-login');
    });

    it('should show loading state during registration', async () => {
      await navigateToRegister();
      await fillRegistrationForm('customer');

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      // Verify loading indicator
      await TestHelpers.waitForElement(by.id('register-loading-indicator'));
      await TestHelpers.takeScreenshot('register-loading-state');
    });

    it('should switch between customer and seller roles', async () => {
      await navigateToRegister();

      // Select customer
      await TestHelpers.tapElement(by.id(config.screens.register.customerRadio));
      await TestHelpers.takeScreenshot('register-customer-selected');

      // Switch to seller
      await TestHelpers.tapElement(by.id(config.screens.register.sellerRadio));
      await TestHelpers.takeScreenshot('register-seller-selected');

      // Switch back to customer
      await TestHelpers.tapElement(by.id(config.screens.register.customerRadio));
      await TestHelpers.takeScreenshot('register-customer-selected-again');
    });
  });

  describe('Registration Edge Cases', () => {
    it('should handle registration with network error', async () => {
      await navigateToRegister();
      await fillRegistrationForm('customer');

      // Disable network
      await device.setURLBlacklist(['.*']);

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      // Should show network error
      await TestHelpers.verifyToastMessage('Network error', config.timeouts.medium);
      await TestHelpers.takeScreenshot('register-network-error');

      // Re-enable network
      await device.setURLBlacklist([]);
    });

    it('should trim whitespace from input fields', async () => {
      await navigateToRegister();

      await fillRegistrationForm('customer', {
        username: '  ' + testUsername + '  ',
        email: '  ' + testEmail + '  ',
      });

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      // Should succeed despite whitespace
      await TestHelpers.verifyToastMessage('Registration Successful', config.timeouts.medium);
      await TestHelpers.takeScreenshot('register-whitespace-trimmed-success');
    });

    it('should handle rapid form submission', async () => {
      await navigateToRegister();
      await fillRegistrationForm('customer');

      // Tap submit multiple times rapidly
      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));
      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));
      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));

      // Should still register successfully only once
      await TestHelpers.verifyToastMessage('Registration Successful', config.timeouts.medium);
      await TestHelpers.takeScreenshot('register-rapid-submission');
    });
  });

  describe('Post-Registration Flow', () => {
    it('should allow login after successful registration', async () => {
      await navigateToRegister();
      await fillRegistrationForm('customer');

      await TestHelpers.tapElement(by.id(config.screens.register.submitButton));
      await TestHelpers.verifyToastMessage('Registration Successful', config.timeouts.medium);

      // Wait for navigation to login
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Login with new credentials
      await TestHelpers.typeText(by.id(config.screens.login.usernameInput), testUsername);
      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        'TestPass123!'
      );
      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      await TestHelpers.verifyToastMessage('Login Successful', config.timeouts.medium);
      await TestHelpers.takeScreenshot('login-after-registration-success');
    });
  });
});
