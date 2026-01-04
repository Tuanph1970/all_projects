# Mobile Automation Test

End-to-End (E2E) automated testing for the Ceramic Mobile App using **Maestro**.

## Quick Start

### Prerequisites

1. **Java 17+** (Required by Maestro)
   ```bash
   java -version  # Check current version
   # If needed, install Java 17:
   sudo apt install openjdk-17-jdk
   ```

2. **Android SDK** with environment variables set:
   ```bash
   export ANDROID_HOME=~/Android/Sdk
   export PATH=$PATH:$ANDROID_HOME/emulator
   export PATH=$PATH:$ANDROID_HOME/platform-tools
   ```

3. **Android Emulator** or physical device

### Installation

```bash
# 1. Install dependencies
npm install

# 2. Install Maestro CLI
npm run maestro:setup
# or manually:
curl -Ls "https://get.maestro.mobile.dev" | bash
export PATH="$HOME/.maestro/bin:$PATH"

# 3. Verify installation
maestro --version
```

## Running Tests

### Quick Start (Emulator already running)

```bash
# Run smoke tests
npm run maestro:smoke

# Run auth tests
npm run maestro:auth

# Run all tests
npm run maestro:test
```

### Available Test Suites

| Command | Description | Duration |
|---------|-------------|----------|
| `npm run maestro:smoke` | Critical path tests | ~5 min |
| `npm run maestro:auth` | Authentication tests | ~15 min |
| `npm run maestro:seller` | Seller features | ~20 min |
| `npm run maestro:customer` | Customer features | ~15 min |
| `npm run maestro:regression` | Full test suite | ~45 min |
| `npm run maestro:quick` | Essential tests | ~5 min |
| `npm run maestro:debug` | Debug mode | Varies |

### Running Single Test

```bash
# Run specific test file
maestro test maestro/tests/auth/login.yaml

# Run with verbose output
maestro test --debug maestro/tests/auth/login.yaml

# Interactive mode for inspection
maestro studio
```

## Project Structure

```
mobile_automation_test/
├── maestro/                     # Maestro test files
│   ├── .maestro/
│   │   └── config.yaml          # Workspace config
│   ├── config/
│   │   └── maestro.yaml         # Global configuration
│   ├── flows/                   # Reusable flows
│   │   ├── login-flow.yaml
│   │   └── seller-login-flow.yaml
│   ├── tests/                   # Test files
│   │   ├── auth/               # Authentication tests
│   │   ├── seller/             # Seller feature tests
│   │   ├── product/            # Product browsing
│   │   └── cart/               # Shopping cart
│   └── test-suites.yaml        # Test suite definitions
├── scripts/                     # Helper scripts
│   ├── setup-maestro.sh
│   └── run-maestro-tests.sh
├── __tests__/                   # Unit tests (Jest)
├── api-tests/                   # API tests (Jest)
└── package.json
```

## Test Users

| Username | Password | Role |
|----------|----------|------|
| test_customer | 12345678 | CUSTOMER |
| test_seller | 12345678 | SELLER |
| test_dual | 12345678 | DUAL |

## Writing Tests

### Basic Test Structure

```yaml
appId: com.ceramicmarketplace.app
name: "Test Name"
tags:
  - smoke
  - auth
---
- launchApp:
    clearState: true
- tapOn:
    id: "elementId"
- inputText: "text to type"
- assertVisible:
    text: "Expected text"
```

### Common Commands

```yaml
# Tap element
- tapOn:
    id: "buttonId"

# Type text
- inputText: "text"

# Assert visible
- assertVisible:
    text: "Expected"

# Take screenshot
- takeScreenshot: "step-name"
```

## Debugging

### Using Maestro Studio

```bash
maestro studio
```
Interactive tool to inspect app and test commands.

### Debug Mode

```bash
npm run maestro:debug
```

### Taking Screenshots

Add screenshots at key points:
```yaml
- takeScreenshot: "before-action"
- tapOn:
    id: "submitButton"
- takeScreenshot: "after-action"
```

## Troubleshooting

### "Java 17 or higher is required"

```bash
sudo apt install openjdk-17-jdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

### "No connected devices"

```bash
# Check emulator is running
adb devices

# Start emulator
emulator -avd <avd-name>
```

### "Element not found"

1. Use Maestro Studio: `maestro studio`
2. Verify testID in app code
3. Try different selectors (text, id, index)

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Install Maestro
  run: |
    curl -Ls "https://get.maestro.mobile.dev" | bash
    echo "$HOME/.maestro/bin" >> $GITHUB_PATH

- name: Run Tests
  run: |
    maestro test --format junit --output results.xml maestro/tests/
```

## Additional Commands

```bash
# Unit tests
npm run test:unit

# API tests
npm run test:api

# Lint
npm run lint
```

## Documentation

- [MAESTRO_GUIDE.md](MAESTRO_GUIDE.md) - Detailed Maestro guide
- [Maestro Documentation](https://maestro.mobile.dev/docs)

---

**Note**: Ensure the Android emulator is running and the mobile app is installed before running tests.
