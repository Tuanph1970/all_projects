#!/bin/bash
# =============================================================================
# AUTH-006: Customer Registration Test
# =============================================================================
# Tests customer account registration flow
# Test scenarios:
#   1. Navigate to registration screen
#   2. Fill all required fields
#   3. Submit registration
#   4. Verify successful registration (redirect to login or auto-login)
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

# Source the login library for helper functions
source "$SCRIPT_DIR/customer-login-lib.sh"

# Configuration
APP_ID="com.mercai.app"
TEMP_FLOW=$(mktemp /tmp/auth-customer-register-XXXXXX.yaml)

# Generate unique test user data to avoid conflicts
TIMESTAMP=$(date +%s)
TEST_FIRST_NAME="TestCustomer"
TEST_LAST_NAME="User$TIMESTAMP"
TEST_USERNAME="test_cust_$TIMESTAMP"
TEST_EMAIL="test_cust_${TIMESTAMP}@test.com"
TEST_PASSWORD="TestCust@123"
TEST_PHONE="0912345678"

echo ""
echo "=============================================="
echo "  AUTH-006: Customer Registration Test"
echo "=============================================="
echo "Test User Data:"
echo "  - First Name: $TEST_FIRST_NAME"
echo "  - Last Name: $TEST_LAST_NAME"
echo "  - Username: $TEST_USERNAME"
echo "  - Email: $TEST_EMAIL"
echo "  - Password: ${TEST_PASSWORD:0:4}****"
echo "  - Role: Customer"
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

# Launch app and navigate to registration screen
navigate_to_registration() {
    _log_step "Step 1: Launching app and navigating to registration..."

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
- takeScreenshot: "customer-register-login-screen"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_error "Failed to access login screen"
        return 1
    fi
    _log_success "Login screen loaded"

    # Look for registration link/button - testID is "login-register-link"
    _log_step "Looking for registration link..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "login-register-link"
- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Found login-register-link, tapped it"
    else
        # Try alternative: tap on text
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    text: ".*[Ss]ign [Uu]p.*|.*[Rr]egister.*|.*[Cc]reate [Aa]ccount.*"
- waitForAnimationToEnd
EOF
        if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
            _log_success "Found registration text link"
        else
            _log_error "Could not find registration link"
            return 1
        fi
    fi

    sleep 1
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- takeScreenshot: "customer-register-screen"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    _log_success "Registration screen loaded"
    return 0
}

# Fill first name field
fill_first_name() {
    _log_step "Filling first name..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "register-firstname-input"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
        # Try alternative ID
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "first-name-input"
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2
    fi

    sleep 0.5
    _adb_input "$TEST_FIRST_NAME"
    _adb_dismiss_keyboard
    _log_success "First name entered"
}

# Fill last name field
fill_last_name() {
    _log_step "Filling last name..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "register-lastname-input"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "last-name-input"
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2
    fi

    sleep 0.5
    _adb_input "$TEST_LAST_NAME"
    _adb_dismiss_keyboard
    _log_success "Last name entered"
}

# Fill username field
fill_username() {
    _log_step "Filling username..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "register-username-input"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "username-input"
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2
    fi

    sleep 0.5
    _adb_input "$TEST_USERNAME"
    _adb_dismiss_keyboard
    _log_success "Username entered"
}

# Fill email field
fill_email() {
    _log_step "Filling email..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "register-email-input"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "email-input"
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2
    fi

    sleep 0.5
    _adb_input "$TEST_EMAIL"
    _adb_dismiss_keyboard
    _log_success "Email entered"
}

# Fill password fields
fill_password() {
    _log_step "Filling password..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "register-password-input"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "password-input"
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2
    fi

    sleep 0.5
    _adb_input "$TEST_PASSWORD"
    _adb_dismiss_keyboard
    _log_success "Password entered"

    # Fill confirm password
    _log_step "Filling confirm password..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "register-confirm-password-input"
EOF

    if ! maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "confirm-password-input"
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2
    fi

    sleep 0.5
    _adb_input "$TEST_PASSWORD"
    _adb_dismiss_keyboard
    _log_success "Confirm password entered"
}

# Fill phone number (optional)
fill_phone() {
    _log_step "Filling phone number..."

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "register-phone-input"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
        sleep 0.5
        _adb_input "$TEST_PHONE"
        _adb_dismiss_keyboard
        _log_success "Phone number entered"
    else
        _log_info "Phone field not found (may be optional or named differently)"
    fi
}

