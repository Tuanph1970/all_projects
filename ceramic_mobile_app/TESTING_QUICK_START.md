# Testing Quick Start Guide

Get started with testing in 5 minutes.

## 🚀 Installation

### Step 1: Install Testing Dependencies

```bash
cd front_end

# Install required packages
npm install --save-dev \
  @testing-library/react-native@^12.0.0 \
  @testing-library/jest-native@^5.4.0 \
  redux-mock-store@^1.5.4 \
  redux-thunk@^3.1.0
```

### Step 2: Verify Installation

```bash
# Run existing unit test examples
npm test

# Should see output like:
# PASS  src/components/common/__tests__/Button.test.jsx
# PASS  src/screens/auth/__tests__/LoginScreen.test.jsx
#
# Tests:       15 passed, 15 total
# Time:        2.5s
```

---

## 📝 Quick Test Commands

### Unit Tests (Most Common)

```bash
cd front_end

# Run all unit tests
npm test

# Watch mode (auto re-run on file changes)
npm run test:watch

# With coverage report
npm run test:coverage

# Test specific file
npm test -- LoginScreen.test.jsx

# Update snapshots
npm run test:update
```

### Integration Tests

```bash
cd front_end

# Run integration tests only
npm run test:integration

# Watch mode
npm run test:integration:watch
```

### E2E Tests (Detox)

```bash
cd mobile_automation_test

# iOS Simulator
npm run build:ios           # Build once
npm run test:ios           # Run tests

# Android Emulator
npm run build:android      # Build once
npm run test:android       # Run tests

# Real Devices
npm run build:device:ios
npm run test:device:ios

# Debug mode (verbose logs)
npm run test:debug

# With screenshots
npm run test:screenshots
```

---

## ✍️ Writing Your First Test

### 1. Unit Test Example

Create: `src/components/MyComponent/__tests__/MyComponent.test.jsx`

```javascript
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { MyComponent } from '../MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    const { getByText } = render(<MyComponent title="Hello" />);
    expect(getByText('Hello')).toBeTruthy();
  });

  it('handles button press', () => {
    const onPress = jest.fn();
    const { getByTestId } = render(
      <MyComponent onPress={onPress} testID="my-button" />
    );

    fireEvent.press(getByTestId('my-button'));
    expect(onPress).toHaveBeenCalled();
  });
});
```

### 2. Integration Test Example

Create: `src/__tests__/integration/MyFeature.integration.test.jsx`

```javascript
import React from 'react';
import { fireEvent, waitFor } from '@testing-library/react-native';
import { renderWithProviders } from '../utils/testUtils';
import { MyScreen } from '../../screens/MyScreen';

describe('MyFeature Integration', () => {
  it('completes user flow', async () => {
    const { getByTestId, getByText } = renderWithProviders(<MyScreen />);

    // Step 1: Fill form
    fireEvent.changeText(getByTestId('input'), 'test value');

    // Step 2: Submit
    fireEvent.press(getByTestId('submit-button'));

    // Step 3: Verify result
    await waitFor(() => {
      expect(getByText('Success!')).toBeTruthy();
    });
  });
});
```

### 3. E2E Test Example

Create: `mobile_automation_test/e2e/myfeature.test.js`

```javascript
const config = require('./config/testConfig');

describe('My Feature E2E', () => {
  beforeEach(async () => {
    await device.launchApp({ newInstance: true });
  });

  it('should complete workflow', async () => {
    // Find and interact with elements
    await element(by.id('my-input')).typeText('test');
    await element(by.id('submit-button')).tap();

    // Verify outcome
    await waitFor(element(by.text('Success')))
      .toBeVisible()
      .withTimeout(5000);
  });
});
```

---

## 🎯 Test Coverage Goals

Run this to see current coverage:

```bash
cd front_end
npm run test:coverage
```

**Target Coverage:**
- Statements: 80%
- Branches: 75%
- Functions: 80%
- Lines: 80%

**View Coverage Report:**
```bash
npm run test:coverage:view
# Opens browser with detailed coverage report
```

---

## 🔧 Common Issues & Solutions

### Issue: "Cannot find module '@testing-library/react-native'"

**Solution:**
```bash
cd front_end
npm install --save-dev @testing-library/react-native
```

### Issue: "ReferenceError: device is not defined"

**Solution:** This is a Detox E2E test. Run from mobile_automation_test:
```bash
cd mobile_automation_test
npm run test:ios
```

### Issue: Tests hanging or not completing

**Solution:**
```bash
# Debug mode to see what's hanging
npm run test:debug

# Or run with timeout
npm test -- --testTimeout=10000
```

### Issue: "Detox build failed"

**Solution:**
```bash
# iOS: Clean build
cd front_end/ios
rm -rf build DerivedData
pod install
cd ../../mobile_automation_test
npm run build:ios

# Android: Clean build
cd front_end/android
./gradlew clean
cd ../../mobile_automation_test
npm run build:android
```

---

## 📚 Test Types at a Glance

| Type | Speed | Cost | Reliability | When to Run |
|------|-------|------|-------------|-------------|
| **Unit** | ⚡ Fast (30s) | 💰 Low | ✅ High (95%) | Every commit |
| **Integration** | ⚡ Medium (3min) | 💰💰 Medium | ✅ Good (85%) | Before PR |
| **E2E** | 🐌 Slow (15min) | 💰💰💰 High | ⚠️ Medium (75%) | Before release |

---

## 🎬 Daily Workflow

### During Development (Fast Feedback)

```bash
cd front_end

# Terminal 1: Watch mode for current file
npm run test:watch -- MyComponent.test.jsx

# Make changes to MyComponent.jsx
# Tests auto-run on save
```

### Before Committing (Quick Validation)

```bash
cd front_end

# Run all tests
npm test

# Fix any linting issues
npm run lint:fix

# Commit if all pass ✅
```

### Before Creating PR (Comprehensive)

```bash
cd front_end

# 1. Run tests with coverage
npm run test:coverage

# 2. Run integration tests
npm run test:integration

# 3. Optional: Run E2E for critical changes
cd ../mobile_automation_test
npm run build:ios
npm run test:ios
```

---

## 🚦 CI/CD Integration

Tests run automatically on GitHub Actions:

**On Every Push:**
- ✅ Unit tests
- ✅ Linting

**On Pull Requests:**
- ✅ Unit tests
- ✅ Integration tests
- ✅ Coverage report

**On Main Branch / Before Release:**
- ✅ Full test suite
- ✅ iOS E2E tests
- ✅ Android E2E tests

**Add `run-e2e` label to PR** to trigger E2E tests on demand.

---

## 📖 Further Reading

- [Test Pyramid Guide](./TEST_PYRAMID_GUIDE.md) - Complete testing strategy
- [Real Device Testing](./mobile_automation_test/REAL_DEVICE_TESTING.md) - Physical device setup
- [Dependencies Guide](./front_end/DEPENDENCIES_TO_ADD.md) - Installation details

---

## ✅ Checklist

Before you start coding:
- [ ] Dependencies installed
- [ ] `npm test` runs successfully
- [ ] Understand unit vs integration vs E2E
- [ ] Know how to run each test type
- [ ] Coverage goals are clear

You're ready to write tests! 🎉

---

## 🆘 Get Help

**Test Not Running?**
```bash
# Check dependencies
cd front_end
npm list @testing-library/react-native

# Reinstall if missing
npm install
```

**Still Stuck?**
1. Check error message carefully
2. Review example tests in `__tests__` folders
3. Consult [Test Pyramid Guide](./TEST_PYRAMID_GUIDE.md)
4. Check GitHub Issues for similar problems
