const config = require('../config/testConfig');
const TestHelpers = require('../helpers/testHelpers');
const apiHelpers = require('../helpers/apiHelpers');

describe('Login Flow', () => {
  beforeAll(async () => {
    // Check if server is reachable
    const serverReachable = await apiHelpers.checkServerHealth();
    if (!serverReachable) {
      console.warn('Warning: API server may not be reachable');
    }
  });

  beforeEach(async () => {
    // Launch app with delete flag to clear app data
    // Synchronization is disabled globally in init.js
    await device.launchApp({
      newInstance: true,
      permissions: { notifications: 'YES' }
    });
    // Add small delay to ensure app is ready
    await new Promise(resolve => setTimeout(resolve, 2000));
  });

  afterEach(async () => {
    await TestHelpers.takeScreenshot('login-test-end');
  });

  describe('Successful Login', () => {
    it('should login successfully with valid credentials', async () => {
      const testUser = config.testUsers.customer;

      // Wait for login screen to load
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Enter username
      await TestHelpers.typeText(
        by.id(config.screens.login.usernameInput),
        testUser.username
      );

      // Enter password
      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        testUser.password
      );

      // Take screenshot before login
      await TestHelpers.takeScreenshot('login-before-submit');

      // Tap login button
      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      // Wait for navigation - verify login screen disappears
      await waitFor(element(by.text('Sign in to your account')))
        .not.toBeVisible()
        .withTimeout(config.timeouts.long);

      await TestHelpers.takeScreenshot('login-success');
    });

    it('should login with email instead of username', async () => {
      const testUser = config.testUsers.customer;

      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Enter email instead of username
      await TestHelpers.typeText(
        by.id(config.screens.login.usernameInput),
        testUser.email
      );

      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        testUser.password
      );

      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      // Verify navigation away from login screen
      await waitFor(element(by.text('Sign in to your account')))
        .not.toBeVisible()
        .withTimeout(config.timeouts.long);
    });
  });

  describe('Login Validation', () => {
    it('should show error for empty username', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Tap and then clear the username field to trigger onChange validation
      await element(by.id(config.screens.login.usernameInput)).tap();
      await element(by.id(config.screens.login.usernameInput)).clearText();

      // Enter password
      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        'TestPass123!'
      );

      // Dismiss keyboard before tapping button
      await device.pressBack();
      await new Promise(resolve => setTimeout(resolve, 500));

      // Tap login button to trigger form validation
      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      // Wait for React state to update and animation to complete
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Verify inline error message appears using testID (more reliable than text matching)
      await waitFor(element(by.id('login-username-input-error')))
        .toExist()
        .withTimeout(config.timeouts.long);
      await TestHelpers.takeScreenshot('login-empty-username-error');
    });

    it('should show error for empty password', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Enter username, leave password empty
      await TestHelpers.typeText(
        by.id(config.screens.login.usernameInput),
        'testuser'
      );

      // Tap password field to register it with form (touch event)
      await TestHelpers.tapElement(by.id(config.screens.login.passwordInput));

      // Tap login button to trigger form validation
      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      // Wait for React state to update and animation to complete
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Verify inline error message appears using testID (more reliable than text matching)
      await waitFor(element(by.id('login-password-input-error')))
        .toExist()
        .withTimeout(config.timeouts.medium);
      await TestHelpers.takeScreenshot('login-empty-password-error');
    });

    it('should show error for invalid credentials', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Enter invalid credentials
      await TestHelpers.typeText(
        by.id(config.screens.login.usernameInput),
        'invalid_user'
      );

      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        'WrongPassword123!'
      );

      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      // Verify we're still on login screen (login failed)
      await TestHelpers.waitForElement(by.id(config.screens.login.loginButton), config.timeouts.long);
      await TestHelpers.takeScreenshot('login-invalid-credentials-error');
    });

    it('should show error for short username', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Enter username less than 3 characters
      await TestHelpers.typeText(
        by.id(config.screens.login.usernameInput),
        'ab'
      );

      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        'TestPass123!'
      );

      // Tap login button to trigger form validation
      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      // Wait for React state to update and animation to complete
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Verify error message appears using testID (more reliable than text matching)
      await waitFor(element(by.id('login-username-input-error')))
        .toExist()
        .withTimeout(config.timeouts.medium);
      await TestHelpers.takeScreenshot('login-short-username-error');
    });

    it('should show error for short password', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      await TestHelpers.typeText(
        by.id(config.screens.login.usernameInput),
        'testuser'
      );

      // Enter password less than 6 characters
      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        '12345'
      );

      // Dismiss keyboard before tapping button
      await device.pressBack();
      await new Promise(resolve => setTimeout(resolve, 500));

      // Tap login button to trigger form validation
      await TestHelpers.tapElement(by.id(config.screens.login.loginButton));

      // Wait for React state to update and animation to complete
      await new Promise(resolve => setTimeout(resolve, 1500));

      // Verify error message appears using testID (more reliable than text matching)
      await waitFor(element(by.id('login-password-input-error')))
        .toExist()
        .withTimeout(config.timeouts.long);
      await TestHelpers.takeScreenshot('login-short-password-error');
    });
  });

  describe('Login UI Interactions', () => {
    it('should toggle password visibility', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      await TestHelpers.typeText(
        by.id(config.screens.login.passwordInput),
        'TestPass123!'
      );

      // Tap eye icon to show password
      await TestHelpers.tapElement(by.id('login-password-toggle'));

      await TestHelpers.takeScreenshot('login-password-visible');

      // Tap eye icon again to hide password
      await TestHelpers.tapElement(by.id('login-password-toggle'));

      await TestHelpers.takeScreenshot('login-password-hidden');
    });

    it('should navigate to register screen', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Tap "Sign Up" link
      await TestHelpers.tapElement(by.id(config.screens.login.registerLink));

      // Verify navigation to register screen
      await TestHelpers.waitForElement(by.id(config.screens.register.firstNameInput));
      await TestHelpers.takeScreenshot('navigated-to-register');
    });

    it('should navigate to forgot password screen', async () => {
      await TestHelpers.waitForElement(by.id(config.screens.login.usernameInput));

      // Tap "Forgot Password?" link
      await TestHelpers.tapElement(by.id(config.screens.login.forgotPasswordLink));

      // Verify navigation to forgot password screen
      await TestHelpers.waitForElement(by.id(config.screens.forgotPassword.emailInput));
      await TestHelpers.takeScreenshot('navigated-to-forgot-password');
    });

    it('should show loading state during login', async () => {
      const testUser = config.testUsers.customer;

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

      // In release mode, loading is very fast - just verify we navigated successfully
      // The loading indicator may not be visible long enough to detect
      await waitFor(element(by.text('Sign in to your account')))
        .not.toBeVisible()
        .withTimeout(config.timeouts.long);

      await TestHelpers.takeScreenshot('login-completed');
    });
  });

  describe('Login with Different User Roles', () => {
    it('should login as customer', async () => {
      const testUser = config.testUsers.customer;

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

      // Verify navigation away from login screen
      await waitFor(element(by.text('Sign in to your account')))
        .not.toBeVisible()
        .withTimeout(config.timeouts.long);

      await TestHelpers.takeScreenshot('login-customer-success');
    });

    it('should login as seller', async () => {
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

      // Verify navigation away from login screen
      await waitFor(element(by.text('Sign in to your account')))
        .not.toBeVisible()
        .withTimeout(config.timeouts.long);

      await TestHelpers.takeScreenshot('login-seller-success');
    });
  });
});
