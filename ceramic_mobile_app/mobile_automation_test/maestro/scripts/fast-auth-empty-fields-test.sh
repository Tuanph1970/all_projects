#!/bin/bash
# =============================================================================
# AUTH-005: Login with Empty Fields Test
# =============================================================================
# Tests authentication validation when fields are empty
# Test scenarios:
#   1. Both username and password empty
#   2. Username filled, password empty
#   3. Username empty, password filled
# Expected: Login should fail with validation errors
#
# Prerequisites:
# - Android emulator connected
# - Metro bundler running
# - Backend server running
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library for helper functions
source "$SCRIPT_DIR/seller-login-lib.sh"

# Configuration
APP_ID="com.ceramicmarketplace.app"
TEMP_FLOW=$(mktemp /tmp/auth-empty-fields-XXXXXX.yaml)

echo ""
echo "=============================================="
echo "  AUTH-005: Login with Empty Fields Test"
echo "=============================================="
echo "Test Scenarios:"
echo "  1. Both fields empty - tap submit"
echo "  2. Only username filled - password empty"
echo "  3. Only password filled - username empty"
echo "  Expected: Validation errors for each case"
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

# Launch app and verify login screen
launch_app() {
    _log_step "Launching app..."

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
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_error "Failed to access login screen"
        return 1
    fi
    _log_success "Login screen ready"
    return 0
}

# Test 1: Both fields empty
test_both_empty() {
    _log_step "Test 1: Both fields empty..."

    # Try to submit without entering anything
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-submit-button"
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 1

    # Take screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "auth-empty-both-fields"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Verify still on login screen
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- assertVisible:
    id: "login-username-input"
    timeout: 3000
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Test 1 PASSED: Correctly blocked empty submission"
        return 0
    else
        _log_error "Test 1 FAILED: Unexpectedly left login screen"
        return 1
    fi
}

# Test 2: Username filled, password empty
test_password_empty() {
    _log_step "Test 2: Username filled, password empty..."

    # Tap username field and enter username
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-username-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.5

    # Enter username
    _adb_input "test_user"
    _adb_hide_keyboard
    sleep 0.3

    # Submit without password
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-submit-button"
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 1

    # Take screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "auth-empty-password"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Verify still on login screen
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- assertVisible:
    id: "login-username-input"
    timeout: 3000
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Test 2 PASSED: Correctly blocked empty password submission"
        return 0
    else
        _log_error "Test 2 FAILED: Unexpectedly left login screen"
        return 1
    fi
}

# Test 3: Username empty, password filled
test_username_empty() {
    _log_step "Test 3: Username empty, password filled..."

    # Clear app state and restart
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- launchApp:
    clearState: true
- waitForAnimationToEnd
- assertVisible:
    id: "login-username-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Tap password field directly
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-password-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 0.5

    # Enter password only
    _adb_input "SomePassword123"
    _adb_hide_keyboard
    sleep 0.3

    # Submit without username
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-submit-button"
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2
    sleep 1

    # Take screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "auth-empty-username"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Verify still on login screen
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- assertVisible:
    id: "login-username-input"
    timeout: 3000
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Test 3 PASSED: Correctly blocked empty username submission"
        return 0
    else
        _log_error "Test 3 FAILED: Unexpectedly left login screen"
        return 1
    fi
}

# =============================================================================
# Main Test Execution
# =============================================================================

main() {
    local tests_passed=0
    local tests_failed=0

    # Launch app
    if ! launch_app; then
        echo -e "${RED}[FAIL]${NC} Failed to launch app"
        exit 1
    fi

    # Test 1: Both fields empty
    if test_both_empty; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    # Test 2: Password empty
    if test_password_empty; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    # Test 3: Username empty
    if test_username_empty; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi

    # Final screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.ceramicmarketplace.app
---
- takeScreenshot: "auth-empty-fields-final"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Summary
    echo ""
    echo "=============================================="
    echo "  AUTH-005: Empty Fields Test Summary"
    echo "=============================================="
    echo "  Tests Passed: $tests_passed"
    echo "  Tests Failed: $tests_failed"
    echo "=============================================="

    if [[ $tests_failed -eq 0 ]]; then
        echo -e "${GREEN}[PASS]${NC} AUTH-005: All empty field validations working!"
    else
        echo -e "${RED}[FAIL]${NC} AUTH-005: Some validation tests failed!"
    fi
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - auth-empty-both-fields.png"
    echo "  - auth-empty-password.png"
    echo "  - auth-empty-username.png"
    echo "  - auth-empty-fields-final.png"
    echo "=============================================="

    if [[ $tests_failed -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

# Run main
main "$@"
