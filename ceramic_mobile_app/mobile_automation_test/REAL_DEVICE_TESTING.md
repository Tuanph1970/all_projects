# Real Device Testing Guide

Complete guide for testing on real iOS and Android devices instead of emulators.

## Why Test on Real Devices?

**Emulator Limitations:**
- ❌ Performance doesn't match real hardware
- ❌ Missing sensors (GPS, accelerometer, camera)
- ❌ Different memory constraints
- ❌ Network conditions differ
- ❌ Touch vs mouse interactions

**Real Device Benefits:**
- ✅ Accurate performance metrics
- ✅ Real-world user experience
- ✅ True hardware capabilities
- ✅ Actual touch gestures
- ✅ Real network conditions

---

## Option 1: Local Physical Devices

### iOS Device Setup

#### Prerequisites:
```bash
# Install ios-deploy for device deployment
npm install -g ios-deploy

# Verify installation
ios-deploy --version
```

#### Configuration Steps:

1. **Connect iPhone via USB**

2. **Trust Computer on Device**
   - Unlock iPhone
   - Tap "Trust" when prompted

3. **Configure Xcode**
   ```bash
   # Open Xcode
   cd front_end/ios
   open CeramicMarketplace.xcworkspace

   # In Xcode:
   # 1. Select your device from device list
   # 2. Product > Destination > Your iPhone
   # 3. Signing & Capabilities > Select Team
   ```

4. **Build for Device**
   ```bash
   cd mobile_automation_test

   # Build iOS app for device
   detox build --configuration ios.device.debug
   ```

5. **Run Tests on Device**
   ```bash
   # Run all tests
   detox test --configuration ios.device.debug

   # Run specific test
   detox test e2e/auth/login.test.js --configuration ios.device.debug
   ```

#### Troubleshooting iOS:

**"Failed to install app":**
```bash
# Clean build
cd front_end/ios
rm -rf build DerivedData
cd ../../mobile_automation_test
detox build --configuration ios.device.debug
```

**"Code signing error":**
- Open Xcode
- Select your team under Signing & Capabilities
- Ensure provisioning profile is valid

**"Device not found":**
```bash
# List connected devices
xcrun xctrace list devices

# Verify device is connected
instruments -s devices
```

---

### Android Device Setup

#### Prerequisites:
```bash
# Enable ADB over USB
adb devices

# Should show your device:
# List of devices attached
# 1234567890ABCDEF    device
```

#### Configuration Steps:

1. **Enable Developer Options**
   - Settings > About Phone
   - Tap "Build Number" 7 times
   - Go back to Settings > Developer Options

2. **Enable USB Debugging**
   - Developer Options > USB Debugging (ON)
   - Allow USB debugging on popup

3. **Connect Device**
   ```bash
   # Connect via USB
   adb devices

   # Should show:
   # 1234567890ABCDEF    device
   ```

4. **Reverse Port for API**
   ```bash
   # Make localhost:8002 accessible from device
   adb reverse tcp:8002 tcp:8002
   ```

5. **Build for Device**
   ```bash
   cd mobile_automation_test

   # Build Android APK
   detox build --configuration android.device.debug
   ```

6. **Run Tests on Device**
   ```bash
   # Run all tests
   detox test --configuration android.device.debug

   # Run specific test
   detox test e2e/auth/login.test.js --configuration android.device.debug
   ```

#### Troubleshooting Android:

**"Device unauthorized":**
```bash
# Disconnect and reconnect USB
# Check device for authorization popup
adb devices

# If still unauthorized:
adb kill-server
adb start-server
adb devices
```

**"App not installed":**
```bash
# Uninstall old version
adb uninstall com.ceramicmarketplace

# Clean and rebuild
cd front_end/android
./gradlew clean
cd ../../mobile_automation_test
detox build --configuration android.device.debug
```

**"Port already in use":**
```bash
# Kill processes on port
lsof -ti:8002 | xargs kill -9

# Or use different port
adb reverse tcp:8003 tcp:8002
```

---

## Option 2: Cloud Device Testing

### Firebase Test Lab (Google)

**Best For:** Android testing at scale

#### Setup:
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize project
firebase init
```

#### Configuration:
```yaml
# firebase-test-lab.yml
platforms:
  - name: Android
    device: Pixel 3a
    versions: [30, 31]
    locales: [en, vi]
    orientations: [portrait, landscape]

test:
  type: instrumentation
  app: front_end/android/app/build/outputs/apk/debug/app-debug.apk
  test: front_end/android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
```

#### Run Tests:
```bash
# Build APKs
cd front_end/android
./gradlew assembleDebug assembleAndroidTest

# Upload and run
gcloud firebase test android run \
  --type instrumentation \
  --app app/build/outputs/apk/debug/app-debug.apk \
  --test app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk \
  --device model=Pixel3a,version=30,locale=en,orientation=portrait
