# E2E Testing Setup Guide

## Overview

This guide covers setting up the E2E testing environment for the Mercai mobile app. The tests use a **hybrid Maestro + ADB approach** for fast and reliable automation.

## Prerequisites

### 1. Java 17+
```bash
java -version  # Check current version

# Install if needed:
sudo apt install openjdk-17-jdk  # Ubuntu/Debian
brew install openjdk@17          # macOS
```

### 2. Android SDK & Emulator
```bash
# Set environment variables (add to ~/.bashrc or ~/.zshrc)
export ANDROID_HOME=~/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/platform-tools

# Verify ADB is working
adb devices
```

### 3. Node.js 18+ and npm
```bash
node -v  # Should be 18+
npm -v
```

## Installation

### Step 1: Install Maestro 1.38.x (IMPORTANT!)

**Use version 1.38.x, NOT version 2.x** - Version 2.x has compatibility issues with our hybrid approach.

```bash
# Install Maestro 1.38.x
curl -Ls "https://get.maestro.mobile.dev" | bash

# Verify version (should be 1.38.x)
~/.maestro/bin/maestro --version

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.maestro/bin:$PATH"
source ~/.bashrc
```

If you have Maestro 2.x installed, downgrade:
```bash
# Remove existing Maestro
rm -rf ~/.maestro

# Reinstall 1.38.x
curl -Ls "https://get.maestro.mobile.dev" | bash
```

### Step 2: Clone Repository
```bash
git clone <repository-url>
cd mercai
```

### Step 3: Install Frontend Dependencies
```bash
cd front_end
npm install
```

### Step 4: Start Backend Services
```bash
cd back_end
docker-compose up -d

# Verify services are running
docker ps
# Should see: mercai_auth_service, mercai_product_service,
# mercai_order_service, mercai_seller_service, mercai_chat_service,
# mercai_mysql, mercai_redis, mercai_traefik
```

### Step 5: Start Android Emulator
```bash
# List available emulators
emulator -list-avds

# Start emulator
emulator -avd <emulator-name> &

# Wait for emulator to boot, verify connection
adb devices
# Should show: emulator-5554   device
```

### Step 6: Start Metro Bundler
```bash
cd front_end
npm start

# Metro should show: "Waiting on http://localhost:8081"
```

### Step 7: Install App on Emulator
```bash
# Build and install the app (first time only)
cd front_end
npx react-native run-android

# Or install existing APK
adb install path/to/app.apk
```

## Running E2E Tests

### Navigate to Scripts Directory
```bash
cd mobile_automation_test/maestro/scripts
```

### Available Test Scripts

| Script | Description |
|--------|-------------|
| `fast-seller-login-test.sh` | Seller authentication test |
| `fast-seller-add-product-test.sh` | Add single product |
| `fast-seller-add-5-products-test.sh` | Add 5 products in bulk |
| `fast-seller-analytics-test.sh` | Seller analytics dashboard |
| `fast-seller-edit-products-test.sh` | Edit existing products |
| `fast-seller-delete-product-test.sh` | Delete products |
| `fast-seller-product-management-test.sh` | Product CRUD operations |
| `fast-seller-order-fulfillment-test.sh` | Order processing workflow |
| `fast-customer-login-test.sh` | Customer authentication test |
| `fast-customer-order-test.sh` | Customer order placement |
| `fast-complete-order-flow-test.sh` | Full order lifecycle (customer + seller) |
| `run-all-seller-tests.sh` | Run all seller tests sequentially |

### Run Individual Tests
```bash
# Make scripts executable (first time)
chmod +x *.sh

# Run a specific test
./fast-seller-login-test.sh
./fast-customer-login-test.sh
./fast-complete-order-flow-test.sh
```

### Run All Seller Tests
```bash
./run-all-seller-tests.sh
```

## Test Credentials

### Seller Account
- Username: `seller_test_user`
- Password: `@Test_seller@1234`

### Customer Account
- Username: `test_customer_user`
- Password: `@Test_customer@1234`

## Architecture

### Hybrid Maestro + ADB Approach

The tests use a hybrid approach for optimal speed and reliability:

1. **Maestro** - Used for:
   - Element detection and assertions
   - Tapping buttons and UI elements
   - Taking screenshots
   - Waiting for animations

2. **ADB** - Used for:
   - Fast text input (much faster than Maestro's inputText)
   - Keyboard dismissal
   - App lifecycle management

### Reusable Login Libraries

- `seller-login-lib.sh` - Seller login functions and navigation helpers
- `customer-login-lib.sh` - Customer login functions and navigation helpers
- `ensure-metro.sh` - Metro bundler health check

## Troubleshooting

### "No connected devices"
```bash
# Check emulator is running
adb devices

# If empty, start emulator
emulator -avd <emulator-name> &
```

### "Metro bundler not running"
```bash
cd front_end
npm start
```

### "Maestro command not found"
```bash
export PATH="$HOME/.maestro/bin:$PATH"
source ~/.bashrc
```

### "App not installed"
```bash
cd front_end
npx react-native run-android
```

### "Test timeout on login"
- Ensure Metro bundler is running
- Ensure backend services are up: `docker ps`
- Check API connectivity: `curl http://localhost:80/mercai/api/v1/auth/login`

### "Element not found"
- App may need to reload: restart app via `adb shell am force-stop com.mercai.app`
- Metro cache may be stale: restart with `npm start -- --reset-cache`

## API Configuration

The app connects to backend via nginx proxy:
- **Emulator URL**: `http://10.0.2.2/mercai` (10.0.2.2 is Android emulator's alias for host localhost)
- **API Gateway**: Traefik on port 80 (via nginx)

## Directory Structure

```
mobile_automation_test/
├── maestro/
│   └── scripts/
│       ├── seller-login-lib.sh      # Seller login library
│       ├── customer-login-lib.sh    # Customer login library
│       ├── ensure-metro.sh          # Metro helper
│       ├── fast-seller-*.sh         # Seller test scripts
│       ├── fast-customer-*.sh       # Customer test scripts
│       ├── fast-complete-*.sh       # Combined flow tests
│       └── run-all-seller-tests.sh  # Test runner
└── LATEST_E2E_SETUP_GUIDE.md        # This file
```

## Quick Start Checklist

- [ ] Java 17+ installed
- [ ] Android SDK with ADB working
- [ ] Maestro 1.38.x installed (NOT 2.x)
- [ ] Backend services running (docker-compose up -d)
- [ ] Android emulator running
- [ ] Metro bundler running (npm start)
- [ ] App installed on emulator

Then run: `./fast-seller-login-test.sh`

---
Last updated: January 2026
