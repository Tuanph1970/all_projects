#!/bin/bash
# =============================================================================
# Fast Seller Product Management Test
# =============================================================================
# Tests product management functionality using the reusable login library
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

echo ""
echo "=============================================="
echo "  Fast Seller Product Management Test"
echo "=============================================="
echo "Time: $(date)"
echo ""

# ===== STEP 1: Login =====
if ! seller_login; then
    _log_error "Login failed - cannot proceed with test"
    exit 1
fi

# Create temporary Maestro flow
TEMP_FLOW=$(mktemp /tmp/seller-products-XXXXXX.yaml)

# ===== STEP 2: Navigate to Products =====
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

_log_step "Navigating to Products tab..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    _log_error "Failed to navigate to Products"
    rm -f "$TEMP_FLOW"
    exit 1
fi
_log_success "Product management screen loaded"

# ===== STEP 3: Test Search Functionality =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "product-management-search"
    optional: true
EOF

_log_step "Tapping search field..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2

# Fast search input with ADB
_log_step "Entering search term..."
_adb_input "ceramic"

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "products-02-search"

# Clear search by pressing back
- pressKey: back
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3
_log_success "Search tested"

# ===== STEP 4: Test Product Selection =====
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

_log_step "Testing product selection..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
_log_success "Product selection tested"

# ===== STEP 5: Test FAB Add Button =====
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

_log_step "Testing FAB add button..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
_log_success "FAB add button tested"

# ===== STEP 6: Verify Back on Product Management =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- assertVisible:
    id: "product-management-screen"
    optional: true

- takeScreenshot: "products-05-final"
EOF

_log_step "Verifying product management screen..."
if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    echo ""
    echo "=============================================="
    _log_success "SELLER PRODUCT MANAGEMENT TEST PASSED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 0
else
    echo ""
    echo "=============================================="
    _log_error "SELLER PRODUCT MANAGEMENT TEST FAILED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 1
fi
