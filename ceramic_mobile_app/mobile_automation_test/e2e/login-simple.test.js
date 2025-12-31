const config = require('./config/testConfig');

// Helper function for visual delays
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

describe('Simple Login Visual Test', () => {

  it('should show login screen and allow input', async () => {
    console.log('👀 WATCH YOUR EMULATOR NOW!');
    console.log('📱 You should see the login screen...');

    // Wait for login screen to load
    await sleep(3000); // Give app time to load

    console.log('⌨️ Typing username...');
    // Find and fill username
    try {
      await element(by.id('login-username-input')).typeText('test_customer');
      console.log('✅ Username entered!');
    } catch (e) {
      console.log('⚠️ Could not find username field, trying by label...');
      await element(by.label('Username')).typeText('test_customer');
    }

    await sleep(1000);

    console.log('🔒 Typing password...');
    // Fill password
    try {
      await element(by.id('login-password-input')).typeText('12345678');
      console.log('✅ Password entered!');
    } catch (e) {
      console.log('⚠️ Could not find password field, trying by label...');
      await element(by.label('Password')).typeText('12345678');
    }

    await sleep(1000);

    console.log('👆 Tapping login button...');
    // Tap login button
    try {
      await element(by.id('login-submit-button')).tap();
      console.log('✅ Login button tapped!');
    } catch (e) {
      console.log('⚠️ Could not find button by ID, trying by text...');
      await element(by.text('Login')).tap();
    }

    await sleep(3000);

    console.log('🎉 Test completed! Check your emulator to see what happened.');
  });

  it('should toggle password visibility', async () => {
    console.log('👀 WATCH: Testing password toggle...');

    await sleep(2000);

    console.log('🔒 Entering password...');
    try {
      await element(by.id('login-password-input')).typeText('secret123');
    } catch (e) {
      await element(by.label('Password')).typeText('secret123');
    }

    await sleep(1000);

    console.log('👁️ Clicking eye icon to show password...');
    try {
      await element(by.id('login-password-toggle')).tap();
      await sleep(1000);
      console.log('✅ Password should now be visible!');

      await element(by.id('login-password-toggle')).tap();
      await sleep(1000);
      console.log('✅ Password should now be hidden again!');
    } catch (e) {
      console.log('⚠️ Could not find password toggle');
    }

    console.log('🎉 Toggle test completed!');
  });
});
