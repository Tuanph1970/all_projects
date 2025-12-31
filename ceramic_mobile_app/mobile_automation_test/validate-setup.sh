#!/bin/bash

# Detox Setup Validation Script
# This script validates that your Detox environment is correctly configured

set -e

echo "=================================="
echo "Detox Setup Validation"
echo "=================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Check Java version
echo "1. Checking Java version..."
if java -version 2>&1 | grep -q "version \"17"; then
    check_pass "Java 17 is installed"
else
    check_warn "Java 17 recommended, current: $(java -version 2>&1 | head -1)"
fi
echo ""

# 2. Check Android SDK
echo "2. Checking Android SDK..."
if [ -d "$HOME/Android/Sdk" ] || [ -d "$ANDROID_HOME" ]; then
    check_pass "Android SDK found"
else
    check_fail "Android SDK not found at $HOME/Android/Sdk"
fi
echo ""

# 3. Check Node.js version
echo "3. Checking Node.js version..."
NODE_VERSION=$(node -v)
check_pass "Node.js $NODE_VERSION installed"
echo ""

# 4. Check if emulator exists
echo "4. Checking Android Emulator..."
EXPECTED_AVD=$(grep "avdName:" .detoxrc.js | grep -v "simulator" | sed "s/.*avdName: '\(.*\)'.*/\1/")
if command -v emulator &> /dev/null; then
    if emulator -list-avds | grep -q "$EXPECTED_AVD"; then
        check_pass "Emulator '$EXPECTED_AVD' found"
    else
        check_warn "Emulator '$EXPECTED_AVD' not found. Available emulators:"
        emulator -list-avds | sed 's/^/    /'
    fi
else
    check_fail "Emulator command not found. Check Android SDK installation."
fi
echo ""

# 5. Check if APKs exist
echo "5. Checking built APKs..."
if [ -f "../front_end/android/app/build/outputs/apk/debug/app-debug.apk" ]; then
    APK_SIZE=$(du -h ../front_end/android/app/build/outputs/apk/debug/app-debug.apk | cut -f1)
    check_pass "App APK found ($APK_SIZE)"
else
    check_warn "App APK not found. Run: npm run build:android"
fi

if [ -f "../front_end/android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk" ]; then
    TEST_APK_SIZE=$(du -h ../front_end/android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk | cut -f1)
    check_pass "Test APK found ($TEST_APK_SIZE)"
else
    check_warn "Test APK not found. Run: npm run build:android"
fi
echo ""

# 6. Check Detox installation
echo "6. Checking Detox installation..."
if [ -d "node_modules/detox" ]; then
    DETOX_VERSION=$(cat package.json | grep '"detox"' | head -1 | sed 's/.*: "\^*//;s/".*//')
    check_pass "Detox $DETOX_VERSION installed in mobile_automation_test/"
else
    check_fail "Detox not installed. Run: npm install"
fi

if [ -d "../front_end/node_modules/detox" ]; then
    DETOX_VERSION_FRONTEND=$(cat ../front_end/package.json | grep '"detox"' | head -1 | sed 's/.*: "\^*//;s/".*//')
    check_pass "Detox $DETOX_VERSION_FRONTEND installed in front_end/"
else
    check_warn "Detox not installed in front_end/"
fi
echo ""

# 7. Check configuration files
echo "7. Checking configuration files..."
if [ -f ".detoxrc.js" ]; then
    check_pass ".detoxrc.js exists"
else
    check_fail ".detoxrc.js not found"
fi

if [ -f "e2e/jest.config.js" ]; then
    check_pass "e2e/jest.config.js exists"
else
    check_fail "e2e/jest.config.js not found"
fi

if [ -f "../front_end/android/gradle.properties" ]; then
    if grep -q "org.gradle.java.home=/usr/lib/jvm/java-1.17.0-openjdk-amd64" ../front_end/android/gradle.properties; then
        check_pass "Java 17 configured in gradle.properties"
    else
        check_warn "Java 17 path not set in gradle.properties"
    fi
else
    check_fail "gradle.properties not found"
fi
echo ""

# 8. Check test files
echo "8. Checking test files..."
TEST_COUNT=$(find e2e -name "*.test.js" | wc -l)
check_pass "Found $TEST_COUNT test files"
echo ""

# Summary
echo "=================================="
echo "Validation Complete!"
echo "=================================="
echo ""
EXPECTED_AVD=$(grep "avdName:" .detoxrc.js | grep -v "simulator" | sed "s/.*avdName: '\(.*\)'.*/\1/")
echo "Next steps:"
echo "  1. Start emulator: emulator -avd $EXPECTED_AVD &"
echo "  2. Build app (if needed): npm run build:android"
echo "  3. Run tests: npm run test:android"
echo ""
echo "For detailed setup information, see DETOX_SETUP.md"
