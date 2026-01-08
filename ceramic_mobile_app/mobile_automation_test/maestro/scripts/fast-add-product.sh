#!/bin/bash
# Fast product addition using hybrid Maestro + ADB approach

MAESTRO=~/.maestro/bin/maestro
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAESTRO_DIR="$(dirname "$SCRIPT_DIR")"

# Helper function for fast text input via ADB
fast_input() {
    local text="$1"
    # Replace spaces with %s for ADB
    local escaped="${text// /%s}"
    adb shell input text "$escaped"
}

# Helper to run a simple maestro tap
tap_element() {
    local element_id="$1"
    cat > /tmp/tap-temp.yaml << EOF
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "$element_id"
EOF
    $MAESTRO test /tmp/tap-temp.yaml 2>/dev/null
}

tap_point() {
    local point="$1"
    cat > /tmp/tap-temp.yaml << EOF
appId: com.ceramicmarketplace.app
---
- tapOn:
    point: "$point"
EOF
    $MAESTRO test /tmp/tap-temp.yaml 2>/dev/null
}

swipe_down() {
    cat > /tmp/swipe-temp.yaml << EOF
appId: com.ceramicmarketplace.app
---
- swipe:
    start: "50%,70%"
    end: "50%,30%"
EOF
    $MAESTRO test /tmp/swipe-temp.yaml 2>/dev/null
}

echo "=== Fast Add Product Test ==="

# Launch app and wait for login
echo "1. Launching app..."
cat > /tmp/launch.yaml << EOF
appId: com.ceramicmarketplace.app
---
- launchApp:
    clearState: true
- extendedWaitUntil:
    visible:
      id: "login-username-input"
    timeout: 15000
EOF
$MAESTRO test /tmp/launch.yaml

# Login
echo "2. Logging in as seller..."
tap_element "login-username-input"
sleep 0.3
fast_input "test_seller"

tap_element "login-password-input"
sleep 0.3
fast_input "12345678"

cat > /tmp/login-submit.yaml << EOF
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-submit-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "tab-dashboard"
    timeout: 15000
EOF
$MAESTRO test /tmp/login-submit.yaml

# Navigate to add product
echo "3. Opening add product screen..."
cat > /tmp/nav-add.yaml << EOF
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "seller-dashboard-fab-add"
- waitForAnimationToEnd
- assertVisible:
    id: "add-product-screen"
EOF
$MAESTRO test /tmp/nav-add.yaml

# Fill form with fast input
echo "4. Filling product form..."
tap_element "add-product-title-input"
sleep 0.3
fast_input "Quick%sTest%sVase"

tap_element "add-product-description-input"
sleep 0.3
fast_input "A%stest%sproduct%sdescription"

tap_element "add-product-price-input"
sleep 0.3
fast_input "29.99"

# Scroll down
swipe_down

tap_element "add-product-category-input"
sleep 0.3
fast_input "1"

tap_element "add-product-stock-input"
sleep 0.3
fast_input "25"

# Dismiss keyboard and scroll
tap_point "50%,30%"
swipe_down

# Submit
echo "5. Submitting product..."
cat > /tmp/submit.yaml << EOF
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "add-product-submit-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      text: "Success"
    timeout: 15000
EOF
$MAESTRO test /tmp/submit.yaml

echo "=== Test Complete ==="
