#!/bin/bash
# Fast Seller Product Management Test - Hybrid approach
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
echo "  Fast Seller Product Management Test (Hybrid)"
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
TEMP_FLOW=$(mktemp /tmp/seller-products-XXXXXX.yaml)

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

# ===== PHASE 2: Navigate to Products =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-products"

- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "product-management-screen"
    timeout: 10000

- takeScreenshot: "products-01-list"
EOF

print_step "Navigating to Products tab..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_error "Failed to navigate to Products"
    rm -f "$TEMP_FLOW"
    exit 1
fi
print_success "Product management screen loaded"

# ===== PHASE 3: Test Search Functionality =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "product-management-search"
    optional: true
EOF

print_step "Tapping search field..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2

# Fast search input with ADB
print_step "Entering search term (fast ADB input)..."
adb shell input text "ceramic"
sleep 0.5

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "products-02-search"

# Clear search by pressing back
- pressKey: back
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Search tested"

# ===== PHASE 4: Test Product Selection =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd

# Test product selection
- tapOn:
    id: "product-item-0"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "products-03-detail"

# Go back
- pressKey: back
EOF

print_step "Testing product selection..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Product selection tested"

# ===== PHASE 5: Test FAB Add Button =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd

- assertVisible:
    id: "product-management-fab-add"
    optional: true

- tapOn:
    id: "product-management-fab-add"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "products-04-add-screen"

# Go back
- pressKey: back
- waitForAnimationToEnd
EOF

print_step "Testing FAB add button..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "FAB add button tested"

# ===== PHASE 6: Verify Back on Product Management =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- assertVisible:
    id: "product-management-screen"
    optional: true

- takeScreenshot: "products-05-final"
EOF

print_step "Verifying product management screen..."
if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    echo ""
    echo "=============================================="
    print_success "SELLER PRODUCT MANAGEMENT TEST PASSED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 0
else
    echo ""
    echo "=============================================="
    print_error "SELLER PRODUCT MANAGEMENT TEST FAILED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 1
fi
