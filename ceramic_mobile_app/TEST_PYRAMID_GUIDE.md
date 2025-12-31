# Test Pyramid Guide for Ceramic Marketplace

Complete testing strategy following the test pyramid methodology for React Native applications.

## 📊 The Test Pyramid

```
        /\
       /  \
      / E2E\ ←------ 10% (Slow, Expensive, Brittle)
     /______\
    /        \
   /Integration\ ←-- 20% (Medium Speed, Moderate Cost)
  /__________\
 /            \
/    Unit      \ ←---- 70% (Fast, Cheap, Stable)
/________________\
```

---

## Level 1: Unit Tests (70% of tests)

**Purpose:** Test individual components and functions in isolation

**Characteristics:**
- ⚡ **Fast:** <1s per test
- 💰 **Cheap:** No setup required
- 🎯 **Focused:** Single responsibility
- 🔄 **Reliable:** No external dependencies
- 🚀 **High Coverage:** 80%+ code coverage

### What to Test:

#### ✅ Components
```javascript
// Button.test.jsx
- Renders with correct text
- Calls onClick when pressed
- Shows disabled state
- Displays loading indicator
- Applies custom styles
```

#### ✅ Business Logic
```javascript
// utils/validation.test.js
- Email validation
- Password strength
- Price formatting
- Date calculations
```

#### ✅ Redux Reducers
```javascript
// authSlice.test.js
- Initial state
- Login success action
- Login failure action
- Logout action
- State updates
```

#### ✅ Custom Hooks
```javascript
// useAuth.test.js
- Returns current user
- Handles login flow
- Handles logout
- Updates on state change
```

### Example Unit Test:

```javascript
// Button.test.jsx
import { render, fireEvent } from '@testing-library/react-native';
import { Button } from '../Button';

describe('Button', () => {
  it('calls onPress when tapped', () => {
    const onPress = jest.fn();
    const { getByText } = render(<Button onPress={onPress}>Click</Button>);

    fireEvent.press(getByText('Click'));

    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
```

### Running Unit Tests:

```bash
# Run all unit tests
cd front_end
npm test

# Watch mode (re-run on changes)
npm run test:watch

# With coverage
npm run test:coverage

# Specific file
npm test -- Button.test.jsx

# Update snapshots
npm test -- -u
```

### Coverage Goals:

```
Statements   : 80%
Branches     : 75%
Functions    : 80%
Lines        : 80%
```

---

## Level 2: Integration Tests (20% of tests)

**Purpose:** Test how components work together

**Characteristics:**
- ⚡ **Medium Speed:** 2-5s per test
- 💰 **Moderate Cost:** Some setup needed
- 🔗 **Connected:** Multiple components
- 🎯 **User Flows:** Real interactions
- 📊 **Coverage:** Critical paths

### What to Test:

#### ✅ User Flows
```javascript
// AuthFlow.integration.test.jsx
- Login → Home navigation
- Register → Email verification
- Forgot password → Reset
- Logout → Return to login
```

#### ✅ Form Submissions
```javascript
// ProductForm.integration.test.jsx
- Fill form → Validate → Submit → Success
- Fill form → API error → Show error
- Upload image → Preview → Submit
```

#### ✅ State Management
```javascript
// Cart.integration.test.jsx
- Add to cart → Update count
- Remove item → Recalculate total
- Apply coupon → Update price
```

#### ✅ Navigation
```javascript
// Navigation.integration.test.jsx
- Tab navigation
- Stack navigation
- Deep linking
- Back button handling
```

### Example Integration Test:

```javascript
// AuthFlow.integration.test.jsx
import { renderWithProviders } from '../utils/testUtils';
import { LoginScreen } from '../screens/LoginScreen';

describe('Login Flow', () => {
  it('navigates to home after successful login', async () => {
    const { getByTestId, getByText } = renderWithProviders(<LoginScreen />);

    // Enter credentials
    fireEvent.changeText(getByTestId('username'), 'testuser');
    fireEvent.changeText(getByTestId('password'), 'password123');

    // Submit form
    fireEvent.press(getByTestId('submit'));

    // Verify navigation
    await waitFor(() => {
      expect(getByText('Welcome back!')).toBeTruthy();
    });
  });
});
```

