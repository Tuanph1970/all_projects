#!/bin/bash
# Fast Seller Login Test - Hybrid approach
# Uses Maestro for element detection/tapping, ADB for fast text input

set -e

# Configuration
USERNAME="${TEST_SELLER_USERNAME:-test_seller_user}"
PASSWORD="${TEST_PASSWORD:-Test@12345678}"
APP_ID="com.ceramicmarketplace.app"
MAESTRO_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

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
echo "  Fast Seller Login Test (Hybrid)"
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

# Create temporary Maestro flow for hybrid execution
TEMP_FLOW=$(mktemp /tmp/seller-login-XXXXXX.yaml)

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Launch app fresh
- launchApp:
    clearState: true
    permissions:
      notifications: allow

# Wait for login screen
- waitForAnimationToEnd
- assertVisible:
    id: "login-username-input"

- takeScreenshot: "01-login-screen"

# Tap username field
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

# Create flow to tap password field
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
# Escape @ symbol for ADB
ESCAPED_PASSWORD=$(echo "$PASSWORD" | sed 's/@/\\@/g')
adb shell input text "$ESCAPED_PASSWORD"
sleep 0.3
print_success "Password entered"

# Create flow to submit and verify
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- takeScreenshot: "02-login-filled"

# Tap login button
- tapOn:
    id: "login-submit-button"

# Wait for login
- waitForAnimationToEnd

# Verify seller dashboard
- extendedWaitUntil:
    visible:
      id: "tab-dashboard"
    timeout: 20000

- takeScreenshot: "03-seller-dashboard"
EOF

print_step "Submitting login and verifying..."
if maestro test "$TEMP_FLOW" 2>&1; then
    echo ""
    echo "=============================================="
    print_success "SELLER LOGIN TEST PASSED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 0
else
    echo ""
    echo "=============================================="
    print_error "SELLER LOGIN TEST FAILED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 1
fi
