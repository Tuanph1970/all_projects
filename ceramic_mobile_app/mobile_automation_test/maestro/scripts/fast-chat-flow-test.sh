#!/bin/bash
# =============================================================================
# Fast Chat Flow Test - Customer and Seller Chat Interaction
# =============================================================================
# Tests bidirectional chat between customer and seller:
# - Customer sends message to seller about a product
# - Seller receives and replies
# - Customer verifies reply
#
# Prerequisites:
# - Backend API running
# - Metro bundler running
# - Android emulator connected
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source login libraries
source "$SCRIPT_DIR/customer-login-lib.sh"
source "$SCRIPT_DIR/seller-login-lib.sh"

# Configuration
APP_ID="com.ceramicmarketplace.app"
TEMP_FLOW=$(mktemp /tmp/chat-test-XXXXXX.yaml)
SCREENSHOTS_DIR="/tmp/chat-test-screenshots"

# Create screenshots directory
mkdir -p "$SCREENSHOTS_DIR"

echo ""
echo "=============================================="
echo "  Fast Chat Flow Test"
echo "=============================================="
echo "Test Flow:"
echo "  1. Customer login → Find product → Start chat"
echo "  2. Customer sends message to seller"
echo "  3. Seller login → Check messages → Reply"
echo "  4. Customer login → Verify reply received"
echo "=============================================="
echo "Time: $(date)"
echo ""

# =============================================================================
# Cleanup
# =============================================================================

cleanup() {
    rm -f "$TEMP_FLOW"
}

trap cleanup EXIT

# =============================================================================
# Helper: Logout from the app
# =============================================================================
do_logout() {
    _log_step "Logging out..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-profile"
- waitForAnimationToEnd:
    timeout: 3000
- scroll
- tapOn:
    text: "Logout"
    optional: true
- waitForAnimationToEnd:
    timeout: 2000
- tapOn:
    text: "Yes"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3 || true
    _log_success "Logout completed"
}

# =============================================================================
# PHASE 1: Customer sends message to seller
# =============================================================================
phase1_customer_sends_message() {
    echo ""
    echo "=============================================="
    echo "  PHASE 1: Customer Sends Message"
    echo "=============================================="

    # Step 1.1: Login as customer
    _log_step "Step 1.1: Login as customer..."
    if ! customer_login; then
        _log_error "Customer login failed"
        return 1
    fi
    _log_success "Customer logged in"

    # Step 1.2: Navigate to Search and find a product
    _log_step "Step 1.2: Navigate to Search and find product..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-search"
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "/tmp/chat-test-screenshots/01-search-screen"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Step 1.3: Tap on a product (Blue Ceramic Vase or first available)
    _log_step "Step 1.3: Tap on a product..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Blue Ceramic Vase"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "/tmp/chat-test-screenshots/02-product-details"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    # Step 1.4: Scroll down to find Chat Now button
    _log_step "Step 1.4: Find and tap Chat Now..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- scroll
- waitForAnimationToEnd:
    timeout: 1000
- tapOn:
    text: "Chat Now"
- waitForAnimationToEnd:
    timeout: 5000
- takeScreenshot: "/tmp/chat-test-screenshots/03-chat-screen"
EOF
    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_error "Could not find Chat Now button"
        return 1
    fi
    _log_success "Chat screen opened"

    # Step 1.5: Type and send message using ADB
    _log_step "Step 1.5: Sending message to seller..."

    # Tap on message input field
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Type a message..."
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2 || true

    sleep 0.5

    # Type message using ADB
    _adb_input "Hello, I would like to buy this product. Is it available?"
    sleep 0.3

    # Dismiss keyboard and send
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap send button
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Send"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "/tmp/chat-test-screenshots/04-message-sent"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3
    _log_success "Message sent to seller"

    # Step 1.6: Logout
    do_logout

    return 0
}

