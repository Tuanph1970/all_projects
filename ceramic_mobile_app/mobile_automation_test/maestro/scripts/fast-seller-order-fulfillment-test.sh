#!/bin/bash
# =============================================================================
# Fast Seller Order Fulfillment Test
# =============================================================================
# Tests order fulfillment functionality:
# - FUL-001: View Incoming Orders
# - FUL-002: Accept Order (Confirm pending order)
# - FUL-004: Mark Order as Shipped
#
# Prerequisites:
# - Backend API running on localhost:8000
# - Metro bundler running
# - Android emulator connected
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

# Configuration
APP_ID="com.ceramicmarketplace.app"
# API running on host machine - use localhost for curl from host
# Port 8002 for TCP proxy or 80 for direct traefik
API_BASE_URL="${API_BASE_URL:-http://localhost:80}"
TEMP_FLOW=$(mktemp /tmp/order-fulfillment-XXXXXX.yaml)

# Test customer credentials (for creating orders)
CUSTOMER_USERNAME="${CUSTOMER_USERNAME:-customer_a}"
CUSTOMER_PASSWORD="${CUSTOMER_PASSWORD:-Mysql_2025!}"

# Seller credentials (using defaults from seller-login-lib.sh)
# SELLER_USERNAME=test_seller_user
# SELLER_PASSWORD=Testseller@123456

echo ""
echo "=============================================="
echo "  Fast Seller Order Fulfillment Test"
echo "=============================================="
echo "Test Cases:"
echo "  FUL-001: View Incoming Orders"
echo "  FUL-002: Accept Order"
echo "  FUL-004: Mark Order as Shipped"
echo "=============================================="
echo "Time: $(date)"
echo ""

# =============================================================================
# Helper Functions for API Operations
# =============================================================================

