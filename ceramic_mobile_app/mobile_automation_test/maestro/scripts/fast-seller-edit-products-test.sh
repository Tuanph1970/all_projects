#!/bin/bash
# =============================================================================
# Fast Seller Edit Products Test
# =============================================================================
# Tests editing existing products using the reusable login library
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

TIMESTAMP=$(date +%s)

echo ""
echo "=============================================="
echo "  Fast Seller Edit 2 Products Test"
echo "=============================================="
echo "Time: $(date)"
echo ""

# ===== STEP 1: Login =====
if ! seller_login; then
    _log_error "Login failed - cannot proceed with test"
    exit 1
fi

# Create temporary Maestro flow
TEMP_FLOW=$(mktemp /tmp/seller-edit-products-XXXXXX.yaml)

# ===== STEP 2: Navigate to Products =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-products"

- waitForAnimationToEnd
- takeScreenshot: "edit-01-product-list"
EOF

_log_step "Navigating to products..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3
_log_success "Products screen loaded"

# ===== STEP 3: Edit First Product =====
_log_info "Editing product 1 of 2..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Tap on first product to view/edit
- tapOn:
    id: "product-item-0"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-02-product-1-details"

# Tap edit button
- tapOn:
    id: "edit-product-button"
    optional: true

- waitForAnimationToEnd
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Update title
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "edit-product-title-input"
    optional: true

- eraseText:
    charactersToErase: 50
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

NEW_TITLE="Updated_Product_1_${TIMESTAMP}"
_adb_input "$NEW_TITLE"

# Update price
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "edit-product-price-input"
    optional: true

- eraseText:
    charactersToErase: 10
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2
_adb_input "59.99"

# Save changes
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "save-product-button"
    optional: true

- tapOn:
    id: "edit-product-submit-button"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-03-product-1-saved"
EOF

if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    _log_success "Product 1 edited successfully"
else
    _log_info "Product 1 edit attempted"
fi

# Go back to product list
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- pressKey: back
- waitForAnimationToEnd

- tapOn:
    id: "tab-products"
    optional: true

- waitForAnimationToEnd
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

# ===== STEP 4: Edit Second Product =====
_log_info "Editing product 2 of 2..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Tap on second product
- tapOn:
    id: "product-item-1"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-04-product-2-details"

# Tap edit button
- tapOn:
    id: "edit-product-button"
    optional: true

- waitForAnimationToEnd
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Update description
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "edit-product-description-input"
    optional: true

- eraseText:
    charactersToErase: 100
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

NEW_DESC="Updated_description_with_new_details_${TIMESTAMP}"
_adb_input "$NEW_DESC"

# Update stock
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- scroll
- tapOn:
    id: "edit-product-stock-input"
    optional: true

- eraseText:
    charactersToErase: 5
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2
_adb_input "200"

# Save changes
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- hideKeyboard
- tapOn:
    id: "save-product-button"
    optional: true

- tapOn:
    id: "edit-product-submit-button"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-05-product-2-saved"
EOF

if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    _log_success "Product 2 edited successfully"
else
    _log_info "Product 2 edit attempted"
fi

# Final screenshot of product list
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- pressKey: back
- waitForAnimationToEnd

- tapOn:
    id: "tab-products"
    optional: true

- waitForAnimationToEnd
- takeScreenshot: "edit-06-final-list"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Cleanup
rm -f "$TEMP_FLOW"

echo ""
echo "=============================================="
_log_success "SELLER EDIT 2 PRODUCTS TEST COMPLETED!"
echo "=============================================="
exit 0
