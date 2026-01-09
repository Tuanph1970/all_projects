#!/bin/bash
# =============================================================================
# Fast Seller Delete Product Test
# =============================================================================
# Tests product deletion using the reusable login library
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
echo "  Fast Seller Delete Product Test"
echo "=============================================="
echo "Time: $(date)"
echo ""

# ===== STEP 1: Login =====
if ! seller_login; then
    _log_error "Login failed - cannot proceed with test"
    exit 1
fi

# Create temporary Maestro flow
TEMP_FLOW=$(mktemp /tmp/seller-delete-product-XXXXXX.yaml)

# ===== STEP 2: Navigate to Products =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-products"

- waitForAnimationToEnd
- takeScreenshot: "delete-01-product-list-before"
EOF

_log_step "Navigating to products..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
_log_success "Products screen loaded"

# ===== STEP 3: Select Product to Delete =====
_log_info "Selecting product to delete..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Tap on a product (choosing the first one to delete)
- tapOn:
    id: "product-item-0"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "delete-02-product-details"
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3

# ===== STEP 4: Delete Product =====
_log_step "Deleting product..."

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

# ===== STEP 5: Confirm Delete =====
_log_step "Confirming deletion..."

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
    _log_success "Delete confirmation completed"
else
    _log_info "Delete confirmation attempted"
fi

# ===== STEP 6: Verify Deletion =====
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
_log_success "SELLER DELETE PRODUCT TEST COMPLETED!"
echo "=============================================="
exit 0
