#!/bin/bash
# =============================================================================
# Seller Login Library - Reusable Hybrid Login Function
# =============================================================================
# Usage: Source this file in your test scripts and call seller_login
#
# Example:
#   source "$(dirname "$0")/seller-login-lib.sh"
#   seller_login  # Returns 0 on success, 1 on failure
# =============================================================================

# Default seller credentials - can be overridden via environment variables
SELLER_USERNAME="${SELLER_USERNAME:-test_seller_user}"
SELLER_PASSWORD="${SELLER_PASSWORD:-Testseller@123456}"
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
seller_login() {
    local username="${1:-$SELLER_USERNAME}"
    local password="${2:-$SELLER_PASSWORD}"
    local skip_launch="${3:-}"

    echo ""
    echo "=============================================="
    echo "  Seller Login (Hybrid: Maestro + ADB)"
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

    local temp_flow=$(mktemp /tmp/seller-login-XXXXXX.yaml)

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

    # ===== STEP 5: Submit login and verify seller dashboard =====
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
      id: "tab-dashboard"
    timeout: 20000
- takeScreenshot: "seller-login-success"
EOF

    if maestro test "$temp_flow" 2>&1 | tail -3; then
        echo ""
        _log_success "SELLER LOGIN SUCCESSFUL!"
        echo "=============================================="
        rm -f "$temp_flow"
        return 0
    else
        echo ""
        _log_error "SELLER LOGIN FAILED!"
        echo "=============================================="
        rm -f "$temp_flow"
        return 1
    fi
}

# =============================================================================
# Helper function to navigate to Products tab
# =============================================================================
navigate_to_products() {
    _log_step "Navigating to Products tab..."
    local temp_flow=$(mktemp /tmp/nav-products-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Products"
- waitForAnimationToEnd
- takeScreenshot: "products-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Products tab loaded"
    fi
    return $result
}

# =============================================================================
# Helper function to navigate to Analytics tab
# =============================================================================
navigate_to_analytics() {
    _log_step "Navigating to Analytics tab..."
    local temp_flow=$(mktemp /tmp/nav-analytics-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    text: "Analytics"
- waitForAnimationToEnd
- takeScreenshot: "analytics-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Analytics tab loaded"
    fi
    return $result
}

# =============================================================================
# Helper function to navigate to Dashboard tab
# =============================================================================
navigate_to_dashboard() {
    _log_step "Navigating to Dashboard tab..."
    local temp_flow=$(mktemp /tmp/nav-dashboard-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-dashboard"
- waitForAnimationToEnd
- takeScreenshot: "dashboard-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Dashboard tab loaded"
    fi
    return $result
}

# =============================================================================
# Helper function to navigate to Orders tab
# =============================================================================
navigate_to_orders() {
    _log_step "Navigating to Orders tab..."
    local temp_flow=$(mktemp /tmp/nav-orders-XXXXXX.yaml)
    cat > "$temp_flow" << 'EOF'
appId: com.ceramicmarketplace.app
---
- tapOn:
    id: "tab-orders"
- waitForAnimationToEnd
- extendedWaitUntil:
    visible:
      id: "order-management-screen"
    timeout: 15000
- takeScreenshot: "orders-tab"
EOF
    local result
    maestro test "$temp_flow" 2>&1 | tail -3
    result=$?
    rm -f "$temp_flow"
    if [[ $result -eq 0 ]]; then
        _log_success "Orders tab loaded"
    fi
    return $result
}

# Export functions for use in other scripts
export -f seller_login
export -f navigate_to_products
export -f navigate_to_analytics
export -f navigate_to_dashboard
export -f navigate_to_orders
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