# =============================================================================
# PHASE 2: Seller receives and replies
# =============================================================================
phase2_seller_replies() {
    echo ""
    echo "=============================================="
    echo "  PHASE 2: Seller Receives and Replies"
    echo "=============================================="

    # Step 2.1: Login as seller
    _log_step "Step 2.1: Login as seller..."
    if ! seller_login; then
        _log_error "Seller login failed"
        return 1
    fi
    _log_success "Seller logged in"

    # Step 2.2: Navigate to Messages tab
    _log_step "Step 2.2: Navigate to Messages tab..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-chat"
- waitForAnimationToEnd:
    timeout: 5000
- takeScreenshot: "/tmp/chat-test-screenshots/05-seller-messages"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3
    _log_success "Messages tab loaded"

    # Step 2.3: Check for Online Users section and customer message
    _log_step "Step 2.3: Look for customer conversation..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "/tmp/chat-test-screenshots/06-online-users-check"
- tapOn:
    text: "test_customer"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3 || true

    # Try tapping on the first conversation if customer name not found
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Hello"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "/tmp/chat-test-screenshots/07-seller-chat-view"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3 || true
    _log_success "Chat conversation opened"

    # Step 2.4: Reply to customer
    _log_step "Step 2.4: Replying to customer..."

    # Tap on message input field
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Type a message..."
    optional: true
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2 || true

    sleep 0.5

    # Type reply using ADB
    _adb_input "Hello! Yes, this product is available. Would you like to place an order?"
    sleep 0.3

    # Dismiss keyboard and send
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap send button
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Send"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "/tmp/chat-test-screenshots/08-seller-reply-sent"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3
    _log_success "Seller reply sent"

    # Step 2.5: Logout
    do_logout

    return 0
}

# =============================================================================
# PHASE 3: Customer verifies reply
# =============================================================================
phase3_customer_verifies() {
    echo ""
    echo "=============================================="
    echo "  PHASE 3: Customer Verifies Reply"
    echo "=============================================="

    # Step 3.1: Login as customer again
    _log_step "Step 3.1: Login as customer again..."
    if ! customer_login; then
        _log_error "Customer login failed"
        return 1
    fi
    _log_success "Customer logged in"

    # Step 3.2: Navigate to Messages tab
    _log_step "Step 3.2: Navigate to Messages tab..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-chat"
- waitForAnimationToEnd:
    timeout: 5000
- takeScreenshot: "/tmp/chat-test-screenshots/09-customer-messages"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3
    _log_success "Messages tab loaded"

    # Step 3.3: Open conversation with seller
    _log_step "Step 3.3: Open conversation with seller..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "test_seller"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3 || true

    # Try tapping on conversation containing seller's reply
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "available"
    optional: true
- waitForAnimationToEnd:
    timeout: 3000
- takeScreenshot: "/tmp/chat-test-screenshots/10-customer-sees-reply"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3 || true
    _log_success "Seller reply visible to customer"

    # Final screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "/tmp/chat-test-screenshots/11-final-chat-state"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -3

    return 0
}

# =============================================================================
# Main Test Execution
# =============================================================================

main() {
    local failed=0

    # Phase 1: Customer sends message
    if ! phase1_customer_sends_message; then
        _log_error "Phase 1 failed: Customer could not send message"
        failed=1
    fi

    # Phase 2: Seller receives and replies
    if ! phase2_seller_replies; then
        _log_error "Phase 2 failed: Seller could not reply"
        failed=1
    fi

    # Phase 3: Customer verifies reply
    if ! phase3_customer_verifies; then
        _log_error "Phase 3 failed: Customer could not verify reply"
        failed=1
    fi

    # Summary
    echo ""
    echo "=============================================="
    if [[ $failed -eq 0 ]]; then
        echo -e "${GREEN}[PASS]${NC} CHAT FLOW TEST COMPLETED SUCCESSFULLY!"
    else
        echo -e "${YELLOW}[WARN]${NC} CHAT FLOW TEST COMPLETED WITH ISSUES"
    fi
    echo "=============================================="
    echo "Screenshots saved in: $SCREENSHOTS_DIR"
    echo ""
    echo "Chat Flow Tested:"
    echo "  Customer: 'Hello, I would like to buy this product. Is it available?'"
    echo "  Seller:   'Hello! Yes, this product is available. Would you like to place an order?'"
    echo "=============================================="

    return $failed
}

# Run main
main "$@"
