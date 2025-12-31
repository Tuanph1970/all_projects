# testID Integration Guide

This guide shows you how to add `testID` props to your React Native components to make them testable with Detox.

## Why testID?

Detox uses `testID` to reliably identify and interact with UI elements during automated testing. Unlike text-based selectors, `testID` values:

- Are stable across different languages/locales
- Don't break when UI text changes
- Provide consistent element identification
- Work the same on iOS and Android

## Quick Reference

### Required testIDs for Authentication Screens

Below are the testIDs referenced in the test files. Add these to your React Native components:

## Login Screen (`LoginScreen.jsx`)

```jsx
// Username/Email Input
<Input
  testID="login-username-input"
  label="Username or Email"
  // ... other props
/>

// Password Input
<Input
  testID="login-password-input"
  label="Password"
  secureTextEntry={!showPassword}
  // ... other props
/>

// Password Toggle Icon
<TextInput.Icon
  testID="login-password-toggle"
  icon={showPassword ? "eye-off" : "eye"}
  onPress={() => setShowPassword(!showPassword)}
/>

// Login Button
<Button
  testID="login-submit-button"
  onPress={handleSubmit(onSubmit)}
>
  Sign In
</Button>

// Register Link
<Button
  testID="login-register-link"
  variant="text"
  onPress={navigateToRegister}
>
  Sign Up
</Button>

// Forgot Password Link
<Button
  testID="login-forgot-password-link"
  variant="text"
  onPress={navigateToForgotPassword}
>
  Forgot Password?
</Button>

// Loading Indicator (optional)
{isLoading && (
  <ActivityIndicator testID="login-loading-indicator" />
)}
```

## Register Screen (`RegisterScreen.jsx`)

```jsx
// First Name Input
<Input
  testID="register-firstname-input"
  label="First Name"
  // ... other props
/>

// Last Name Input
<Input
  testID="register-lastname-input"
  label="Last Name"
  // ... other props
/>

// Username Input
<Input
  testID="register-username-input"
  label="Username"
  // ... other props
/>

// Email Input
<Input
  testID="register-email-input"
  label="Email"
  // ... other props
/>

// Password Input
<Input
  testID="register-password-input"
  label="Password"
  secureTextEntry
  // ... other props
/>

// Confirm Password Input
<Input
  testID="register-confirm-password-input"
  label="Confirm Password"
  secureTextEntry
  // ... other props
/>

// Password Toggle (if implemented)
<TextInput.Icon
  testID="register-password-toggle"
  icon={showPassword ? "eye-off" : "eye"}
  onPress={() => setShowPassword(!showPassword)}
/>

// Customer Role Radio
<View testID="register-role-customer">
  <RadioButton value="customer" />
  <Text>Customer</Text>
</View>

// Seller Role Radio
<View testID="register-role-seller">
  <RadioButton value="seller" />
  <Text>Seller</Text>
</View>

// Dual Role Radio (if available)
<View testID="register-role-dual">
  <RadioButton value="dual" />
  <Text>Dual (Customer & Seller)</Text>
</View>

// Submit Button
<Button
  testID="register-submit-button"
  onPress={handleSubmit(onSubmit)}
>
  Create Account
</Button>

// Login Link
<Button
  testID="register-login-link"
  variant="outlined"
  onPress={() => navigation.navigate('Login')}
>
  Already have an account? Sign In
</Button>

// Loading Indicator
{loading && (
  <ActivityIndicator testID="register-loading-indicator" />
)}
```

## Forgot Password Screen (`ForgotPasswordScreen.jsx`)

```jsx
// Email Input
<Input
  testID="forgot-password-email-input"
  label="Email"
  // ... other props
/>

// Submit Button
<Button
  testID="forgot-password-submit-button"
  onPress={handleSubmit(onSubmit)}
>
  Send Reset Link
</Button>

// Back to Login Button
<Button
  testID="forgot-password-back-button"
  variant="outlined"
  onPress={() => navigation.navigate('Login')}
>
  Back to Sign In
</Button>

// Loading Indicator
{loading && (
  <ActivityIndicator testID="forgot-password-loading-indicator" />
)}
```

## Reset Password Screen (`ResetPasswordScreen.jsx`)

```jsx
// New Password Input
<Input
  testID="reset-password-input"
  label="New Password"
  secureTextEntry
  // ... other props
/>

// Confirm Password Input
<Input
  testID="reset-password-confirm-input"
  label="Confirm New Password"
  secureTextEntry
  // ... other props
/>

// Password Toggle
<TextInput.Icon
  testID="reset-password-toggle"
  icon={showPassword ? "eye-off" : "eye"}
  onPress={() => setShowPassword(!showPassword)}
/>

// Submit Button
<Button
  testID="reset-password-submit-button"
  onPress={handleSubmit(onSubmit)}
>
  Reset Password
</Button>

// Back Button
<Button
  testID="reset-password-back-button"
  variant="outlined"
  onPress={() => navigation.navigate('Login')}
>
  Back to Sign In
</Button>
```

## Change Password Screen (Profile/Settings)

```jsx
// Current Password Input
<Input
  testID="change-password-current-input"
  label="Current Password"
  secureTextEntry
  // ... other props
/>

// New Password Input
<Input
  testID="change-password-new-input"
  label="New Password"
  secureTextEntry
  // ... other props
/>

// Confirm Password Input
<Input
  testID="change-password-confirm-input"
  label="Confirm New Password"
  secureTextEntry
  // ... other props
/>

// Password Toggles
<TextInput.Icon
  testID="change-password-current-toggle"
  icon={showCurrentPassword ? "eye-off" : "eye"}
  onPress={() => setShowCurrentPassword(!showCurrentPassword)}
/>

<TextInput.Icon
  testID="change-password-new-toggle"
  icon={showNewPassword ? "eye-off" : "eye"}
  onPress={() => setShowNewPassword(!showNewPassword)}
/>

// Submit Button
<Button
  testID="change-password-submit-button"
  onPress={handleSubmit(onSubmit)}
>
  Change Password
</Button>

// Loading Indicator
{loading && (
  <ActivityIndicator testID="change-password-loading-indicator" />
)}
```

