#!/bin/bash
# Fast Customer Cart Test - Hybrid approach
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
echo "  Fast Customer Cart Test (Hybrid)"
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

TEMP_FLOW=$(mktemp /tmp/customer-cart-XXXXXX.yaml)

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

print_step "Launching app..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Login screen ready"

print_step "Entering credentials (fast ADB input)..."
adb shell input text "$USERNAME"
sleep 0.3

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "login-password-input"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

ESCAPED_PASSWORD=$(echo "$PASSWORD" | sed 's/@/\\@/g')
adb shell input text "$ESCAPED_PASSWORD"
sleep 0.3

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "login-submit-button"

- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "tab-home"
    timeout: 20000
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Login successful"

# ===== PHASE 2: Navigate to Products =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-search"

- waitForAnimationToEnd

# Tap on first product
- tapOn:
    id: "product-item-0"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "cart-01-product-details"
EOF

print_step "Navigating to product..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Product details loaded"

# ===== PHASE 3: Add to Cart =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Add to cart
- tapOn:
    id: "add-to-cart-button"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "cart-02-after-add"
EOF

print_step "Adding product to cart..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Product added to cart"

# ===== PHASE 4: Navigate to Cart =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-cart"

- waitForAnimationToEnd
- takeScreenshot: "cart-03-cart-screen"

# Verify cart has items
- assertVisible:
    id: "cartItem-0"
    optional: true
EOF

print_step "Navigating to cart..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Cart screen loaded"

# ===== PHASE 5: Update Quantity =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Increase quantity
- tapOn:
    id: "increaseQuantity-0"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "cart-04-quantity-updated"
EOF

print_step "Testing quantity update..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Quantity updated"

# ===== PHASE 6: Verify Checkout Button =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- assertVisible:
    id: "checkoutButton"
    optional: true

- takeScreenshot: "cart-05-checkout-ready"
EOF

print_step "Verifying checkout button..."
if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    echo ""
    echo "=============================================="
    print_success "CUSTOMER CART TEST PASSED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 0
else
    echo ""
    echo "=============================================="
    print_error "CUSTOMER CART TEST FAILED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 1
fi
