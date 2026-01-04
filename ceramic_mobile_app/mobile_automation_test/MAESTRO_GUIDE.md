# Maestro Testing Guide for Ceramic Mobile App

## Overview

This guide documents the Maestro setup for mobile automation testing. Maestro provides a simple, maintainable approach to mobile testing with excellent support for emulators and real devices.

## Why Maestro?

- **Simpler Setup**: No complex build configurations or native dependencies
- **Better Stability**: More reliable element detection and interactions
- **Cross-Platform**: Same tests work on both iOS and Android
- **Human-Readable**: YAML-based test files are easy to understand
- **Fast Iteration**: No app rebuilds required for test changes
- **Great Debugging**: Built-in screenshot and video recording capabilities

## Installation

### Prerequisites

1. **Java 17 or higher** (Required by Maestro)
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

### Install Maestro

Run the setup script:
```bash
npm run maestro:setup
# or
./scripts/setup-maestro.sh
```

This will:
- Install Maestro CLI
- Add Maestro to your PATH
- Verify the installation

### Manual Installation (if needed)

**Linux:**
```bash
curl -Ls "https://get.maestro.mobile.dev" | bash
export PATH="$HOME/.maestro/bin:$PATH"
```

**macOS:**
```bash
brew tap mobile-dev-inc/maestro
brew install maestro
```

## Project Structure

```
maestro/
├── .maestro/
│   └── config.yaml         # Workspace configuration
├── config/
│   └── maestro.yaml        # Global test configuration
├── flows/
│   └── login-flow.yaml     # Reusable test flows
└── tests/
    ├── auth/
    │   ├── login.yaml
    │   ├── login-failure.yaml
    │   └── register.yaml
    ├── product/
    │   └── browse-products.yaml
    └── cart/
        └── add-to-cart.yaml
```

## Writing Tests

### Basic Test Structure

```yaml
appId: com.ceramicapp
name: "Test Name"
tags:
  - smoke
  - auth
---
# Test steps go here
- launchApp:
    clearState: true
- tapOn:
    id: "elementId"
- inputText: "text to type"
- assertVisible:
    text: "Expected text"
```

### Common Commands

1. **App Control**
   ```yaml
   - launchApp:
       clearState: true  # Fresh app state
       permissions:
         notifications: allow
   ```

2. **Interactions**
   ```yaml
   - tapOn:
       id: "buttonId"
   - inputText: "text"
   - scroll:
       direction: DOWN
   - swipe:
       direction: LEFT
   ```

3. **Assertions**
   ```yaml
   - assertVisible:
       text: "Expected text"
       timeout: 10000
   - assertNotVisible:
       id: "elementId"
   ```

4. **Screenshots**
   ```yaml
   - takeScreenshot: "screenshot-name"
   ```

### Using TestIDs

Maestro can find elements by:
- `id`: TestID/accessibility ID (recommended)
- `text`: Visible text content
- `index`: Position in list

Example:
```yaml
- tapOn:
    id: "loginButton"  # Uses testID
- tapOn:
    text: "Login"      # Uses visible text
```

### Reusable Flows

Create reusable flows in `maestro/flows/`:
```yaml
# flows/login-flow.yaml
- tapOn:
    id: "usernameInput"
- inputText: ${USERNAME}
# ... more steps
```

Use in tests:
```yaml
- runFlow: flows/login-flow.yaml
```

## Running Tests

### Quick Test (Emulator already running)

```bash
# Run all tests
npm run maestro:quick

# Run specific test category
npm run maestro:quick auth
npm run maestro:quick product

# Run single test file
./scripts/maestro-quick-test.sh single maestro/tests/auth/login.yaml
```

### Full Test Run (Starts emulator, backend, etc.)

```bash
# Run all tests
npm run maestro:test

# Run smoke tests only
npm run maestro:smoke

# Run auth tests only  
npm run maestro:auth
```

### Debug Mode

```bash
npm run maestro:debug
```

### Command Line Options

```bash
# Run with specific tags
maestro test --tags smoke tests/

# Output JUnit results
maestro test --format junit --output results.xml tests/

# Run with video recording
maestro record tests/auth/login.yaml

# Interactive mode
maestro studio
```

## Emulator Setup

### Using Existing Emulator

If you already have an emulator running:
```bash
# Check connected devices
adb devices

# Run tests directly
npm run maestro:quick
```

### Starting Emulator

The full test script will start an emulator if needed:
```bash
# Set emulator name (optional)
export EMULATOR_NAME="Pixel_4_API_30"

# Run tests (will start emulator)
npm run maestro:test
```

### Creating New Emulator

```bash
# List available system images
sdkmanager --list | grep system-images

# Install system image
sdkmanager "system-images;android-30;google_apis;x86_64"

# Create AVD
avdmanager create avd -n Pixel_4_API_30 -k "system-images;android-30;google_apis;x86_64" -d pixel_4

# Start emulator
emulator -avd Pixel_4_API_30
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Install Maestro
  run: |
    curl -Ls "https://get.maestro.mobile.dev" | bash
    echo "$HOME/.maestro/bin" >> $GITHUB_PATH

- name: Run Maestro Tests
  run: |
    maestro test --format junit --output test-results.xml maestro/tests/
```

## Troubleshooting

### Common Issues

1. **"Java 17 or higher is required"**
   - Install Java 17: `sudo apt install openjdk-17-jdk`
   - Set JAVA_HOME: `export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64`

2. **"No connected devices"**
   - Check emulator is running: `adb devices`
   - Start emulator: `emulator -avd <name>`

3. **"Element not found"**
   - Verify testID in app code
   - Use Maestro Studio to inspect: `maestro studio`
   - Try different selectors (text, id, index)

4. **"Timeout waiting for element"**
   - Increase timeout: `timeout: 30000`
   - Add wait commands: `waitForAnimationToEnd`
   - Check if element is scrolled out of view

### Debugging Tips

1. **Use Maestro Studio**
   ```bash
   maestro studio
   ```
   Interactive tool to inspect app and test commands

2. **Enable Debug Output**
   ```bash
   maestro test --debug tests/auth/login.yaml
   ```

3. **Take Screenshots**
   Add screenshots at key points to debug failures

4. **Use Assertions**
   Add assertions to verify app state at each step

## Best Practices

1. **Use TestIDs**: Prefer `id` over `text` for stability
2. **Add Waits**: Use `waitForAnimationToEnd` after navigations
3. **Handle Optionals**: Use `optional: true` for elements that may not appear
4. **Tag Tests**: Use tags for test organization
5. **Take Screenshots**: Capture state for debugging
6. **Reuse Flows**: Extract common patterns to reusable flows
7. **Test Data**: Use environment variables for test data

## Additional Resources

- [Maestro Documentation](https://maestro.mobile.dev/docs)
- [Maestro GitHub](https://github.com/mobile-dev-inc/maestro)
- [YAML Syntax Guide](https://maestro.mobile.dev/syntax)
- [Best Practices](https://maestro.mobile.dev/best-practices)

## Support

For issues or questions:
1. Check this guide
2. Run tests in debug mode
3. Use Maestro Studio for inspection
4. Check Maestro documentation
5. Review test output and screenshots