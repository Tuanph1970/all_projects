# Mobile Automation Test

End-to-End (E2E) automated testing for the Ceramic Mobile App using Detox.

## Quick Start

### First Time Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd ceramic_mobile_app/mobile_automation_test

# 2. Run automated setup
chmod +x setup.sh
./setup.sh

# 3. Start backend server (in separate terminal)
cd ../back_end
gunicorn app.main:app --workers 4 --bind 0.0.0.0:8002

# 4. Run tests
./run-tests.sh
```

## Usage

### Run All Tests

```bash
./run-tests.sh
```

### Run Specific Tests

```bash
# Login tests only
./run-tests.sh --file e2e/auth/login.test.js

# Registration tests only
./run-tests.sh --file e2e/auth/register.test.js

# Specific test by name
./run-tests.sh --pattern "should login successfully"
```

### Debug Mode

```bash
# Run with console logs (slower)
./run-tests.sh --debug

# Debug specific test
./run-tests.sh --debug --file e2e/auth/login.test.js
```

### Advanced Options

```bash
# Start backend automatically
./run-tests.sh --backend

# Clean artifacts before running
./run-tests.sh --cleanup

# Combine options
./run-tests.sh --debug --backend --cleanup --file e2e/auth/login.test.js
```

### Get Help

```bash
./run-tests.sh --help
```

## Test Users

| Username | Password | Role |
|----------|----------|------|
| test_customer | 12345678 | CUSTOMER |
| test_seller | 12345678 | SELLER |
| test_dual | 12345678 | DUAL |

## Project Structure

```
mobile_automation_test/
├── e2e/                          # Test files
│   ├── auth/                     # Authentication tests
│   │   ├── login.test.js        # Login flow tests
│   │   └── register.test.js     # Registration tests
│   ├── config/                   # Test configuration
│   │   └── testConfig.js        # Test settings & users
│   └── helpers/                  # Test utilities
│       └── testHelpers.js       # Helper functions
├── artifacts/                    # Test outputs (auto-generated)
│   ├── *.png                    # Screenshots
│   └── *.log                    # Test logs
├── setup.sh                     # Automated setup script
├── run-tests.sh                 # Test runner script
├── SETUP_GUIDE.md              # Detailed setup instructions
└── README.md                    # This file
```

## Prerequisites

- **Node.js**: 18.x or 20.x
- **JDK**: OpenJDK 11 (required - NOT 17+)
- **Android SDK**: Command line tools
- **System**: Ubuntu 20.04+ or macOS
- **RAM**: 8GB minimum (16GB recommended)

## Manual Commands

If you prefer not to use the scripts:

```bash
# Build app
cd ../front_end/android
./gradlew assembleRelease assembleAndroidTest -DtestBuildType=release

# Run tests
cd ../../mobile_automation_test
npx detox test --configuration android.emu.release

# Run specific test file
npx detox test --configuration android.emu.release e2e/auth/login.test.js

# Run with pattern
npx detox test --configuration android.emu.release --testNamePattern="should login"
```

## Common Issues

### "JAVA_HOME is set to an invalid directory"

```bash
# Install JDK 11
sudo apt install openjdk-11-jdk

# Set JAVA_HOME
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

### "Emulator not found"

```bash
# List emulators
emulator -list-avds

# Create if missing
./setup.sh
```

### "Connection refused"

```bash
# Check backend is running
curl http://localhost:8002/api/v1/health

# Start backend if needed
cd ../back_end
gunicorn app.main:app --workers 4 --bind 0.0.0.0:8002
```

### Tests timing out

```bash
# Use release build (faster)
./run-tests.sh

# Or explicitly
npx detox test --configuration android.emu.release
```

## Test Results

After running tests, check:

- **Console output**: Pass/fail status
- **Screenshots**: `artifacts/*.png`
- **Logs**: `artifacts/*.log`

## Documentation

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup instructions
- [Detox Documentation](https://wix.github.io/Detox/) - Official Detox docs

## Support

For detailed troubleshooting, see [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting)

---

**Note**: Always ensure the backend server is running before executing tests.
