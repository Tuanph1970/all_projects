# Testing Guide - Ceramic Mobile Automation

## Quick Start

### Run Unit Tests (No Device Required) ✅
```bash
cd mobile_automation_test
npm run test:unit
```

**Result:** All tests run without needing Android emulator or device!

---

## Test Types

### 1. Unit Tests (✅ Implemented)
**Location:** `__tests__/`
**Purpose:** Validate configuration, helpers, and utilities
**Requirements:** None - just Node.js

**Commands:**
```bash
npm run test:unit              # Run all unit tests
npm run test:unit:watch        # Run in watch mode
npm run test:unit:coverage     # Generate coverage report
```

**Tests Include:**
- Configuration validation
- API helper structure tests
- Method signature verification
- URL construction logic
- Data validation rules

---

### 2. E2E Tests (Existing - Device Required)
**Location:** `e2e/auth/`
**Purpose:** Test actual app flows on device
**Requirements:** Android emulator/device + built APK

**Commands:**
```bash
# Build first
npm run build:android

# Run on emulator
npm run test:android

# Run on physical device
npm run test:device:android

# Specific test suites
npm run test:auth:android      # Just auth tests
```

**Tests Include:**
- Login flows
- Registration
- Password reset
- Password change
- Logout functionality

---

## Test Results Summary

| Test Type | Suites | Tests | Status | Time |
|-----------|--------|-------|--------|------|
| Unit Tests | 3 | 31 | ✅ PASSED | 0.17s |
| E2E Tests | 5 | ~50+ | 🔄 Device Required | - |

---

## What Was Changed

### Files Added
1. `jest.config.unit.js` - Unit test configuration
2. `__tests__/testConfig.test.js` - Configuration tests
3. `__tests__/apiHelpers.unit.test.js` - API helper tests
4. `__tests__/apiHelpers.test.js` - Basic helper tests
5. `TEST_REPORT.md` - Detailed test report
6. `README_TESTING.md` - This guide

### Files Modified
- `package.json` - Added unit test scripts

### Test Scripts Added
```json
"test:unit": "jest --config jest.config.unit.js",
"test:unit:watch": "jest --config jest.config.unit.js --watch",
"test:unit:coverage": "jest --config jest.config.unit.js --coverage"
```

---

## When to Use Each Test Type

### Use Unit Tests When:
- ✅ Developing new features
- ✅ Validating configuration changes
- ✅ Testing helper functions
- ✅ Running CI/CD pipelines
- ✅ Quick validation needed
- ✅ No device available

### Use E2E Tests When:
- 🔄 Final validation before production
- 🔄 Testing actual user flows
- 🔄 Verifying UI interactions
- 🔄 Testing on target device
- 🔄 Capturing screenshots
- 🔄 Performance testing

---

## Test Configuration Details

### Unit Tests (`jest.config.unit.js`)
```javascript
{
  testMatch: ['<rootDir>/__tests__/**/*.test.js'],
  testEnvironment: 'node',
  testTimeout: 10000,
  // Ignores E2E test files
}
```

### E2E Tests (`e2e/jest.config.js`)
```javascript
{
  testMatch: ['<rootDir>/e2e/**/*.test.js'],
  testEnvironment: 'detox/runners/jest/testEnvironment',
  testTimeout: 120000,
  // Requires Detox
}
```

---

## Troubleshooting

### Unit Tests Failing
```bash
# Check if dependencies installed
npm install

# Run with verbose output
npm run test:unit -- --verbose

# Check Jest version
npx jest --version
```

### E2E Tests Failing
```bash
# Check device connected
adb devices

# Check app built
ls -la ../front_end/android/app/build/outputs/apk/debug/

# Rebuild app
npm run build:android

# Check Detox configuration
cat .detoxrc.js
```

---

## Adding New Tests

### Add Unit Test
1. Create file in `__tests__/` directory
2. Name it `*.test.js`
3. Import the module to test
4. Write test cases

Example:
```javascript
const myHelper = require('../e2e/helpers/myHelper');

describe('My Helper Tests', () => {
  it('should do something', () => {
    expect(myHelper.someFunction()).toBeDefined();
  });
});
```

### Add E2E Test
1. Create file in `e2e/auth/` directory
2. Name it `*.test.js`
3. Use Detox API
4. Include device interactions

---

## CI/CD Integration

### Unit Tests (Fast - Always Run)
```yaml
# .github/workflows/test.yml
- name: Run Unit Tests
  run: |
    cd mobile_automation_test
    npm install
    npm run test:unit
```

### E2E Tests (Slow - Run on Demand)
```yaml
# Requires emulator setup
- name: Run E2E Tests
  run: |
    cd mobile_automation_test
    npm run build:android
    npm run test:android
```

---

## Next Steps

### Immediate (Your Current Approach) ✅
1. Use unit tests during development
2. Validate configuration changes quickly
3. Test on physical device manually

### Future Enhancements
1. Add more unit tests for utilities
2. Set up mock API server
3. Add integration tests
4. Implement visual regression testing

---

## Summary

**Current Status:**
- ✅ Unit tests: 31 passing (no device needed)
- 🔄 E2E tests: Available for device testing

**Your Workflow:**
1. Run `npm run test:unit` during development
2. All tests pass without device
3. Use physical device for final E2E testing
4. Production testing on real device

**Key Achievement:**
You can now run automated tests and get pass/fail results **without needing to launch an emulator or connect a device**. Perfect for rapid development!

---

For detailed results, see `TEST_REPORT.md`
