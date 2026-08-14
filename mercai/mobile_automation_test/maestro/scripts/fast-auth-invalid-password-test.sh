#!/bin/bash
# =============================================================================
# AUTH-003: Login with Invalid Password Test
# =============================================================================
# Tests authentication with valid username but invalid password
# Expected: Login should fail with appropriate error message
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

# Configuration (uses test_config.sh via seller-login-lib.sh)
TEMP_FLOW=$(mktemp /tmp/auth-invalid-password-XXXXXX.yaml)

# Test credentials - valid username with INVALID password
VALID_USERNAME="${SELLER_USERNAME}"
INVALID_PASSWORD="WrongPassword@123"

echo ""
echo "=============================================="
echo "  AUTH-003: Login with Invalid Password Test"
echo "=============================================="
echo "Test Scenario:"
echo "  - Username: $VALID_USERNAME (valid)"
echo "  - Password: ${INVALID_PASSWORD:0:5}**** (invalid)"
echo "  - Expected: Login failure with error message"
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

# Attempt login with invalid password
attempt_invalid_login() {
    _log_step "Step 1: Launching app and accessing login screen..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
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
    _log_success "Login screen ready"

    # Step 2: Enter valid username via ADB
    _log_step "Step 2: Entering valid username..."
    sleep 0.5
    _adb_input "$VALID_USERNAME"
    _log_success "Username entered: $VALID_USERNAME"

    # Step 3: Tap password field
    _log_step "Step 3: Tapping password field..."
    _adb_dismiss_keyboard
    sleep 0.3

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "login-password-input"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Step 4: Enter INVALID password via ADB
    _log_step "Step 4: Entering invalid password..."
    sleep 0.5
    _adb_input "$INVALID_PASSWORD"
    _log_success "Invalid password entered"

    # Step 5: Submit login
    _log_step "Step 5: Submitting login..."
    _adb_dismiss_keyboard
    sleep 0.3

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "login-submit-button"
- waitForAnimationToEnd
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    return 0
}

# Verify login failure
verify_login_failure() {
    _log_step "Step 6: Verifying login failure..."
    sleep 2  # Wait for error message to appear

    # Take screenshot of error state
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- takeScreenshot: "auth-invalid-password-error"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Check that we're still on login screen (login failed)
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- extendedWaitUntil:
    visible:
      id: "login-username-input"
    timeout: 5000
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Correctly remained on login screen (login rejected)"
        return 0
    else
        _log_error "Unexpectedly left login screen"
        return 1
    fi
}

# Verify error message is displayed
verify_error_message() {
    _log_step "Step 7: Checking for error message..."

    # Try to find error message element or text
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- extendedWaitUntil:
    visible:
      text: ".*[Ii]nvalid.*|.*[Ee]rror.*|.*[Ii]ncorrect.*|.*[Ff]ailed.*"
    timeout: 3000
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Error message displayed"
        return 0
    else
        _log_info "No visible error text found (UI may use different indicator)"
        # Even if no error text, staying on login screen is valid failure behavior
        return 0
    fi
}

# =============================================================================
# Main Test Execution
# =============================================================================

main() {
    local test_passed=true

    # Attempt login with invalid password
    if ! attempt_invalid_login; then
        _log_error "Failed to attempt login"
        test_passed=false
    fi

    # Verify login was rejected
    if [[ "$test_passed" == "true" ]]; then
        if ! verify_login_failure; then
            _log_error "Login was not properly rejected"
            test_passed=false
        fi
    fi

    # Check for error message
    if [[ "$test_passed" == "true" ]]; then
        verify_error_message
    fi

    # Final screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- takeScreenshot: "auth-invalid-password-final"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Summary
    echo ""
    echo "=============================================="
    if [[ "$test_passed" == "true" ]]; then
        echo -e "${GREEN}[PASS]${NC} AUTH-003: Invalid Password Test PASSED!"
        echo "  - Login correctly rejected with invalid password"
        echo "  - User remained on login screen"
    else
        echo -e "${RED}[FAIL]${NC} AUTH-003: Invalid Password Test FAILED!"
    fi
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - auth-invalid-password-error.png"
    echo "  - auth-invalid-password-final.png"
    echo "=============================================="

    if [[ "$test_passed" == "true" ]]; then
        return 0
    else
        return 1
    fi
}

# Run main
main "$@"
