#!/bin/bash
# Fast Customer Login Test - Hybrid approach
# Uses Maestro for element detection/tapping, ADB for fast text input

set -e

# Configuration
USERNAME="${TEST_CUSTOMER_USERNAME:-test_customer}"
PASSWORD="${TEST_PASSWORD:-Test@12345678}"
APP_ID="com.ceramicmarketplace.app"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Add Maestro to PATH
export PATH="$PATH:$HOME/.maestro/bin"

echo "=============================================="
echo "  Fast Customer Login Test (Hybrid)"
echo "=============================================="
echo "Username: $USERNAME"
echo "Time: $(date)"
echo ""

# Check device
if ! adb devices | grep -q "device$"; then
    print_error "No Android device connected"
    exit 1
fi
print_success "Device connected"

# Create temporary Maestro flow
TEMP_FLOW=$(mktemp /tmp/customer-login-XXXXXX.yaml)

# Launch app and wait for login screen
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- launchApp:
    clearState: true
    permissions:
      notifications: allow

- waitForAnimationToEnd
- assertVisible:
    id: "login-username-input"

- takeScreenshot: "customer-01-login-screen"

- tapOn:
    id: "login-username-input"
EOF

print_step "Launching app and waiting for login screen..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
    print_error "Failed to launch app"
    rm -f "$TEMP_FLOW"
    exit 1
fi
print_success "Login screen ready"

# Fast text input with ADB
print_step "Entering username (fast ADB input)..."
adb shell input text "$USERNAME"
sleep 0.3
print_success "Username entered"

# Tap password field
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "login-password-input"
EOF

print_step "Tapping password field..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Fast password input
print_step "Entering password (fast ADB input)..."
ESCAPED_PASSWORD=$(echo "$PASSWORD" | sed 's/@/\\@/g')
adb shell input text "$ESCAPED_PASSWORD"
sleep 0.3
print_success "Password entered"

# Submit and verify
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- takeScreenshot: "customer-02-login-filled"

- tapOn:
    id: "login-submit-button"

- waitForAnimationToEnd

# Wait longer for login to complete
- extendedWaitUntil:
    visible:
      id: "tab-search"
    timeout: 20000

- takeScreenshot: "customer-03-home-screen"
EOF

print_step "Submitting login and verifying..."
if maestro test "$TEMP_FLOW" 2>&1; then
    echo ""
    echo "=============================================="
    print_success "CUSTOMER LOGIN TEST PASSED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 0
else
    echo ""
    echo "=============================================="
    print_error "CUSTOMER LOGIN TEST FAILED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 1
fi
