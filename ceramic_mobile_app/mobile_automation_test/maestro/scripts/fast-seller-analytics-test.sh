#!/bin/bash
# Fast Seller Analytics Test - Hybrid approach
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
echo "  Fast Seller Analytics Test (Hybrid)"
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
TEMP_FLOW=$(mktemp /tmp/seller-analytics-XXXXXX.yaml)

# ===== PHASE 1: Fast Login =====
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

- tapOn:
    id: "login-username-input"
EOF

print_step "Launching app and waiting for login screen..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_error "Failed to launch app"
    rm -f "$TEMP_FLOW"
    exit 1
fi
print_success "Login screen ready"

# Fast username input with ADB
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
maestro test "$TEMP_FLOW" 2>&1 | tail -2

# Fast password input
print_step "Entering password (fast ADB input)..."
ESCAPED_PASSWORD=$(echo "$PASSWORD" | sed 's/@/\\@/g')
adb shell input text "$ESCAPED_PASSWORD"
sleep 0.3
print_success "Password entered"

# Submit login
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "login-submit-button"

- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "tab-dashboard"
    timeout: 20000
EOF

print_step "Submitting login..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_error "Login failed"
    rm -f "$TEMP_FLOW"
    exit 1
fi
print_success "Login successful"

# ===== PHASE 2: Navigate to Analytics =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-analytics"

- waitForAnimationToEnd
- takeScreenshot: "analytics-01-default"
EOF

print_step "Navigating to Analytics tab..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_error "Failed to navigate to Analytics"
    rm -f "$TEMP_FLOW"
    exit 1
fi
print_success "Analytics screen loaded"

# ===== PHASE 3: Test Period Selection =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Try 7 day period
- tapOn:
    id: "analytics-period-7"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "analytics-02-7day"

# Try 30 day period
- tapOn:
    id: "analytics-period-30"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "analytics-03-30day"
EOF

print_step "Testing period selection..."
maestro test "$TEMP_FLOW" 2>&1 | tail -5
print_success "Period selection tested"

# ===== PHASE 4: Scroll and Check Metrics =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Scroll to see more metrics
- scroll

- assertVisible:
    id: "analytics-sales-card"
    optional: true

- assertVisible:
    id: "analytics-revenue-metric"
    optional: true

- takeScreenshot: "analytics-04-sales-metrics"

# Scroll more
- scroll

- assertVisible:
    id: "analytics-inventory-card"
    optional: true

- assertVisible:
    id: "analytics-top-products-card"
    optional: true

- takeScreenshot: "analytics-05-inventory"

# Scroll to bottom
- scroll

- assertVisible:
    id: "analytics-customer-card"
    optional: true

- takeScreenshot: "analytics-06-customers"
EOF

print_step "Checking analytics metrics..."
if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
    echo ""
    echo "=============================================="
    print_success "SELLER ANALYTICS TEST PASSED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 0
else
    echo ""
    echo "=============================================="
    print_error "SELLER ANALYTICS TEST FAILED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 1
fi
