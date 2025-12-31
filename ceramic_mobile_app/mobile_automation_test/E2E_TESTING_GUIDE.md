# E2E Testing Guide - Ceramic Mobile App

This guide explains how to set up and run E2E (End-to-End) tests for the Ceramic Mobile App on Ubuntu 22.04.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Automated Setup)](#quick-start-automated-setup)
3. [Manual Setup](#manual-setup)
4. [Running E2E Tests](#running-e2e-tests)
5. [Test Configuration](#test-configuration)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Ubuntu 22.04 LTS
- At least 16GB RAM (recommended for emulator)
- 50GB free disk space
- CPU with virtualization support (Intel VT-x or AMD-V)
- Backend API server running (already deployed)

### Check Virtualization Support

```bash
# Check if KVM is available
egrep -c '(vmx|svm)' /proc/cpuinfo
# Output should be > 0

# Check KVM module
lsmod | grep kvm
```

---

## Quick Start (Automated Setup)

The easiest way to set up the E2E testing environment is to use the provided setup script.

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd ceramic_mobile_app
```

### Step 2: Run the Setup Script

```bash
chmod +x mobile_automation_test/scripts/setup-e2e-ubuntu.sh
./mobile_automation_test/scripts/setup-e2e-ubuntu.sh
```

The script will install:
- Node.js 20
- Java 17 (OpenJDK)
- Android SDK (API 35)
- Android Emulator (Pixel 4 API 35)
- Detox CLI

### Step 3: Restart Terminal

```bash
source ~/.bashrc
```

### Step 4: Install Project Dependencies

```bash
# Install frontend dependencies
cd front_end
npm install

# Build debug APK
cd android
./gradlew assembleDebug assembleAndroidTest -DtestBuildType=debug
cd ../..

# Install test dependencies
cd mobile_automation_test
npm install
```

### Step 5: Run Tests

```bash
# Start emulator
emulator -avd Pixel_4_API_35 &

# Wait for emulator to boot (check with: adb devices)
adb wait-for-device

# Run E2E tests
npx detox test --configuration android.emu.debug
```

---

## Manual Setup

If you prefer to install components manually, follow these steps:

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y curl wget git unzip openjdk-17-jdk \
    qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils

# Add user to kvm group
sudo adduser $USER kvm
```

### 2. Install Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify
node -v  # Should show v20.x.x
npm -v   # Should show 10.x.x
```

### 3. Install Android SDK

```bash
# Create SDK directory
mkdir -p ~/Android/Sdk/cmdline-tools

# Download command-line tools
wget -O /tmp/cmdline-tools.zip \
    https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip

# Extract
unzip /tmp/cmdline-tools.zip -d /tmp/
mv /tmp/cmdline-tools ~/Android/Sdk/cmdline-tools/latest

# Set environment variables (add to ~/.bashrc)
export ANDROID_HOME="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

# Apply changes
source ~/.bashrc

# Accept licenses
yes | sdkmanager --licenses

# Install required components
sdkmanager "platform-tools" \
    "platforms;android-35" \
    "build-tools;35.0.0" \
    "emulator" \
    "system-images;android-35;google_apis;x86_64"
```

### 4. Create Android Emulator

```bash
# Create AVD
avdmanager create avd \
    --name "Pixel_4_API_35" \
    --device "pixel_4" \
    --package "system-images;android-35;google_apis;x86_64"

# Start emulator
emulator -avd Pixel_4_API_35 &
```

### 5. Install Detox CLI

```bash
sudo npm install -g detox-cli
```

### 6. Set Java Environment

```bash
# Add to ~/.bashrc
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"

source ~/.bashrc
```

---

## Running E2E Tests

### Start the Emulator

```bash
# Start emulator in background
emulator -avd Pixel_4_API_35 &

# Or with specific options
emulator -avd Pixel_4_API_35 -no-snapshot-load -gpu swiftshader_indirect &

# Wait for boot
adb wait-for-device
adb shell getprop sys.boot_completed  # Should return "1"
```

### Start Metro Bundler (for Debug builds)

```bash
cd front_end
npm start
```

### Set Up Port Forwarding

```bash
# Forward Metro bundler port
adb reverse tcp:8081 tcp:8081

# Forward API server port (if needed)
adb reverse tcp:8002 tcp:8002
```

### Run All Tests

```bash
cd mobile_automation_test
npx detox test --configuration android.emu.debug
```

### Run Specific Test Files

```bash
# Run only login tests
npx detox test --configuration android.emu.debug e2e/auth/login.test.js

# Run only register tests
npx detox test --configuration android.emu.debug e2e/auth/register.test.js
```

### Run Tests with Verbose Output

```bash
npx detox test --configuration android.emu.debug --loglevel verbose
```

### Run Tests and Keep Artifacts

```bash
npx detox test --configuration android.emu.debug --artifacts-location ./test-artifacts --record-videos all
```

---

## Test Configuration

### API Configuration

Edit `e2e/config/testConfig.js` to update the API server URL:

```javascript
module.exports = {
  api: {
    baseUrl: process.env.API_BASE_URL || 'http://your-api-server:8002',
    timeout: 10000,
  },
  // ...
};
```

### Detox Configuration

The Detox configuration is in `.detoxrc.js`:

```javascript
module.exports = {
  testRunner: {
    args: {
      config: 'e2e/jest.config.js',
    },
  },
  apps: {
    'android.debug': {
      type: 'android.apk',
      binaryPath: '../front_end/android/app/build/outputs/apk/debug/app-debug.apk',
      testBinaryPath: '../front_end/android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk',
      build: 'cd ../front_end/android && ./gradlew assembleDebug assembleAndroidTest -DtestBuildType=debug',
    },
  },
  devices: {
    emulator: {
      type: 'android.emulator',
      device: {
        avdName: 'Pixel_4_API_35',  // Change this to match your emulator
      },
    },
  },
  configurations: {
    'android.emu.debug': {
      device: 'emulator',
      app: 'android.debug',
    },
  },
};
```

### Test Users

Test user credentials are defined in `e2e/config/testConfig.js`:

```javascript
testUsers: {
  customer: {
    username: 'test_customer',
    email: 'test_customer@example.com',
    password: '12345678',
  },
  seller: {
    username: 'test_seller',
    email: 'test_seller@example.com',
    password: '12345678',
  },
}
```

---

## Troubleshooting

### Emulator Issues

#### Emulator won't start
```bash
# Check if KVM is available
kvm-ok

# If not, enable virtualization in BIOS
# Or use software rendering:
emulator -avd Pixel_4_API_35 -gpu swiftshader_indirect
```

#### Emulator is too slow
```bash
# Increase RAM in emulator config
# Edit: ~/.android/avd/Pixel_4_API_35.avd/config.ini
hw.ramSize=4096
hw.gpu.enabled=yes
hw.gpu.mode=auto
```

### Build Issues

#### Gradle build fails
```bash
# Clean and rebuild
cd front_end/android
./gradlew clean
./gradlew assembleDebug assembleAndroidTest -DtestBuildType=debug

# If Java version issues:
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

#### Out of memory
```bash
# Increase Gradle memory in gradle.properties
org.gradle.jvmargs=-Xmx4096m -XX:MaxMetaspaceSize=1024m
```

### Test Issues

#### Tests timeout waiting for element
- Increase timeout in test config
- Check if element testID matches
- Take screenshots to debug:
```javascript
await device.takeScreenshot('debug-screenshot');
```

#### App doesn't connect to API
```bash
# Check port forwarding
adb reverse tcp:8002 tcp:8002

# Verify API is reachable from emulator
adb shell curl http://10.0.2.2:8002/health
```

#### Metro bundler connection issues
```bash
# Ensure Metro is running
cd front_end && npm start

# Set up port forwarding
adb reverse tcp:8081 tcp:8081
```

### Detox Issues

#### Detox can't find the app
```bash
# Rebuild the app
cd front_end/android
./gradlew assembleDebug assembleAndroidTest -DtestBuildType=debug
```

#### Detox synchronization issues
```bash
# Disable synchronization for specific operations
await device.disableSynchronization();
// ... your actions
await device.enableSynchronization();
```

---

## Useful Commands Reference

```bash
# List available emulators
emulator -list-avds

# List connected devices
adb devices

# Install APK manually
adb install -r path/to/app.apk

# View device logs
adb logcat

# Clear app data
adb shell pm clear com.ceramicmarketplace.app

# Take screenshot
adb exec-out screencap -p > screenshot.png

# Kill emulator
adb emu kill
```

---

## Project Structure

```
ceramic_mobile_app/
├── front_end/                 # React Native app
│   ├── android/              # Android native code
│   │   ├── app/
│   │   │   └── build/outputs/apk/  # Built APKs
│   │   └── gradlew           # Gradle wrapper
│   └── src/                  # App source code
│
└── mobile_automation_test/   # E2E tests
    ├── e2e/
    │   ├── auth/             # Authentication tests
    │   │   ├── login.test.js
    │   │   └── register.test.js
    │   ├── config/
    │   │   └── testConfig.js # Test configuration
    │   └── helpers/
    │       └── testHelpers.js
    ├── scripts/
    │   └── setup-e2e-ubuntu.sh
    ├── .detoxrc.js           # Detox configuration
    └── package.json
```

---

## Support

If you encounter issues not covered in this guide:

1. Check the Detox documentation: https://wix.github.io/Detox/
2. Check React Native documentation: https://reactnative.dev/
3. Review the test logs for error details
4. Take screenshots during test failures for debugging
