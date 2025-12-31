# Mobile Automation Test Setup Guide

Complete guide to set up and run E2E mobile automation tests from a fresh installation.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Manual Setup](#manual-setup)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Operating System**: Ubuntu 20.04+ or macOS
2. **Node.js**: v18.x or v20.x
3. **JDK**: OpenJDK 11 (NOT JDK 17 or higher)
4. **Android SDK**: Command line tools
5. **Git**: For cloning repository

### System Requirements

- **RAM**: Minimum 8GB (16GB recommended)
- **Disk Space**: At least 20GB free
- **CPU**: Multi-core processor recommended

---

## Quick Start

### Using Automated Setup Script

```bash
# 1. Clone the repository
git clone <repository-url>
cd ceramic_mobile_app/mobile_automation_test

# 2. Make setup script executable
chmod +x setup.sh

# 3. Run automated setup
./setup.sh

# 4. Follow the prompts and wait for setup to complete

# 5. Run tests
./run-tests.sh
```

---

## Manual Setup

If you prefer to set up manually or if the automated script fails:

### Step 1: Install Node.js

```bash
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20

# Verify installation
node --version  # Should show v20.x.x
npm --version   # Should show 10.x.x
```

### Step 2: Install JDK 11

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install openjdk-11-jdk -y

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Verify installation
java -version  # Should show openjdk version "11.x.x"
```

### Step 3: Install Android SDK

```bash
# Create Android SDK directory
mkdir -p ~/Android/Sdk
cd ~/Android/Sdk

# Download command line tools
wget https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip
unzip commandlinetools-linux-9477386_latest.zip
mkdir -p cmdline-tools/latest
mv cmdline-tools/* cmdline-tools/latest/

# Set environment variables
echo 'export ANDROID_HOME=$HOME/Android/Sdk' >> ~/.bashrc
echo 'export PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$PATH' >> ~/.bashrc
echo 'export PATH=$ANDROID_HOME/platform-tools:$PATH' >> ~/.bashrc
echo 'export PATH=$ANDROID_HOME/emulator:$PATH' >> ~/.bashrc
source ~/.bashrc

# Accept licenses and install packages
yes | sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-33" "build-tools;33.0.0" \
  "system-images;android-33;google_apis;x86_64" "emulator"
```

### Step 4: Create Android Emulator

```bash
# Create emulator (Pixel 3a API 33)
avdmanager create avd -n Pixel_3a_API_36_extension_level_17_x86_64 \
  -k "system-images;android-33;google_apis;x86_64" \
  -d "pixel_3a" \
  --force

# Verify emulator was created
emulator -list-avds
```

### Step 5: Install Project Dependencies

```bash
# Navigate to mobile automation test directory
cd /path/to/ceramic_mobile_app/mobile_automation_test

# Install dependencies
npm install

# Navigate to frontend and install
cd ../front_end
npm install

# Return to test directory
cd ../mobile_automation_test
```

### Step 6: Configure Environment

```bash
# Create .env file if needed
cat > .env << 'EOF'
# Backend API Configuration
API_BASE_URL=http://10.0.2.2:8002
API_TIMEOUT=30000

# Test Configuration
TEST_TIMEOUT=120000
EOF
```

### Step 7: Set Up Test Database

```bash
# Navigate to backend directory
cd ../back_end

# Run SQL script to create test users
mysql -h 127.0.0.1 -P 3308 -u ceramic_user -p'Mysql_2025' ceramic_marketplace < insert_test_users.sql

# Verify users were created
mysql -h 127.0.0.1 -P 3308 -u ceramic_user -p'Mysql_2025' ceramic_marketplace \
  -e "SELECT id, username, email, role FROM users WHERE id IN (500, 501, 502);"
```

---

## Running Tests

### Start Backend Server

```bash
# In a separate terminal
cd ceramic_mobile_app/back_end
gunicorn app.main:app --workers 4 --bind 0.0.0.0:8002
```

### Option 1: Run All Tests

```bash
cd ceramic_mobile_app/mobile_automation_test

# Run all tests
./run-tests.sh

# Or manually:
npx detox test --configuration android.emu.release
```

### Option 2: Run Specific Test File

```bash
# Run only login tests
npx detox test --configuration android.emu.release e2e/auth/login.test.js

# Run only registration tests
npx detox test --configuration android.emu.release e2e/auth/register.test.js
```

### Option 3: Run Single Test

```bash
# Run specific test by name
npx detox test --configuration android.emu.release \
  --testNamePattern="should login successfully with valid credentials"
```

### Debug Mode

```bash
# Run with debug build (slower but shows console logs)
npx detox test --configuration android.emu.debug e2e/auth/login.test.js
```

---

## Test Configuration

### Test Users

Three test users are available:

| Username | Password | Role | ID |
|----------|----------|------|-----|
| test_customer | 12345678 | CUSTOMER | 500 |
| test_seller | 12345678 | SELLER | 501 |
| test_dual | 12345678 | DUAL | 502 |

### API Endpoints

- **Base URL**: `http://10.0.2.2:8002` (emulator → localhost)
- **Login**: `POST /api/v1/auth/login`
- **Register**: `POST /api/v1/auth/register`
- **Me**: `GET /api/v1/auth/me`

### Timeouts

- **Default**: 120000ms (2 minutes)
- **Short**: 5000ms
- **Medium**: 10000ms
- **Long**: 20000ms

---

## Troubleshooting

### Issue: "JAVA_HOME is set to an invalid directory"

**Solution**:
```bash
# Find Java installation
update-alternatives --list java

# Set JAVA_HOME (adjust path based on output above)
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

### Issue: "SDK location not found"

**Solution**:
```bash
# Create local.properties file
echo "sdk.dir=$HOME/Android/Sdk" > front_end/android/local.properties
```

### Issue: "Emulator not found"

**Solution**:
```bash
# List available emulators
emulator -list-avds

# If empty, create new emulator
avdmanager create avd -n Pixel_3a_API_36_extension_level_17_x86_64 \
  -k "system-images;android-33;google_apis;x86_64" \
  -d "pixel_3a" --force
```

### Issue: "Connection refused" or "Network error"

**Solution**:
```bash
# 1. Verify backend is running
curl http://localhost:8002/api/v1/health

# 2. From emulator, test connectivity
adb shell
curl http://10.0.2.2:8002/api/v1/health

# 3. Check firewall settings
sudo ufw allow 8002
```

### Issue: "Build failed" or "Gradle error"

**Solution**:
```bash
# Clean build
cd front_end/android
./gradlew clean

# Rebuild
./gradlew assembleRelease assembleAndroidTest -DtestBuildType=release
```

### Issue: Tests timing out

**Solution**:
```bash
# 1. Use release build (faster)
npx detox test --configuration android.emu.release

# 2. Increase timeout in config
# Edit e2e/config/testConfig.js and increase timeout values

# 3. Check emulator performance
emulator @Pixel_3a_API_36_extension_level_17_x86_64 -gpu host
```

### Issue: "Port already in use"

**Solution**:
```bash
# Find process using port 8002
lsof -i :8002

# Kill the process
kill -9 <PID>

# Or kill all gunicorn processes
pkill -9 gunicorn
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Mobile E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Setup JDK 11
        uses: actions/setup-java@v3
        with:
          distribution: 'adopt'
          java-version: '11'

      - name: Setup Android SDK
        uses: android-actions/setup-android@v2

      - name: Install dependencies
        run: |
          cd mobile_automation_test
          npm install
          cd ../front_end
          npm install

      - name: Run tests
        run: |
          cd mobile_automation_test
          ./run-tests.sh

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: mobile_automation_test/artifacts/
```

---

## Directory Structure

```
ceramic_mobile_app/
├── mobile_automation_test/          # Test directory
│   ├── e2e/                        # Test files
│   │   ├── auth/                   # Authentication tests
│   │   │   ├── login.test.js
│   │   │   └── register.test.js
│   │   ├── config/                 # Test configuration
│   │   │   └── testConfig.js
│   │   └── helpers/                # Test utilities
│   │       └── testHelpers.js
│   ├── artifacts/                  # Screenshots, logs
│   ├── .detoxrc.js                # Detox configuration
│   ├── package.json
│   ├── setup.sh                   # Automated setup script
│   ├── run-tests.sh               # Test execution script
│   └── SETUP_GUIDE.md            # This file
├── front_end/                     # React Native app
│   └── android/                   # Android build files
└── back_end/                      # FastAPI backend
    └── insert_test_users.sql     # Test user SQL
```

---

## Support

For issues and questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review test logs in `artifacts/` directory
- Check Detox documentation: https://wix.github.io/Detox/

---

## License

[Your License Here]