```

**Pricing:**
- Free: 5 tests/day, 10 devices
- Paid: $5/device-hour

---

### BrowserStack (iOS + Android)

**Best For:** Cross-platform testing, CI/CD integration

#### Setup:
```bash
# Install BrowserStack Local
npm install -g browserstack-local

# Set credentials
export BROWSERSTACK_USERNAME=your_username
export BROWSERSTACK_ACCESS_KEY=your_key
```

#### Configuration:
```javascript
// browserstack.config.js
module.exports = {
  user: process.env.BROWSERSTACK_USERNAME,
  key: process.env.BROWSERSTACK_ACCESS_KEY,

  capabilities: [
    {
      device: 'iPhone 14',
      os_version: '16',
      app: 'bs://app_url_here'
    },
    {
      device: 'Google Pixel 7',
      os_version: '13.0',
      app: 'bs://app_url_here'
    }
  ]
};
```

#### Run Tests:
```bash
# Upload app
curl -u "$BROWSERSTACK_USERNAME:$BROWSERSTACK_ACCESS_KEY" \
  -X POST "https://api-cloud.browserstack.com/app-automate/upload" \
  -F "file=@front_end/android/app/build/outputs/apk/debug/app-debug.apk"

# Run tests
npm run test:browserstack
```

**Pricing:**
- Free: 100 min/month
- Paid: $29/user/month

---

### AWS Device Farm

**Best For:** Enterprise, large test suites

#### Setup:
```bash
# Install AWS CLI
pip install awscli

# Configure
aws configure
```

#### Run Tests:
```bash
# Create project
aws devicefarm create-project --name "Ceramic Marketplace"

# Upload app
aws devicefarm create-upload \
  --project-arn arn:aws:devicefarm:... \
  --name app-debug.apk \
  --type ANDROID_APP

# Schedule test run
aws devicefarm schedule-run \
  --project-arn arn:aws:devicefarm:... \
  --app-arn arn:aws:devicefarm:... \
  --device-pool-arn arn:aws:devicefarm:...
```

**Pricing:**
- Free: 1000 device minutes/month
- Paid: $0.17/device-minute

---

## Option 3: CI/CD Integration

### GitHub Actions with Real Devices

```yaml
# .github/workflows/test-real-devices.yml
name: Real Device Tests

on: [push, pull_request]

jobs:
  test-ios:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: |
          cd front_end
          npm install

      - name: Run tests on BrowserStack
        env:
          BROWSERSTACK_USERNAME: ${{ secrets.BROWSERSTACK_USERNAME }}
          BROWSERSTACK_ACCESS_KEY: ${{ secrets.BROWSERSTACK_ACCESS_KEY }}
        run: |
          npm run test:browserstack:ios

  test-android:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'zulu'
          java-version: '11'

      - name: Run tests on Firebase Test Lab
        run: |
          cd front_end/android
          ./gradlew assembleDebug assembleAndroidTest
          gcloud firebase test android run \
            --type instrumentation \
            --app app/build/outputs/apk/debug/app-debug.apk \
            --test app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
```

---

## Comparison Matrix

| Service | iOS | Android | Price | CI/CD | Best For |
|---------|-----|---------|-------|-------|----------|
| **Local Physical** | ✅ | ✅ | Free | ⚠️ | Development, debugging |
| **Firebase Test Lab** | ❌ | ✅ | Free tier | ✅ | Android-only projects |
| **BrowserStack** | ✅ | ✅ | $29/mo | ✅ | Cross-platform |
| **AWS Device Farm** | ✅ | ✅ | $0.17/min | ✅ | Enterprise, scale |
| **Sauce Labs** | ✅ | ✅ | $39/mo | ✅ | Comprehensive testing |

---

## Recommended Approach

### For Development:
1. **Local emulators** - Fast iteration (70% of testing)
2. **Local physical device** - Quick real-world validation (20%)
3. **Cloud devices** - Pre-release verification (10%)

### For CI/CD:
1. **Unit/Integration tests** - Every commit
2. **E2E on emulators** - Every PR
3. **E2E on real devices** - Before release

### Cost-Effective Strategy:
```bash
# Daily development: Free
- Local emulators + 1 physical device

# Weekly: Free
- Firebase Test Lab (Android)

# Pre-release: ~$50/month
- BrowserStack for iOS
- Firebase for Android
- CI/CD integration
```

---

## Quick Start Commands

```bash
# iOS Real Device
detox build --configuration ios.device.debug
detox test --configuration ios.device.debug

# Android Real Device
adb reverse tcp:8002 tcp:8002
detox build --configuration android.device.debug
detox test --configuration android.device.debug

# Firebase Test Lab
gcloud firebase test android run \
  --type instrumentation \
  --app path/to/app-debug.apk \
  --test path/to/app-debug-androidTest.apk \
  --device model=Pixel3a,version=30

# BrowserStack
export BROWSERSTACK_USERNAME=your_user
export BROWSERSTACK_ACCESS_KEY=your_key
npm run test:browserstack
```
