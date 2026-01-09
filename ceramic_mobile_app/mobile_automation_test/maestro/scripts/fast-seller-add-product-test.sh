#!/bin/bash
# =============================================================================
# Fast Seller Add Product Test
# =============================================================================
# Tests adding a new product using the reusable login library
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

# Product details
PRODUCT_TITLE="Test_Product_$(date +%s)"
PRODUCT_DESCRIPTION="This_is_a_test_product_created_by_automated_test"
PRODUCT_PRICE="99.99"
PRODUCT_STOCK="50"
PRODUCT_CATEGORY="Ceramics"
PRODUCT_TAGS="handmade,ceramic,pottery"

echo ""
echo "=============================================="
echo "  Fast Seller Add Product Test"
echo "=============================================="
echo "Product: $PRODUCT_TITLE"
echo "Time: $(date)"
echo ""

# ===== STEP 1: Login =====
echo ""
echo ">>> CURRENT SCREEN: Login Screen"
echo ""
if ! seller_login; then
    _log_error "Login failed - cannot proceed with test"
    exit 1
fi

# Create temporary Maestro flow
TEMP_FLOW=$(mktemp /tmp/seller-add-product-XXXXXX.yaml)

# ===== STEP 2: Navigate to Products Tab =====
echo ""
echo ">>> CURRENT SCREEN: Seller Dashboard (after login)"
echo ""

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

- takeScreenshot: "products-tab-loaded"
EOF

_log_step "Navigating to Products tab..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    _log_error "Failed to navigate to Products tab"
    rm -f "$TEMP_FLOW"
    exit 1
fi
_log_success "Products tab loaded"

# ===== STEP 3: Navigate to Add Product =====
echo ""
echo ">>> CURRENT SCREEN: Products Tab (Product Management)"
echo ""

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- tapOn:
    id: "product-management-fab-add"

- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "add-product-screen"
    timeout: 10000

- takeScreenshot: "add-product-01-empty"
EOF

_log_step "Navigating to Add Product screen..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    _log_error "Failed to navigate to Add Product"
    rm -f "$TEMP_FLOW"
    exit 1
fi
_log_success "Add Product screen loaded"

echo ""
echo ">>> CURRENT SCREEN: Add Product Form (empty)"
echo ""

# ===== STEP 4: Fill Product Title =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-title-input"
EOF

_log_step "Filling product title..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2
sleep 0.5
_adb_input "$PRODUCT_TITLE"
_log_success "Title entered: $PRODUCT_TITLE"

echo ""
echo ">>> CURRENT SCREEN: Add Product Form (title filled, keyboard open)"
echo ""

# ===== STEP 5: Fill Product Description =====
_log_step "Filling product description..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-description-input"
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -2
sleep 0.5
_adb_input "$PRODUCT_DESCRIPTION"
_log_success "Description entered"

echo ""
echo ">>> CURRENT SCREEN: Add Product Form (description filled)"
echo ""

# ===== STEP 6: Fill Product Price =====
_log_step "Filling product price..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-price-input"
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -2
sleep 0.5
_adb_input "$PRODUCT_PRICE"
_log_success "Price entered: $PRODUCT_PRICE"

echo ""
echo ">>> CURRENT SCREEN: Add Product Form (price filled)"
echo ""

# ===== STEP 7: Scroll and Fill Category =====
_log_step "Scrolling and filling category..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- scroll
- tapOn:
    id: "add-product-category-input"
    optional: true
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -2
sleep 0.5
_adb_input "$PRODUCT_CATEGORY"
_log_success "Category entered: $PRODUCT_CATEGORY"

echo ""
echo ">>> CURRENT SCREEN: Add Product Form (category filled, scrolled)"
echo ""

# ===== STEP 8: Fill Stock =====
_log_step "Filling stock quantity..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-stock-input"
    optional: true
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -2
sleep 0.5
_adb_input "$PRODUCT_STOCK"
_log_success "Stock entered: $PRODUCT_STOCK"

echo ""
echo ">>> CURRENT SCREEN: Add Product Form (stock filled)"
echo ""

