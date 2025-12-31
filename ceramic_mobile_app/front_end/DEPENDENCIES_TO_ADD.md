# Dependencies to Add for Testing

Run the following command to install all necessary testing dependencies:

```bash
cd front_end

npm install --save-dev \
  @testing-library/react-native@^12.0.0 \
  @testing-library/jest-native@^5.4.0 \
  redux-mock-store@^1.5.4 \
  redux-thunk@^3.1.0

# Or with yarn:
yarn add -D \
  @testing-library/react-native@^12.0.0 \
  @testing-library/jest-native@^5.4.0 \
  redux-mock-store@^1.5.4 \
  redux-thunk@^3.1.0
```

## What Each Dependency Does:

### @testing-library/react-native
- **Purpose**: Testing utilities for React Native components
- **Features**:
  - Query components by text, testID, role
  - Fire events (press, change text, scroll)
  - Wait for async operations
  - Better testing practices

### @testing-library/jest-native
- **Purpose**: Custom Jest matchers for React Native
- **Features**:
  - `toBeVisible()`, `toBeDisabled()`, `toHaveTextContent()`
  - `toHaveStyle()`, `toBeEmpty()`
  - Better assertions for RN components

### redux-mock-store
- **Purpose**: Mock Redux store for testing
- **Features**:
  - Create mock stores with initial state
  - Test Redux-connected components
  - Verify dispatched actions

### redux-thunk
- **Purpose**: Async action support for Redux (if not already installed)
- **Features**:
  - Handle async actions in tests
  - Required for mocking async Redux operations

## Already Installed:
✅ jest (v29.2.1)
✅ jest-expo (~54.0.0)
✅ react-test-renderer (19.1.0)
✅ detox (^20.46.0)

## Installation Verification:

After installing, verify with:

```bash
npm list --depth=0 | grep testing-library
npm list --depth=0 | grep redux-mock-store
```

Expected output:
```
├── @testing-library/jest-native@5.4.x
├── @testing-library/react-native@12.0.x
├── redux-mock-store@1.5.x
└── redux-thunk@3.1.x (if not already present)
```

## Run Tests:

After installation:

```bash
# Run all unit tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run integration tests only
npm run test:integration

# Run unit tests only
npm run test:unit
```
