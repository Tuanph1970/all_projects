# Mathematics Solver Mobile Automation Tests

E2E and API automation tests for the Mathematics Solver mobile application using [Maestro](https://maestro.mobile.dev/) and Jest.

## 📋 Overview

This project provides comprehensive test coverage for the Mathematics Solver mobile app:

- **Maestro E2E Tests**: Mobile UI automation tests
- **API Tests**: Backend service API testing
- **Unit Tests**: Configuration and helper function tests

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** and **npm**
- **Java 17+** (required for Maestro)
- **Android SDK** with emulator or physical device
- **Maestro CLI** (installed via setup script)

### Installation

1. **Install dependencies**:
   ```bash
   cd math_mobile_automation_test
   npm install
   ```

2. **Setup Maestro**:
   ```bash
   npm run maestro:setup
   ```

3. **Start Android emulator** or connect a physical device:
   ```bash
   # Example for Android Studio
   emulator -avd Pixel_6_API_33
   ```

4. **Verify device connection**:
   ```bash
   adb devices
   ```

## 📁 Project Structure

```
math_mobile_automation_test/
├── __tests__/
│   ├── api/                    # API E2E tests
│   │   ├── auth.api.test.js
│   │   ├── problem.api.test.js
│   │   ├── solution.api.test.js
│   │   └── setup.js
│   ├── apiHelpers.test.js
│   ├── apiHelpers.unit.test.js
│   └── testConfig.test.js
├── e2e/
│   └── config/
│       └── testConfig.js       # Test configuration
├── maestro/
│   ├── .maestro/
│   │   └── config.yaml         # Maestro configuration
│   └── flows/                  # Maestro test flows
│       ├── login-flow.yaml
│       ├── fast-login-flow.yaml
│       ├── register-flow.yaml
│       └── capture-and-solve-flow.yaml
├── scripts/
│   ├── setup-maestro.sh        # Maestro setup script
│   ├── run-maestro-tests.sh    # Test runner
│   ├── run-test-suite.sh       # Suite runner
│   ├── install-java17.sh       # Java installation
│   ├── wait-for-metro.sh       # Metro bundler wait script
│   └── tcp_proxy.py            # TCP proxy for testing
├── screenshots/                # Test screenshots (gitignored)
├── .eslintrc.js
├── .gitignore
├── jest.config.api.js
├── jest.config.unit.js
└── package.json
```

## 🧪 Running Tests

### All Tests
```bash
npm test
```

### API Tests
```bash
# Run all API tests
npm run test:api

# Run specific API test suite
npm run test:api:auth
npm run test:api:problem
npm run test:api:solution

# Run with verbose output
npm run test:api:verbose

# Watch mode
npm run test:api:watch
```

### Maestro E2E Tests
```bash
# Run all Maestro tests
npm run maestro:test

# Run specific test suites
npm run maestro:smoke          # Quick smoke tests
npm run maestro:auth           # Authentication tests
npm run maestro:problem        # Problem solving tests
npm run maestro:solution       # Solution tests
npm run maestro:regression     # Full regression suite
npm run maestro:quick          # Fast login test

# Debug mode
npm run maestro:debug
```

### Unit Tests
```bash
# Run unit tests
npm run test:unit

# Watch mode
npm run test:unit:watch

# With coverage
npm run test:unit:coverage
```

## 📝 Test Suites

### Authentication Tests
- User registration
- User login/logout
- Token refresh
- Protected route access

### Problem Service Tests
- Create problem
- List problems
- Get problem details
- Delete problem

### Solution Service Tests
- OCR processing
- Solution generation
- Solution history
- ML service health

### E2E Mobile Tests
- Login flow
- Registration flow
- Capture and solve problem
- Navigation flows

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# API Configuration
API_BASE_URL=http://localhost:8001
ML_SERVICE_URL=http://localhost:8002
API_TIMEOUT=10000

# Test Users
TEST_USER_EMAIL=test_user@test.com
TEST_USER_PASSWORD=Test@12345678

# Maestro
MAESTRO_VERBOSE=true
```

### Test Configuration

Edit `e2e/config/testConfig.js` to customize:
- API endpoints
- Test user credentials
- Timeout values
- Screen identifiers (testIDs)

## 🔧 Scripts

| Script | Description |
|--------|-------------|
| `npm run maestro:setup` | Install and configure Maestro |
| `npm run maestro:test` | Run all Maestro E2E tests |
| `npm run maestro:smoke` | Run quick smoke tests |
| `npm run maestro:regression` | Run full regression suite |
| `npm run test:api` | Run API E2E tests |
| `npm run test:unit` | Run unit tests |
| `npm run lint` | Run ESLint |
| `npm run lint:fix` | Fix ESLint issues |

## 📱 App Integration

### Required testIDs in React Native App

For Maestro tests to work, ensure your React Native components have these testIDs:

```javascript
// Login Screen
testID="login-email-input"
testID="login-password-input"
testID="login-button"
testID="register-button"

// Home Screen
testID="home-screen"
testID="scan-button"

// Scan Screen
testID="scan-screen"
testID="capture-button"

// Solution Screen
testID="solution-screen"
testID="solution-result"
testID="solution-steps"
```

## 🐛 Troubleshooting

### Maestro not found
```bash
# Install Java 17
npm run maestro:setup

# Or manually
./scripts/install-java17.sh
```

### No devices detected
```bash
# Start Android emulator
emulator -avd <your-avd-name>

# Or connect physical device via USB
adb devices
```

### API tests failing
```bash
# Ensure backend is running
cd ../backend
dotnet run

# Or start Docker services
docker-compose up
```

### Tests timing out
- Increase timeout in `e2e/config/testConfig.js`
- Check if backend services are responsive
- Verify network connectivity

## 📊 Test Coverage

The test suite covers:

- ✅ Authentication flows
- ✅ Problem CRUD operations
- ✅ Solution generation (OCR + ML)
- ✅ Mobile UI interactions
- ✅ API error handling
- ✅ Security validations

## 🤝 Contributing

1. Create new test flows in `maestro/flows/`
2. Add API tests in `__tests__/api/`
3. Update configuration in `e2e/config/`
4. Run tests before committing: `npm test`

## 📚 Resources

- [Maestro Documentation](https://maestro.mobile.dev/)
- [Jest Documentation](https://jestjs.io/)
- [React Native Testing](https://reactnative.dev/docs/testing-overview)

## 📄 License

ISC
