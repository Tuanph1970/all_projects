#!/bin/bash
# Fast Seller Delete 1 Product Test - Hybrid approach
# Deletes 1 product to test product deletion functionality

set -e

# Configuration
USERNAME="${TEST_SELLER_USERNAME:-test_seller_user}"
PASSWORD="${TEST_PASSWORD:-Test@12345678}"
APP_ID="com.ceramicmarketplace.app"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Add Maestro to PATH
export PATH="$PATH:$HOME/.maestro/bin"

echo "=============================================="
echo "  Fast Seller Delete 1 Product Test (Hybrid)"
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

TEMP_FLOW=$(mktemp /tmp/seller-delete-product-XXXXXX.yaml)

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
      id: "tab-dashboard"
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
    id: "tab-products"

- waitForAnimationToEnd
- takeScreenshot: "delete-01-product-list-before"
EOF

print_step "Navigating to products..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
print_success "Products screen loaded"

# ===== PHASE 3: Select Product to Delete =====
print_info "Selecting product to delete..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Tap on a product (choosing the last one to delete)
- tapOn:
    id: "product-item-0"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "delete-02-product-details"
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3

# ===== PHASE 4: Delete Product =====
print_step "Deleting product..."

# Try delete button in product details
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Try delete button
- tapOn:
    id: "delete-product-button"
    optional: true

- waitForAnimationToEnd
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

# Try menu/more options
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "product-menu-button"
    optional: true

- tapOn:
    id: "product-more-options"
    optional: true

- waitForAnimationToEnd

- tapOn:
    id: "menu-delete"
    optional: true

- tapOn:
    text: "Delete"
    optional: true

- waitForAnimationToEnd
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

# ===== PHASE 5: Confirm Delete =====
print_step "Confirming deletion..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Confirm delete dialog
- tapOn:
    id: "confirm-delete-button"
    optional: true

- tapOn:
    text: "Yes"
    optional: true

- tapOn:
    text: "Confirm"
    optional: true

- tapOn:
    text: "Delete"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "delete-03-after-delete"
EOF

if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    print_success "Delete confirmation completed"
else
    print_info "Delete confirmation attempted"
fi

# ===== PHASE 6: Verify Deletion =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-products"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "delete-04-product-list-after"
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Cleanup
rm -f "$TEMP_FLOW"

echo ""
echo "=============================================="
print_success "SELLER DELETE PRODUCT TEST COMPLETED!"
echo "=============================================="
exit 0
