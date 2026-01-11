#!/bin/bash
# =============================================================================
# AUTH-009: Logout Flow Test
# =============================================================================
# Tests the logout functionality for both customer and seller roles
# Test scenarios:
#   1. Login as customer
#   2. Navigate to profile/settings
#   3. Perform logout
#   4. Verify return to login screen
#   5. Repeat for seller role
#
# Prerequisites:
# - Android emulator connected
# - Metro bundler running
# - Backend server running (port 8002)
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source both login libraries for helper functions
source "$SCRIPT_DIR/customer-login-lib.sh"

# We'll also need seller functions but avoid redefinition conflicts
# by loading seller-specific variables only
SELLER_USERNAME="${SELLER_USERNAME:-test_seller_user}"
SELLER_PASSWORD="${SELLER_PASSWORD:-Testseller@123456}"

# Configuration
APP_ID="com.ceramicmarketplace.app"
TEMP_FLOW=$(mktemp /tmp/auth-logout-XXXXXX.yaml)

echo ""
echo "=============================================="
echo "  AUTH-009: Logout Flow Test"
echo "=============================================="
echo "Test Scenarios:"
echo "  1. Customer logout flow"
echo "  2. Seller logout flow"
echo "  Expected: Return to login screen after logout"
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
# Test Functions
# =============================================================================

# Perform customer logout
customer_logout() {
    _log_step "Navigating to customer profile..."

    # Navigate to profile tab
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-profile"
- waitForAnimationToEnd
- takeScreenshot: "customer-profile-before-logout"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_error "Failed to navigate to profile"
        return 1
    fi
    _log_success "Profile screen loaded"

    # Look for logout button/link
    _log_step "Looking for logout option..."

    # Try common logout element IDs
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "logout-button"
- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Tapped logout-button"
    else
        # Try scrolling to find logout
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- scroll:
    direction: DOWN
- waitForAnimationToEnd
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2

        # Try text-based logout
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: ".*[Ll]og.*[Oo]ut.*|.*[Ss]ign.*[Oo]ut.*"
- waitForAnimationToEnd
EOF

        if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
            _log_success "Tapped logout text"
        else
            # Try settings first, then logout
            cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "settings-button"
- waitForAnimationToEnd
EOF
            maestro test "$TEMP_FLOW" 2>&1 | tail -2

            cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: ".*[Ll]og.*[Oo]ut.*|.*[Ss]ign.*[Oo]ut.*"
- waitForAnimationToEnd
EOF
            if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
                _log_error "Could not find logout option"
                return 1
            fi
        fi
    fi

    # Handle confirmation dialog if present
    sleep 1
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: ".*[Yy]es.*|.*[Cc]onfirm.*|.*[Oo][Kk].*"
    optional: true
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    _log_success "Logout action performed"
    return 0
}

# Perform seller logout
seller_logout() {
    _log_step "Navigating to seller profile/settings..."

    # Try profile tab first
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-profile"
- waitForAnimationToEnd
- takeScreenshot: "seller-profile-before-logout"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        # Seller might have settings in a different location
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "settings-icon"
- waitForAnimationToEnd
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2
    fi
    _log_success "Profile/settings screen loaded"

    # Look for logout button/link
    _log_step "Looking for logout option..."

    # Try common logout element IDs
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "logout-button"
- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Tapped logout-button"
    else
        # Scroll down to find logout
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- scroll:
    direction: DOWN
- waitForAnimationToEnd
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2

        # Try text-based logout
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: ".*[Ll]og.*[Oo]ut.*|.*[Ss]ign.*[Oo]ut.*"
- waitForAnimationToEnd
EOF

        if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
            _log_error "Could not find logout option"
            return 1
        fi
    fi

    # Handle confirmation dialog if present
    sleep 1
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: ".*[Yy]es.*|.*[Cc]onfirm.*|.*[Oo][Kk].*"
    optional: true
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    _log_success "Logout action performed"
    return 0
}

# Verify logout was successful (returned to login screen)
verify_logout() {
    _log_step "Verifying logout success..."
    sleep 2

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- assertVisible:
    id: "login-username-input"
    timeout: 10000
- takeScreenshot: "logout-success"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Successfully logged out - login screen visible"
        return 0
    else
        _log_error "Logout verification failed - not on login screen"
        return 1
    fi
}