### Running Integration Tests:

```bash
# Run integration tests
cd front_end
npm run test:integration

# Specific test suite
npm test -- AuthFlow.integration.test.jsx

# Debug mode
npm test -- --detectOpenHandles
```

---

## Level 3: E2E Tests (10% of tests)

**Purpose:** Test complete user journeys on real/emulated devices

**Characteristics:**
- 🐌 **Slow:** 30s-5min per test
- 💸 **Expensive:** Build + device setup
- 🎯 **Critical Paths:** Most important flows
- 🔄 **Brittle:** Network, timing issues
- 📱 **Real Environment:** Actual device behavior

### What to Test:

#### ✅ Critical User Journeys
```javascript
// login.e2e.test.js
- Complete login flow
- Authentication persistence
- Error handling
```

#### ✅ Core Features
```javascript
// checkout.e2e.test.js
- Browse → Add to cart → Checkout → Payment
```

#### ✅ Platform-Specific
```javascript
// camera.e2e.test.js
- Camera permissions
- Image picker
- Native modules
```

### Example E2E Test:

```javascript
// login.e2e.test.js (Detox)
describe('Login Flow', () => {
  it('should login successfully', async () => {
    await element(by.id('username-input')).typeText('testuser');
    await element(by.id('password-input')).typeText('password123');
    await element(by.id('login-button')).tap();

    await waitFor(element(by.text('Welcome back!')))
      .toBeVisible()
      .withTimeout(5000);
  });
});
```

### Running E2E Tests:

```bash
# Build app
cd mobile_automation_test
detox build --configuration ios.sim.debug

# Run tests
detox test --configuration ios.sim.debug

# Specific test
detox test e2e/auth/login.test.js --configuration ios.sim.debug

# With screenshots
detox test --take-screenshots all

# Debug mode
detox test --loglevel trace
```

---

## Test Distribution Strategy

### Development (Daily)

```bash
# Fast feedback loop
npm test                      # Unit tests (30s)
npm run test:integration      # Integration (2min)
# Skip E2E for rapid iteration
```

### Pull Request (Before Merge)

```bash
# Comprehensive validation
npm run test:coverage         # Unit + coverage (1min)
npm run test:integration      # Integration (3min)
detox test --configuration ios.sim.debug  # E2E critical paths (5min)
# Total: ~10min
```

### Pre-Release (Before Deployment)

```bash
# Full test suite
npm run test:all              # All unit + integration (5min)
detox test --configuration ios.sim.debug    # iOS E2E (15min)
detox test --configuration android.emu.debug # Android E2E (15min)
# Real device smoke tests (10min)
# Total: ~45min
```

---

## When to Use Each Test Type

### Use Unit Tests For:
- ✅ Utility functions (validation, formatting, calculations)
- ✅ Redux reducers and actions
- ✅ Custom hooks
- ✅ Component rendering logic
- ✅ Edge cases and error conditions
- ✅ Math and business logic

### Use Integration Tests For:
- ✅ Form submissions
- ✅ Multi-step workflows
- ✅ Component interactions
- ✅ State management flows
- ✅ Navigation patterns
- ✅ API request/response handling (mocked)

### Use E2E Tests For:
- ✅ Critical user journeys (login, checkout, purchase)
- ✅ Platform-specific features (camera, permissions)
- ✅ Cross-screen workflows
- ✅ Authentication flows
- ✅ Payment processing
- ✅ Smoke tests for deployments

---

## Best Practices

### ✅ DO:

**Unit Tests:**
- Test one thing at a time
- Mock external dependencies
- Use descriptive test names
- Aim for >80% coverage
- Keep tests fast (<1s each)

**Integration Tests:**
- Test real user workflows
- Mock only external APIs
- Use realistic test data
- Focus on critical paths
- Verify state changes