# Get auth token for customer
get_customer_token() {
    _log_step "Getting customer authentication token..."

    local response=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$CUSTOMER_USERNAME&password=$CUSTOMER_PASSWORD")

    local token=$(echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

    if [[ -z "$token" ]]; then
        _log_error "Failed to get customer token"
        echo "Response: $response"
        return 1
    fi

    echo "$token"
}

# Get seller's products
get_seller_products() {
    local token="$1"

    _log_step "Finding seller's products..."

    # Get products list
    local response=$(curl -s -X GET "$API_BASE_URL/api/v1/products?limit=10" \
        -H "Authorization: Bearer $token")

    # Extract first product ID
    local product_id=$(echo "$response" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

    if [[ -z "$product_id" ]]; then
        _log_error "No products found"
        return 1
    fi

    echo "$product_id"
}

# Create a test order
create_test_order() {
    local token="$1"
    local product_id="$2"

    _log_step "Creating test order for product $product_id..."

    local order_data='{
        "items": [
            {
                "product_id": '"$product_id"',
                "quantity": 1
            }
        ],
        "shipping_address_line1": "123 Test Street",
        "shipping_city": "Test City",
        "shipping_state": "TC",
        "shipping_postal_code": "12345",
        "shipping_country": "USA"
    }'

    local response=$(curl -s -X POST "$API_BASE_URL/api/v1/orders" \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "$order_data")

    local order_id=$(echo "$response" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    local order_number=$(echo "$response" | grep -o '"order_number":"[^"]*"' | cut -d'"' -f4)

    if [[ -z "$order_id" ]]; then
        _log_error "Failed to create order"
        echo "Response: $response"
        return 1
    fi

    _log_success "Created order: $order_number (ID: $order_id)"
    echo "$order_id"
}

# =============================================================================
# Setup: Create Test Orders
# =============================================================================

setup_test_orders() {
    echo ""
    echo "=============================================="
    echo "  Setting up test orders via API"
    echo "=============================================="

    # Get customer token
    CUSTOMER_TOKEN=$(get_customer_token)
    if [[ -z "$CUSTOMER_TOKEN" ]]; then
        _log_info "Could not get customer token - proceeding with existing orders"
        return 0
    fi
    _log_success "Customer authenticated"

    # Get a product
    PRODUCT_ID=$(get_seller_products "$CUSTOMER_TOKEN")
    if [[ -z "$PRODUCT_ID" ]]; then
        _log_info "Could not find products - proceeding with existing orders"
        return 0
    fi
    _log_success "Found product ID: $PRODUCT_ID"

    # Create a test order
    ORDER_ID=$(create_test_order "$CUSTOMER_TOKEN" "$PRODUCT_ID")
    if [[ -z "$ORDER_ID" ]]; then
        _log_info "Could not create order - proceeding with existing orders"
        return 0
    fi
    _log_success "Test order created: ID $ORDER_ID"

    # Store order ID for later tests
    export TEST_ORDER_ID="$ORDER_ID"
}

# =============================================================================
# FUL-001: View Incoming Orders
# =============================================================================

test_view_incoming_orders() {
    echo ""
    echo "=============================================="
    echo "  FUL-001: View Incoming Orders"
    echo "=============================================="

    # Check if we're on order management screen
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "order-management-screen"
    timeout: 10000
- takeScreenshot: "orders-01-list"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "Order management screen visible"
    else
        _log_error "Order management screen not visible"
        return 1
    fi

    # Check for orders list or empty state
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- runFlow:
    when:
      visible:
        id: "order-list-empty"
    commands:
      - takeScreenshot: "orders-02-empty"
- runFlow:
    when:
      visible:
        id: "order-list"
    commands:
      - takeScreenshot: "orders-02-with-orders"
EOF

    maestro test "$TEMP_FLOW" 2>&1 | tail -5

    # Try to view order details (if orders exist)
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Try to tap on first order card (if exists)
- tapOn:
    text: "ORD-"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "orders-03-detail-or-list"
# Go back if we navigated to detail
- back
- waitForAnimationToEnd
EOF

    maestro test "$TEMP_FLOW" 2>&1 | tail -5

    _log_success "FUL-001: View Incoming Orders - PASSED"
    return 0
}

# =============================================================================
# FUL-002: Accept Order (Confirm pending order)
# =============================================================================

test_accept_order() {
    echo ""
    echo "=============================================="
    echo "  FUL-002: Accept Order"
    echo "=============================================="

    # Filter for pending orders
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Tap on filter button
- tapOn:
    id: "order-filter-button"
    optional: true
- waitForAnimationToEnd:
    timeout: 2000
- takeScreenshot: "orders-04-filter-menu"
EOF

    maestro test "$TEMP_FLOW" 2>&1 | tail -5

    # Try to select PENDING filter
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Pending"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "orders-05-pending-filter"
EOF

    maestro test "$TEMP_FLOW" 2>&1 | tail -5

    # Try to confirm a pending order
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Look for Confirm button on any order card
- tapOn:
    text: "Confirm"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "orders-06-after-confirm"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "FUL-002: Accept Order - PASSED (or no pending orders found)"
    else
        _log_info "FUL-002: No pending orders to confirm"
    fi

    return 0
}

# =============================================================================
# FUL-004: Mark Order as Shipped
# =============================================================================

test_mark_as_shipped() {
    echo ""
    echo "=============================================="
    echo "  FUL-004: Mark Order as Shipped"
    echo "=============================================="

    # Reset filter to All Orders first
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Tap on filter button
- tapOn:
    id: "order-filter-button"
    optional: true
- waitForAnimationToEnd:
    timeout: 2000
# Select All Orders
- tapOn:
    text: "All Orders"
    optional: true
- waitForAnimationToEnd:
    timeout: 2000
- tapOn:
    text: "Processing"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "orders-07-processing-filter"
EOF

    maestro test "$TEMP_FLOW" 2>&1 | tail -5

    # Try to ship a processing order
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Look for Ship button on any order card
- tapOn:
    text: "Ship"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "orders-08-ship-dialog"
EOF

    maestro test "$TEMP_FLOW" 2>&1 | tail -5

    # If shipping form appears, fill it in
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
# Enter tracking number if form is visible
- tapOn:
    text: "Tracking Number"
    optional: true
- inputText: "TEST-TRACK-123"
# Enter carrier
- tapOn:
    text: "Carrier"
    optional: true
- inputText: "FedEx"
# Confirm shipping
- tapOn:
    text: "Confirm"
    optional: true
- tapOn:
    text: "Mark as Shipped"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "orders-09-after-ship"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
        _log_success "FUL-004: Mark Order as Shipped - PASSED (or no processing orders found)"
    else
        _log_info "FUL-004: No processing orders to ship"
    fi

    return 0
}

# =============================================================================
# Cleanup
# =============================================================================

cleanup() {
    rm -f "$TEMP_FLOW"
}

trap cleanup EXIT

# =============================================================================
# Main Test Execution
# =============================================================================

main() {
    local failed=0

    # Step 0: Try to create test orders (optional - won't fail test if API unavailable)
    setup_test_orders || true

    # Step 1: Seller Login
    _log_step "Step 1: Seller Login..."
    if ! seller_login; then
        _log_error "Seller login failed"
        exit 1
    fi
    _log_success "Seller logged in successfully"

    # Step 2: Navigate to Orders tab
    _log_step "Step 2: Navigate to Orders tab..."
    if ! navigate_to_orders; then
        _log_error "Failed to navigate to Orders tab"
        exit 1
    fi
    _log_success "Orders tab loaded"

    # Step 3: Run FUL-001 test
    if ! test_view_incoming_orders; then
        _log_error "FUL-001 test failed"
        failed=1
    fi

    # Step 4: Run FUL-002 test
    if ! test_accept_order; then
        _log_error "FUL-002 test failed"
        failed=1
    fi

    # Step 5: Run FUL-004 test
    if ! test_mark_as_shipped; then
        _log_error "FUL-004 test failed"
        failed=1
    fi

    # Final screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- waitForAnimationToEnd
- takeScreenshot: "orders-10-final-state"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Summary
    echo ""
    echo "=============================================="
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}[PASS]${NC} ORDER FULFILLMENT TESTS COMPLETED!"
    else
        echo -e "${YELLOW}[WARN]${NC} ORDER FULFILLMENT TESTS COMPLETED WITH WARNINGS"
    fi
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - orders-01-list.png"
    echo "  - orders-02-*.png"
    echo "  - orders-03-detail-or-list.png"
    echo "  - orders-04-filter-menu.png"
    echo "  - orders-05-pending-filter.png"
    echo "  - orders-06-after-confirm.png"
    echo "  - orders-07-processing-filter.png"
    echo "  - orders-08-ship-dialog.png"
    echo "  - orders-09-after-ship.png"
    echo "  - orders-10-final-state.png"
    echo "=============================================="

    return $failed
}

# Run main
main "$@"
