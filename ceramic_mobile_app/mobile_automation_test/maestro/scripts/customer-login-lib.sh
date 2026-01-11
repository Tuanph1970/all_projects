#!/bin/bash
# =============================================================================
# Customer Login Library - Reusable Hybrid Login Function
# =============================================================================
# Usage: Source this file in your test scripts and call customer_login
#
# Example:
#   source "$(dirname "$0")/customer-login-lib.sh"
#   customer_login  # Returns 0 on success, 1 on failure
# =============================================================================

# Default customer credentials - can be overridden via environment variables
# Account created via API and verified in database for E2E testing
CUSTOMER_USERNAME="${CUSTOMER_USERNAME:-test_customer_user}"
CUSTOMER_PASSWORD="${CUSTOMER_PASSWORD:-@Test_customer@1234}"
APP_ID="com.ceramicmarketplace.app"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Logging functions
_log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }
_log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
_log_error() { echo -e "${RED}[FAIL]${NC} $1"; }
_log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

# =============================================================================
# Reliable ADB Text Input - Character by character (default)
# =============================================================================
_adb_input() {
    local text="$1"
    # Always use char-by-char for reliability
    _adb_input_char_by_char "$text"
}

# Character-by-character input (slower but 100% reliable)
_adb_input_char_by_char() {
    local text="$1"
    local delay="${2:-0.03}"  # 30ms delay between characters
    local i char

    for ((i=0; i<${#text}; i++)); do
        char="${text:$i:1}"

        # Handle special characters that need escaping
        case "$char" in
            ' ') adb shell input text '%s' ;;
            '@') adb shell input text '\@' ;;
            '#') adb shell input text '\#' ;;
            '$') adb shell input text '\$' ;;
            '%') adb shell input text '\%' ;;
            '&') adb shell input text '\&' ;;
            '*') adb shell input text '\*' ;;
            '(') adb shell input text '\(' ;;
            ')') adb shell input text '\)' ;;
            '!') adb shell input text '\!' ;;
            '"') adb shell input text '\"' ;;
            "'") adb shell input text "\'" ;;
            '\\') adb shell input text '\\\\' ;;
            '|') adb shell input text '\|' ;;
            '<') adb shell input text '\<' ;;
            '>') adb shell input text '\>' ;;
            ';') adb shell input text '\;' ;;
            '`') adb shell input text '\`' ;;
            '~') adb shell input text '\~' ;;
            *) adb shell input text "$char" ;;
        esac

        sleep "$delay"
    done

    sleep 0.2
    return 0
}

# Tap on element using ADB coordinates (backup method)
_adb_tap() {
    local x="$1"
    local y="$2"
    adb shell input tap "$x" "$y"
    sleep 0.3
}

# Press back key
_adb_back() {
    adb shell input keyevent KEYCODE_BACK
    sleep 0.3
}

# Hide keyboard using ADB (ESCAPE key - WARNING: can trigger back navigation if keyboard already closed)
_adb_hide_keyboard() {
    adb shell input keyevent KEYCODE_ESCAPE
    sleep 0.3
}

# Dismiss keyboard by tapping on empty area (safer than ESCAPE key)
_adb_dismiss_keyboard() {
    # Tap in the middle-left area of the screen (safe zone, avoids header and buttons)
    adb shell input tap 100 800
    sleep 0.3
}