**E2E Tests:**
- Test happy paths only
- Add waits for async operations
- Use stable selectors (testID)
- Screenshot on failure
- Keep suite under 30min

### ❌ DON'T:

**Unit Tests:**
- Test implementation details
- Test external libraries
- Make actual API calls
- Test multiple units together
- Rely on test execution order

**Integration Tests:**
- Test every possible path
- Make real network requests
- Test platform-specific code
- Duplicate unit test coverage

**E2E Tests:**
- Test every edge case
- Use text-based selectors (fragile)
- Hardcode delays (use waitFor)
- Run on every commit (too slow)
- Test external services

---

## Coverage Recommendations

### By Test Type:

| Test Type | % of Tests | Execution Time | Cost | Reliability |
|-----------|-----------|----------------|------|-------------|
| Unit | 70% | <1min | Low | High (95%) |
| Integration | 20% | 2-5min | Medium | Medium (80%) |
| E2E | 10% | 15-30min | High | Low (70%) |

### By Feature:

| Feature | Unit | Integration | E2E | Priority |
|---------|------|-------------|-----|----------|
| **Authentication** | 80% | 15% | 5% | Critical |
| **Product Catalog** | 75% | 20% | 5% | High |
| **Shopping Cart** | 80% | 15% | 5% | Critical |
| **Checkout/Payment** | 70% | 20% | 10% | Critical |
| **User Profile** | 85% | 15% | 0% | Medium |
| **Search** | 80% | 15% | 5% | High |

---

## Migration Plan

### Phase 1: Foundation (Week 1)
1. ✅ Install testing dependencies
2. ✅ Configure Jest and RTL
3. ✅ Create test utilities
4. ✅ Write first unit tests (5 components)
5. Target: 30% unit test coverage

### Phase 2: Expansion (Week 2-3)
1. Add unit tests for all components
2. Add unit tests for utilities
3. Add unit tests for Redux slices
4. Write first integration tests (3 flows)
5. Target: 60% unit test coverage

### Phase 3: Integration (Week 4)
1. Complete integration test suite
2. Add critical path integration tests
3. Improve Detox E2E tests
4. Add real device testing
5. Target: 80% total coverage

### Phase 4: Automation (Week 5)
1. Set up CI/CD pipelines
2. Add pre-commit hooks
3. Configure code coverage reporting
4. Implement automated E2E on PRs
5. Target: Full automation

---

## Quick Reference

```bash
# Unit Tests (fast, run often)
npm test                           # All unit tests
npm run test:watch                 # Watch mode
npm test -- Button.test.jsx        # Specific file

# Integration Tests (medium, run on PR)
npm run test:integration           # All integration
npm run test:integration:watch     # Watch mode

# E2E Tests (slow, run before release)
detox build --configuration ios.sim.debug
detox test --configuration ios.sim.debug    # All E2E
detox test e2e/auth --configuration ios.sim.debug  # Specific folder

# Coverage
npm run test:coverage              # Generate report
npm run test:coverage:view         # Open in browser

# Debug
npm test -- --detectOpenHandles    # Find hanging promises
npm test -- --verbose              # Detailed output
npm test -- --bail                 # Stop on first failure
```

---

## Success Metrics

**Before:**
- ❌ 0 unit tests
- ❌ 0 integration tests
- ❌ Only brittle E2E tests
- ❌ 15min+ test feedback
- ❌ <50% test reliability

**After (Goal):**
- ✅ 80%+ code coverage
- ✅ <1min unit test feedback
- ✅ 95%+ test reliability
- ✅ Automated CI/CD
- ✅ Confidence in deployments

---

## Resources

- [Testing Library Docs](https://testing-library.com/docs/react-native-testing-library/intro/)
- [Jest Documentation](https://jestjs.io/)
- [Detox Documentation](https://wix.github.io/Detox/)
- [Test Pyramid Pattern](https://martinfowler.com/articles/practical-test-pyramid.html)