## Profile Screen (for logout tests)

```jsx
// Change Password Button
<Button
  testID="profile-change-password-button"
  onPress={() => navigation.navigate('ChangePassword')}
>
  Change Password
</Button>

// Logout Button
<Button
  testID="profile-logout-button"
  onPress={handleLogout}
>
  Logout
</Button>
```

## Navigation Tabs (Main App)

```jsx
// Bottom Tab Navigation
<Tab.Screen
  name="Home"
  component={HomeScreen}
  options={{
    tabBarTestID: 'home-tab',
  }}
/>

<Tab.Screen
  name="Profile"
  component={ProfileScreen}
  options={{
    tabBarTestID: 'profile-tab',
  }}
/>
```

## Additional UI Elements

```jsx
// Product List (for post-logout tests)
<FlatList
  testID="product-list"
  data={products}
  // ... other props
/>

// Back Button (general)
<TouchableOpacity
  testID="back-button"
  onPress={() => navigation.goBack()}
>
  <Icon name="arrow-left" />
</TouchableOpacity>
```

## Implementation Steps

### Step 1: Add testIDs to Input Components

If you're using a custom `Input` component, make sure it forwards the `testID` prop:

```jsx
// components/common/Input.jsx
export const Input = ({ testID, ...props }) => {
  return (
    <TextInput
      testID={testID}  // ← Forward testID
      {...props}
    />
  );
};
```

### Step 2: Add testIDs to Button Components

```jsx
// components/common/Button.jsx
export const Button = ({ testID, children, ...props }) => {
  return (
    <TouchableOpacity
      testID={testID}  // ← Forward testID
      {...props}
    >
      <Text>{children}</Text>
    </TouchableOpacity>
  );
};
```

### Step 3: Test Your Changes

After adding testIDs, rebuild and test:

```bash
# Rebuild the app
cd ../front_end
npm run android  # or npm run ios

# Run automation tests
cd ../mobile_automation_test
npm run test:auth
```

## Best Practices

### ✅ DO:

1. **Use kebab-case** for testID values
   ```jsx
   testID="login-username-input"  // ✓
   ```

2. **Be descriptive and specific**
   ```jsx
   testID="register-submit-button"  // ✓ Clear purpose
   ```

3. **Use consistent naming patterns**
   ```jsx
   testID="screen-element-type"
   testID="login-username-input"
   testID="register-email-input"
   ```

4. **Add testID to interactive elements**
   - Buttons
   - Input fields
   - Links/Touchables
   - Radio buttons / Checkboxes
   - Tabs

### ❌ DON'T:

1. **Don't use generic IDs**
   ```jsx
   testID="button"  // ✗ Too generic
   ```

2. **Don't use dynamic values**
   ```jsx
   testID={`item-${id}`}  // ✗ Hard to test
   ```

3. **Don't forget nested components**
   ```jsx
   // ✗ Missing testID on icon
   <Button>
     <Icon name="user" />
   </Button>

   // ✓ Include testID
   <Button testID="profile-button">
     <Icon testID="profile-icon" name="user" />
   </Button>
   ```

## Verification

### Check if testID is Working

1. **Run app in development mode**
2. **Enable Debug mode** (Cmd+D on iOS, Cmd+M on Android)
3. **Select "Show Element Inspector"**
4. **Tap an element** and verify `testID` appears in properties

### Test with Detox

```bash
# Run a single test to verify
detox test e2e/auth/login.test.js --configuration ios.sim.debug --loglevel verbose
```

If you see errors like:
```
Error: Cannot find element with testID "login-username-input"
```

Check that:
1. testID is added to the component
2. Component is rendered on screen
3. Component is visible (not hidden behind other views)
4. testID prop is properly forwarded in custom components

## Common Issues

### Issue: "Cannot find element with testID"

**Solution:**
1. Verify testID is added to the component
2. Check component is rendered (use Element Inspector)
3. Ensure testID prop is forwarded in custom components
4. Rebuild the app after adding testIDs

### Issue: Multiple elements with same testID

**Solution:**
Use unique testIDs for each element, even in lists:

```jsx
// ✗ Don't do this
{items.map(item => (
  <Button testID="list-button">{item.name}</Button>
))}

// ✓ Do this (but avoid if possible)
{items.map((item, index) => (
  <Button testID={`list-button-${index}`}>{item.name}</Button>
))}

// ✓ Better: Test the parent container
<FlatList testID="items-list" data={items} />
```

## Platform Differences

testID works slightly differently on iOS vs Android:

- **iOS**: Uses `accessibilityIdentifier`
- **Android**: Uses `nativeID`

Detox handles this automatically, but if you're accessing native properties:

```jsx
// React Native automatically maps testID to:
// iOS: accessibilityIdentifier
// Android: nativeID

<View testID="my-view" />  // Works on both platforms
```

## Need Help?

- Review existing components with testIDs
- Check [Detox Documentation](https://wix.github.io/Detox/docs/api/matchers)
- Ask the team for testID naming conventions
- Run tests to verify your implementations

---

**Next Steps:**
1. Add all required testIDs to authentication screens
2. Rebuild the mobile app
3. Run automation tests to verify
4. Expand testIDs to other screens as needed