# =============================================================================
# Main Login Function
# =============================================================================
customer_login() {
    local username="${1:-$CUSTOMER_USERNAME}"
    local password="${2:-$CUSTOMER_PASSWORD}"
    local skip_launch="${3:-}"

    echo ""
    echo "=============================================="
    echo "  Customer Login (Hybrid: Maestro + ADB)"
    echo "=============================================="
    echo "Username: $username"
    echo "Time: $(date)"
    echo ""

    # Ensure Maestro is in PATH
    export PATH="$PATH:$HOME/.maestro/bin"

    # Check device connection
    if ! adb devices | grep -q "device$"; then
        _log_error "No Android device connected"
        return 1
    fi
    _log_success "Device connected"

    local temp_flow=$(mktemp /tmp/customer-login-XXXXXX.yaml)

    # ===== STEP 1: Launch app and wait for login screen =====
    if [[ "$skip_launch" != "no_launch" ]]; then
        _log_step "Launching app..."
        cat > "$temp_flow" << 'EOF'
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
    else
        _log_step "Tapping username field (app already launched)..."
        cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- assertVisible:
    id: "login-username-input"
- tapOn:
    id: "login-username-input"
EOF
    fi

    if ! maestro test "$temp_flow" 2>&1 | tail -3; then
        _log_error "Failed to access login screen"
        rm -f "$temp_flow"
        return 1
    fi
    _log_success "Login screen ready"

    # ===== STEP 2: Enter username via ADB =====
    _log_step "Entering username..."
    sleep 0.5
    _adb_input "$username"
    _log_success "Username entered"

    # ===== STEP 3: Hide keyboard and tap password field =====
    _log_step "Tapping password field..."
    # Use ADB to dismiss keyboard first (safer than ESCAPE key)
    _adb_dismiss_keyboard
    sleep 0.3

    # Now use Maestro to tap password field
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-password-input"
EOF
    maestro test "$temp_flow" 2>&1 | tail -2

    # ===== STEP 4: Enter password via ADB =====
    _log_step "Entering password..."
    sleep 0.5
    _adb_input "$password"
    _log_success "Password entered"

    # ===== STEP 5: Submit login and verify customer home screen =====
    _log_step "Submitting login..."
    # Dismiss keyboard first (safer than ESCAPE key)
    _adb_dismiss_keyboard
    sleep 0.3

    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "login-submit-button"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "tab-home"
    timeout: 20000
- takeScreenshot: "customer-login-success"
EOF

    if maestro test "$temp_flow" 2>&1 | tail -3; then
        echo ""
        _log_success "CUSTOMER LOGIN SUCCESSFUL!"
        echo "=============================================="
        rm -f "$temp_flow"
        return 0
    else
        echo ""
        _log_error "CUSTOMER LOGIN FAILED!"
        echo "=============================================="
        rm -f "$temp_flow"
        return 1
    fi
}

# =============================================================================
# Helper function to navigate to Home tab
# =============================================================================
navigate_to_home() {
    _log_step "Navigating to Home tab..."
    local temp_flow=$(mktemp /tmp/nav-home-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-home"
- waitForAnimationToEnd
- takeScreenshot: "home-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Home tab loaded"
    fi
    return $result
}

# =============================================================================
# Helper function to navigate to Search tab
# =============================================================================
navigate_to_search() {
    _log_step "Navigating to Search tab..."
    local temp_flow=$(mktemp /tmp/nav-search-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-search"
- waitForAnimationToEnd
- takeScreenshot: "search-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Search tab loaded"
    fi
    return $result
}

# =============================================================================
# Helper function to navigate to Cart tab
# =============================================================================
navigate_to_cart() {
    _log_step "Navigating to Cart tab..."
    local temp_flow=$(mktemp /tmp/nav-cart-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-cart"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "cart-screen"
    timeout: 15000
- takeScreenshot: "cart-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Cart tab loaded"
    fi
    return $result
}

# =============================================================================
# Helper function to navigate to Profile tab
# =============================================================================
navigate_to_profile() {
    _log_step "Navigating to Profile tab..."
    local temp_flow=$(mktemp /tmp/nav-profile-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-profile"
- waitForAnimationToEnd
- takeScreenshot: "profile-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Profile tab loaded"
    fi
    return $result
}

# =============================================================================
# Helper function to navigate to Chat tab
# =============================================================================
navigate_to_chat() {
    _log_step "Navigating to Chat tab..."
    local temp_flow=$(mktemp /tmp/nav-chat-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-chat"
- waitForAnimationToEnd
- takeScreenshot: "chat-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Chat tab loaded"
    fi
    return $result
}

# Export functions for use in other scripts
export -f customer_login
export -f navigate_to_home
export -f navigate_to_search
export -f navigate_to_cart
export -f navigate_to_profile
export -f navigate_to_chat
export -f _adb_input
export -f _adb_input_char_by_char
export -f _adb_tap
export -f _adb_back
export -f _adb_hide_keyboard
export -f _adb_dismiss_keyboard
export -f _log_step
export -f _log_success
export -f _log_error
export -f _log_info