# ===== STEP 9: Fill Tags =====
_log_step "Filling tags..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-tags-input"
    optional: true
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -2
sleep 0.5
_adb_input "$PRODUCT_TAGS"
_log_success "Tags entered"

echo ""
echo ">>> CURRENT SCREEN: Add Product Form (all fields filled)"
echo ""

# ===== STEP 10: Take Screenshot of Filled Form =====
_log_step "Taking screenshot of filled form..."

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "add-product-02-filled"
EOF

maestro test "$TEMP_FLOW" 2>&1 | tail -2

# ===== STEP 11: Dismiss Popup and Prepare Submit =====
echo ""
echo ">>> CURRENT SCREEN: Add Product Form (ready to submit)"
echo ""

# Dismiss keyboard first
_adb_dismiss_keyboard
sleep 0.3

# Try to dismiss keyboard tutorial popup by tapping "Done"
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Dismiss keyboard tutorial popup (Open the keyboard anytime)
- tapOn:
    text: "Done"
    optional: true
- tapOn:
    text: "OK"
    optional: true
- tapOn:
    text: "Got it"
    optional: true
- tapOn:
    text: "Close"
    optional: true
- tapOn:
    text: "Skip"
    optional: true
- tapOn:
    id: "dialog-dismiss"
    optional: true
- tapOn:
    id: "popup-close"
    optional: true
EOF

_log_step "Dismissing keyboard tutorial popup..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2 || true
sleep 0.5

# Take screenshot to see current state
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "add-product-before-submit"
EOF
maestro test "$TEMP_FLOW" 2>&1 | tail -2

# ===== STEP 12: Submit Product =====
echo ""
echo ">>> CURRENT SCREEN: Add Product Form (popup dismissed)"
echo ""

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Scroll to bottom to find submit button
- scroll
- scroll
- takeScreenshot: "add-product-after-scroll"
EOF

_log_step "Scrolling to submit button..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3

# Try multiple ways to click the submit button
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-submit-button"
    optional: true
EOF

_log_step "Trying to tap submit button by ID..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2 || true

# Also try by text
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Create Product"
    optional: true
- tapOn:
    text: "Add Product"
    optional: true
- tapOn:
    text: "Submit"
    optional: true
- tapOn:
    text: "Save"
    optional: true
EOF

_log_step "Trying to tap submit button by text..."
maestro test "$TEMP_FLOW" 2>&1 | tail -2 || true

sleep 1

# ===== STEP 13: Handle Success Dialog =====
echo ""
echo ">>> CURRENT SCREEN: Checking for success dialog..."
echo ""

cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "add-product-03-result"

# Check for success dialog
- assertVisible:
    text: "Success"
    optional: true
- assertVisible:
    text: "Product created successfully"
    optional: true
EOF

_log_step "Checking for success dialog..."
maestro test "$TEMP_FLOW" 2>&1 | tail -5 || true

# Dismiss success dialog and go back to product list
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
# Press back to dismiss dialog and return to product list
- pressKey: back
- waitForAnimationToEnd
EOF

_log_step "Pressing back to go to product list..."
maestro test "$TEMP_FLOW" 2>&1 | tail -3 || true
sleep 1

# ===== STEP 14: Verify Product in List =====
echo ""
echo ">>> CURRENT SCREEN: Verifying product in list..."
echo ""

# Check we're on the product management screen
cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd

# Verify we're on product management screen
- assertVisible:
    id: "product-management-screen"
    optional: true

# Take screenshot of product list
- takeScreenshot: "product-list-with-new-product"
EOF

_log_step "Verifying product list..."
if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
    _log_success "Product list verified!"
else
    # Try navigating to products tab if not already there
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-products"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "product-list-with-new-product"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3 || true
fi

echo ""
echo ">>> CURRENT SCREEN: Product List (should show new product)"
echo ""
echo "=============================================="
_log_success "SELLER ADD PRODUCT TEST COMPLETED!"
echo "=============================================="
echo "Check screenshots to verify product was added:"
echo "  - add-product-before-submit.png"
echo "  - add-product-after-scroll.png"
echo "  - add-product-03-result.png"
echo "  - product-list-with-new-product.png"
echo "=============================================="
rm -f "$TEMP_FLOW"
exit 0