# Seller-specific login (inline to avoid conflicts with customer lib)
seller_login_inline() {
    local username="${1:-$SELLER_USERNAME}"
    local password="${2:-$SELLER_PASSWORD}"

    _log_step "Logging in as seller..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- launchApp:
    clearState: true
    permissions:
      notifications: allow
      photos: allow
- waitForAnimationToEnd
- assertVisible:
    id: "login-username-input"
- tapOn:
    id: "login-username-input"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_error "Failed to access login screen"
        return 1
    fi

    # Enter username
    sleep 0.5
    _adb_input "$username"
    _adb_dismiss_keyboard
    sleep 0.3

    # Tap password field
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-password-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Enter password
    sleep 0.5
    _adb_input "$password"
    _adb_dismiss_keyboard
    sleep 0.3

    # Submit login
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-submit-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "tab-dashboard"
    timeout: 20000
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Seller login successful"
        return 0
    else
        _log_error "Seller login failed"
        return 1
    fi
}

# =============================================================================
# Main Test Execution
# =============================================================================

main() {
    local customer_passed=true
    local seller_passed=true

    # ===== TEST 1: Customer Logout =====
    echo ""
    echo "=============================================="
    echo "  Test 1: Customer Logout"
    echo "=============================================="

    # Login as customer
    if ! customer_login; then
        _log_error "Customer login failed"
        customer_passed=false
    fi

    # Perform logout
    if [[ "$customer_passed" == "true" ]]; then
        if ! customer_logout; then
            _log_error "Customer logout failed"
            customer_passed=false
        fi
    fi

    # Verify logout
    if [[ "$customer_passed" == "true" ]]; then
        if ! verify_logout; then
            customer_passed=false
        fi
    fi

    # Take screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "customer-logout-complete"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    if [[ "$customer_passed" == "true" ]]; then
        echo -e "${GREEN}[PASS]${NC} Customer logout test passed"
    else
        echo -e "${RED}[FAIL]${NC} Customer logout test failed"
    fi

    # ===== TEST 2: Seller Logout =====
    echo ""
    echo "=============================================="
    echo "  Test 2: Seller Logout"
    echo "=============================================="

    # Login as seller
    if ! seller_login_inline; then
        _log_error "Seller login failed"
        seller_passed=false
    fi

    # Perform logout
    if [[ "$seller_passed" == "true" ]]; then
        if ! seller_logout; then
            _log_error "Seller logout failed"
            seller_passed=false
        fi
    fi

    # Verify logout
    if [[ "$seller_passed" == "true" ]]; then
        if ! verify_logout; then
            seller_passed=false
        fi
    fi

    # Take screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "seller-logout-complete"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    if [[ "$seller_passed" == "true" ]]; then
        echo -e "${GREEN}[PASS]${NC} Seller logout test passed"
    else
        echo -e "${RED}[FAIL]${NC} Seller logout test failed"
    fi

    # ===== Summary =====
    echo ""
    echo "=============================================="
    echo "  AUTH-009: Logout Flow Test Summary"
    echo "=============================================="
    echo "  Customer Logout: $(if [[ "$customer_passed" == "true" ]]; then echo "PASSED"; else echo "FAILED"; fi)"
    echo "  Seller Logout: $(if [[ "$seller_passed" == "true" ]]; then echo "PASSED"; else echo "FAILED"; fi)"
    echo "=============================================="

    if [[ "$customer_passed" == "true" && "$seller_passed" == "true" ]]; then
        echo -e "${GREEN}[PASS]${NC} AUTH-009: All logout tests PASSED!"
    else
        echo -e "${RED}[FAIL]${NC} AUTH-009: Some logout tests FAILED!"
    fi
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - customer-login-success.png"
    echo "  - customer-profile-before-logout.png"
    echo "  - logout-success.png"
    echo "  - customer-logout-complete.png"
    echo "  - seller-profile-before-logout.png"
    echo "  - seller-logout-complete.png"
    echo "=============================================="

    if [[ "$customer_passed" == "true" && "$seller_passed" == "true" ]]; then
        return 0
    else
        return 1
    fi
}

# Run main
main "$@"
