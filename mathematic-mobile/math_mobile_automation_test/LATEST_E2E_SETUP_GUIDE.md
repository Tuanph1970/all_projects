# Maestro E2E Testing Setup Guide

## Complete Setup Guide for Mathematics Solver Mobile App

This guide walks you through setting up and running Maestro E2E tests for the Mathematics Solver mobile application.

## Prerequisites

### 1. Java 17+

Maestro requires Java 17 or higher.

**Check Java version:**
```bash
java -version
```

**Install Java 17:**
```bash
# Using the setup script
./scripts/install-java17.sh

# Or manually on Ubuntu/Debian
sudo apt update
sudo apt install openjdk-17-jdk

# Or on macOS with Homebrew
brew install openjdk@17
```

### 2. Android SDK

**Install Android Studio** from https://developer.android.com/studio

**Set ANDROID_HOME:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/emulator
```

**Verify installation:**
```bash
adb version
emulator -list-avds
```

### 3. Node.js 18+

```bash
node --version
npm --version
```

## Installation Steps

### Step 1: Install Project Dependencies

```bash
cd math_mobile_automation_test
npm install
```

### Step 2: Setup Maestro

```bash
npm run maestro:setup
```

This will:
- Download Maestro CLI
- Add it to your PATH
- Verify installation

### Step 3: Create/Start Android Emulator

**Using Android Studio:**
1. Open Android Studio
2. Go to AVD Manager
3. Create or start an emulator (Pixel 6 API 33+ recommended)

**Using command line:**
```bash
# List available AVDs
emulator -list-avds

# Start emulator
emulator -avd <your-avd-name>
```

**Verify device:**
```bash
adb devices
```

Expected output:
```
List of devices attached
emulator-5554    device
```

### Step 4: Install Mathematics Solver App

**Option A: Using Expo Go (Development)**

1. Install Expo Go on emulator from Play Store
2. Start Expo dev server:
   ```bash
   cd ../frontend
   npm install
   npx expo start --android
   ```

**Option B: Build and Install APK**

```bash
cd ../frontend
npx expo build:android
adb install app-release.apk
```

## Running Tests

### Run All Tests

```bash
npm run maestro:test
```

### Run Specific Test Suites

```bash
# Smoke tests (quick)
npm run maestro:smoke

# Authentication tests
npm run maestro:auth

# Problem solving tests
npm run maestro:problem

# Full regression
npm run maestro:regression
```

### Run Individual Test Flows

```bash
# Login flow
maestro test maestro/flows/login-flow.yaml

# Registration flow
maestro test maestro/flows/register-flow.yaml

# Capture and solve
maestro test maestro/flows/capture-and-solve-flow.yaml
```

### Debug Mode

```bash
# Run with debug output
maestro test maestro/flows/login-flow.yaml --debug

# Verbose output
export MAESTRO_VERBOSE=true
maestro test maestro/flows/login-flow.yaml
```

## Test Flow Examples

### Login Flow

```yaml
# maestro/flows/login-flow.yaml
appId: com.mathematics.solver
env:
  USERNAME: test_user
  PASSWORD: Test@12345678

---
- tapOn:
    id: "login-email-input"
- inputText: ${USERNAME}

- tapOn:
    id: "login-password-input"
- inputText: ${PASSWORD}

- tapOn:
    id: "login-button"

- assertVisible:
    id: "home-screen"
    timeout: 10000
```

### Running with Custom Credentials

```bash
USERNAME=custom_user PASSWORD=CustomPass123 maestro test maestro/flows/login-flow.yaml
```

## Troubleshooting

### Issue: "Maestro command not found"

**Solution:**
```bash
# Add Maestro to PATH
export PATH="$HOME/.maestro/bin:$PATH"

# Add to ~/.bashrc for persistence
echo 'export PATH="$HOME/.maestro/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Issue: "No devices found"

**Solution:**
```bash
# Check ADB
adb devices

# Restart ADB server
adb kill-server
adb start-server

# Check again
adb devices
```

### Issue: "App not installed"

**Solution:**
1. Ensure app is built for the correct architecture
2. Install manually:
   ```bash
   adb install -r path/to/app.apk
   ```

### Issue: "Test fails on specific screen"

**Solution:**
1. Check testID matches app components
2. Increase timeout:
   ```yaml
   - assertVisible:
       id: "home-screen"
       timeout: 15000  # Increase timeout
   ```

### Issue: "API tests failing"

**Solution:**
```bash
# Ensure backend is running
cd ../backend
dotnet run

# Or use Docker
docker-compose up backend-api

# Test API directly
curl http://localhost:8001/health
```

## Advanced Configuration

### Custom Environment Variables

Create `.env` file:
```bash
API_BASE_URL=http://localhost:8001
ML_SERVICE_URL=http://localhost:8002
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=Test@12345678
```

### Parallel Test Execution

```bash
# Run multiple flows in parallel
maestro test maestro/flows/login-flow.yaml &
maestro test maestro/flows/register-flow.yaml &
wait
```

### Screenshots and Recording

```bash
# Take screenshot during test
maestro take-screenshot screenshot.png

# Record video (requires additional setup)
maestro record video.mp4
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          java-version: '17'
          distribution: 'temurin'
      
      - name: Setup Android
        uses: android-actions/setup-android@v2
      
      - name: Install Dependencies
        run: npm install
      
      - name: Setup Maestro
        run: npm run maestro:setup
      
      - name: Run Tests
        run: npm run maestro:test
```

## Best Practices

1. **Keep tests independent**: Each test should be able to run alone
2. **Use meaningful testIDs**: Consistent naming convention
3. **Handle errors gracefully**: Use `optional: true` when appropriate
4. **Add proper waits**: Use `waitForAnimationToEnd` instead of fixed delays
5. **Clean up test data**: Remove test users/problems after tests
6. **Document test flows**: Add comments in YAML files

## Resources

- [Maestro Documentation](https://maestro.mobile.dev/)
- [Maestro YAML Reference](https://maestro.mobile.dev/api-reference/yaml-syntax)
- [Android Emulator Setup](https://developer.android.com/studio/run/managing-avds)

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review Maestro documentation
3. Check project README

---

Last Updated: 2026-03-06
