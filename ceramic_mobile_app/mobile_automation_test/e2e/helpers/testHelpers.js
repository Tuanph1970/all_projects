const axios = require('axios');
const config = require('../config/testConfig');

class TestHelpers {
  /**
   * Wait for an element to be visible
   */
  static async waitForElement(elementMatcher, timeout = config.timeouts.medium) {
    await waitFor(element(elementMatcher))
      .toBeVisible()
      .withTimeout(timeout);
  }

  /**
   * Type text into an input field
   */
  static async typeText(elementMatcher, text) {
    await element(elementMatcher).clearText();
    await element(elementMatcher).typeText(text);
  }

  /**
   * Tap on an element
   */
  static async tapElement(elementMatcher) {
    await element(elementMatcher).tap();
  }

  /**
   * Scroll to an element
   */
  static async scrollToElement(elementMatcher, scrollViewMatcher) {
    await waitFor(element(elementMatcher))
      .toBeVisible()
      .whileElement(scrollViewMatcher)
      .scroll(100, 'down');
  }

  /**
   * Wait for a specific text to appear
   */
  static async waitForText(text, timeout = config.timeouts.medium) {
    await waitFor(element(by.text(text)))
      .toBeVisible()
      .withTimeout(timeout);
  }

  /**
   * Check if element exists
   */
  static async elementExists(elementMatcher) {
    try {
      await expect(element(elementMatcher)).toExist();
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Take a screenshot
   */
  static async takeScreenshot(name) {
    await device.takeScreenshot(name);
  }

  /**
   * Reload the app
   */
  static async reloadApp() {
    await device.reloadReactNative();
  }

  /**
   * Generate random string
   */
  static generateRandomString(length = 8) {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  /**
   * Generate test email
   */
  static generateTestEmail() {
    const timestamp = Date.now();
    const random = this.generateRandomString(6);
    return `test_${random}_${timestamp}@example.com`;
  }

  /**
   * Generate test username
   */
  static generateTestUsername() {
    const timestamp = Date.now();
    const random = this.generateRandomString(6);
    return `test_${random}_${timestamp}`;
  }

  /**
   * Clean up test user via API
   */
  static async cleanupTestUser(email) {
    try {
      await axios.delete(`${config.api.baseUrl}/api/v1/test/users`, {
        data: { email },
        timeout: config.api.timeout,
      });
    } catch (error) {
      console.warn('Failed to cleanup test user:', error.message);
    }
  }

  /**
   * Wait for network idle
   */
  static async waitForNetworkIdle(timeout = config.timeouts.medium) {
    await new Promise(resolve => setTimeout(resolve, timeout));
  }

  /**
   * Dismiss keyboard
   */
  static async dismissKeyboard() {
    if (device.getPlatform() === 'ios') {
      await element(by.type('_UIBackdropView')).tap();
    } else {
      await device.pressBack();
    }
  }

  /**
   * Verify toast message appears
   * @param {string} message - Toast message text (can be text1 or partial match)
   * @param {number} timeout - Timeout in milliseconds
   * @param {string} type - Toast type: 'success' or 'error' (defaults to auto-detect)
   */
  static async verifyToastMessage(message, timeout = config.timeouts.medium, type = null) {
    // Auto-detect type based on common success/failure keywords if not specified
    if (!type) {
      const lowerMessage = message.toLowerCase();
      if (lowerMessage.includes('success') || lowerMessage.includes('welcome')) {
        type = 'success';
      } else if (lowerMessage.includes('fail') || lowerMessage.includes('error') || lowerMessage.includes('incorrect')) {
        type = 'error';
      }
    }

    // If we can detect type, use testID for more reliable detection
    if (type) {
      const testID = type === 'success' ? 'toast-success' : 'toast-error';
      await waitFor(element(by.id(testID)))
        .toBeVisible()
        .withTimeout(timeout);
    } else {
      // Fallback to text-based detection if type cannot be determined
      await waitFor(element(by.text(message)))
        .toBeVisible()
        .withTimeout(timeout);
    }
  }

  /**
   * Wait and tap element
   */
  static async waitAndTap(elementMatcher, timeout = config.timeouts.medium) {
    await this.waitForElement(elementMatcher, timeout);
    await this.tapElement(elementMatcher);
  }

  /**
   * Clear app data and restart
   */
  static async clearAppData() {
    await device.clearKeychain();
    await device.reloadReactNative();
  }
}

module.exports = TestHelpers;