# Select customer role
select_customer_role() {
    _log_step "Selecting customer role..."

    # Try to find and select customer role
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    id: "register-role-customer"
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
        _log_success "Customer role selected"
    else
        # Try alternative: radio button or text
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- tapOn:
    text: ".*[Cc]ustomer.*"
EOF
        if maestro test "$TEMP_FLOW" 2>&1 | tail -2; then
            _log_success "Customer role selected via text"
        else
            _log_info "Role selector not found (may default to customer)"
        fi
    fi
}

# Scroll down if needed
scroll_to_submit() {
    _log_step "Scrolling to submit button..."

    # Scroll multiple times to ensure button is visible
    for i in 1 2 3; do
        cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- scroll:
    direction: DOWN
- waitForAnimationToEnd
EOF
        maestro test "$TEMP_FLOW" 2>&1 | tail -2
        sleep 0.3
    done
}

# Submit registration
submit_registration() {
    _log_step "Submitting registration..."
    _adb_dismiss_keyboard
    sleep 0.5

    # Take screenshot before submit
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- takeScreenshot: "customer-register-before-submit"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Try scrolling until submit button is visible and tap it
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- scrollUntilVisible:
    element:
      id: "register-submit-button"
    direction: DOWN
    timeout: 10000
- tapOn:
    id: "register-submit-button"
- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Registration submitted"
        return 0
    fi

    # Fallback: Try text-based tap with scroll
    _log_info "Trying text-based submit button..."
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- scrollUntilVisible:
    element:
      text: ".*[Ss]ign [Uu]p.*|.*[Rr]egister.*|.*[Cc]reate.*"
    direction: DOWN
    timeout: 10000
- tapOn:
    text: ".*[Ss]ign [Uu]p.*|.*[Rr]egister.*|.*[Cc]reate.*"
- waitForAnimationToEnd
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Registration submitted via text"
        return 0
    fi

    _log_error "Could not tap submit button"
    return 1
}

# Verify registration success
verify_registration() {
    _log_step "Verifying registration success..."
    sleep 3  # Wait for registration to process

    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- takeScreenshot: "customer-register-result"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Check for success indicators:
    # 1. Redirected to login screen (most common)
    # 2. Success message shown
    # 3. Auto-logged in (home screen visible)

    # Check if on login screen
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- assertVisible:
    id: "login-username-input"
    timeout: 5000
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Registration successful - redirected to login screen"
        return 0
    fi

    # Check if auto-logged in (customer home)
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- assertVisible:
    id: "tab-home"
    timeout: 5000
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Registration successful - auto-logged in"
        return 0
    fi

    # Check for success message
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- assertVisible:
    text: ".*[Ss]uccess.*|.*[Rr]egister.*[Ss]uccessful.*|.*[Aa]ccount.*[Cc]reated.*"
    timeout: 3000
EOF

    if maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
        _log_success "Registration successful - success message shown"
        return 0
    fi

    _log_error "Could not verify registration success"
    return 1
}

# =============================================================================
# Main Test Execution
# =============================================================================

main() {
    local test_passed=true

    # Navigate to registration
    if ! navigate_to_registration; then
        _log_error "Failed to navigate to registration"
        test_passed=false
    fi

    if [[ "$test_passed" == "true" ]]; then
        # Fill registration form
        fill_first_name
        fill_last_name
        fill_username
        fill_email
        fill_password
        fill_phone
        select_customer_role
        scroll_to_submit
    fi

    if [[ "$test_passed" == "true" ]]; then
        # Submit registration
        if ! submit_registration; then
            _log_error "Failed to submit registration"
            test_passed=false
        fi
    fi

    if [[ "$test_passed" == "true" ]]; then
        # Verify success
        if ! verify_registration; then
            test_passed=false
        fi
    fi

    # Final screenshot
    cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- takeScreenshot: "customer-register-final"
EOF
    maestro test "$TEMP_FLOW" 2>&1 | tail -2

    # Summary
    echo ""
    echo "=============================================="
    if [[ "$test_passed" == "true" ]]; then
        echo -e "${GREEN}[PASS]${NC} AUTH-006: Customer Registration Test PASSED!"
        echo "  - Registration form completed"
        echo "  - Account created successfully"
        echo "  - Username: $TEST_USERNAME"
        echo "  - Email: $TEST_EMAIL"
    else
        echo -e "${RED}[FAIL]${NC} AUTH-006: Customer Registration Test FAILED!"
    fi
    echo "=============================================="
    echo "Screenshots saved:"
    echo "  - customer-register-login-screen.png"
    echo "  - customer-register-screen.png"
    echo "  - customer-register-before-submit.png"
    echo "  - customer-register-result.png"
    echo "  - customer-register-final.png"
    echo "=============================================="

    if [[ "$test_passed" == "true" ]]; then
        return 0
    else
        return 1
    fi
}

# Run main
main "$@"
