#!/bin/bash
# Seller Add 5 Products Test - Pure Maestro + ADB hybrid
# Uses Maestro for taps/navigation, ADB for fast text input

set -e

MAESTRO=~/.maestro/bin/maestro
TIMESTAMP=$(date +%s)
SCREENSHOTS_DIR="/tmp/maestro-screenshots"
mkdir -p "$SCREENSHOTS_DIR"

echo "=========================================="
echo "Seller Add 5 Products Test (Hybrid v2)"
echo "=========================================="
echo ""

# Helper: Run small Maestro flow
run_flow() {
    local flow_file="$1"
    echo "  Running: $flow_file"
    $MAESTRO test "$flow_file" 2>&1 | tail -5
}

# Helper: ADB text input (fast)
adb_input() {
    local text="$1"
    # Replace spaces with %s for ADB
    local escaped=$(echo "$text" | sed 's/ /%s/g')
    adb shell input text "$escaped"
    sleep 0.3
}

# Helper: Take screenshot
screenshot() {
    local name="$1"
    adb shell screencap -p /sdcard/screen.png
    adb pull /sdcard/screen.png "$SCREENSHOTS_DIR/${name}.png" 2>/dev/null
    echo "  📸 Screenshot: $name"
}

# ============================================
# STEP 1: Login as seller
# ============================================
echo "STEP 1: Logging in as test_seller..."

cat > /tmp/step1-launch.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- launchApp:
    clearState: true
- waitForAnimationToEnd
EOF
run_flow /tmp/step1-launch.yaml

sleep 2

cat > /tmp/step1-tap-login.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Login"
    optional: true
- waitForAnimationToEnd
EOF
run_flow /tmp/step1-tap-login.yaml

sleep 1

# Tap username and enter via ADB
cat > /tmp/step1-tap-username.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-username-input"
EOF
run_flow /tmp/step1-tap-username.yaml
sleep 0.5
adb_input "test_seller"
echo "  ✓ Entered username"

# Tap password and enter via ADB
cat > /tmp/step1-tap-password.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-password-input"
EOF
run_flow /tmp/step1-tap-password.yaml
sleep 0.5
adb_input "12345678"
echo "  ✓ Entered password"

# Tap login button
cat > /tmp/step1-login.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-button"
- waitForAnimationToEnd
EOF
run_flow /tmp/step1-login.yaml

echo "  Waiting for dashboard..."
sleep 5
screenshot "step1-after-login"

# ============================================
# STEP 2: Navigate to Products
# ============================================
echo ""
echo "STEP 2: Navigating to Products..."

cat > /tmp/step2-products.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Products"
- waitForAnimationToEnd
EOF
run_flow /tmp/step2-products.yaml
sleep 2
screenshot "step2-products-screen"

# ============================================
# Function to add a product
# ============================================
add_product() {
    local NUM="$1"
    local TITLE="$2"
    local DESC="$3"
    local PRICE="$4"
    local CATEGORY="$5"
    local QUANTITY="$6"

    echo ""
    echo "Adding Product $NUM: $TITLE"

    # Tap FAB to add
    cat > /tmp/add-tap-fab.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "product-management-fab-add"
- waitForAnimationToEnd
EOF
    run_flow /tmp/add-tap-fab.yaml
    sleep 1

    # Fill Title
    cat > /tmp/add-tap-title.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-title-input"
EOF
    run_flow /tmp/add-tap-title.yaml
    sleep 0.3
    adb_input "$TITLE"
    echo "  ✓ Title: $TITLE"

    # Fill Description
    cat > /tmp/add-tap-desc.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-description-input"
EOF
    run_flow /tmp/add-tap-desc.yaml
    sleep 0.3
    adb_input "$DESC"
    echo "  ✓ Description: $DESC"

    # Fill Price
    cat > /tmp/add-tap-price.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-price-input"
EOF
    run_flow /tmp/add-tap-price.yaml
    sleep 0.3
    adb_input "$PRICE"
    echo "  ✓ Price: $PRICE"

    # Fill Category
    cat > /tmp/add-tap-category.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-category-input"
EOF
    run_flow /tmp/add-tap-category.yaml
    sleep 0.3
    adb_input "$CATEGORY"
    echo "  ✓ Category: $CATEGORY"

    # Fill Stock Quantity
    cat > /tmp/add-tap-stock.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-stock-input"
EOF
    run_flow /tmp/add-tap-stock.yaml
    sleep 0.3
    adb_input "$QUANTITY"
    echo "  ✓ Stock: $QUANTITY"

    # Dismiss keyboard and scroll to submit
    cat > /tmp/add-submit.yaml << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    point: "50%,30%"
- swipe:
    start: "50%,70%"
    end: "50%,30%"
- tapOn:
    id: "add-product-submit-button"
- waitForAnimationToEnd
EOF
    run_flow /tmp/add-submit.yaml
    sleep 2
    screenshot "product-${NUM}-submitted"
    echo "  ✓ Product $NUM submitted!"
}

# ============================================
# STEP 3: Add 5 Products
# ============================================
echo ""
echo "STEP 3: Adding 5 products..."

add_product "1" "Vase_$TIMESTAMP" "Beautiful_ceramic_vase" "49.99" "Vases" "10"
add_product "2" "Bowl_$TIMESTAMP" "Handmade_clay_bowl" "29.99" "Bowls" "15"
add_product "3" "Plate_$TIMESTAMP" "Dinner_plate_set" "19.99" "Plates" "20"
add_product "4" "Mug_$TIMESTAMP" "Coffee_mug_ceramic" "14.99" "Mugs" "25"
add_product "5" "Sculpture_$TIMESTAMP" "Art_sculpture_piece" "99.99" "Art" "5"

# ============================================
# STEP 4: Verify products
# ============================================
echo ""
echo "STEP 4: Verifying products..."
screenshot "final-products-list"

echo ""
echo "=========================================="
echo "✅ TEST COMPLETED"
echo "Screenshots saved to: $SCREENSHOTS_DIR"
echo "=========================================="
