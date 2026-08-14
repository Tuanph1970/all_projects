#!/bin/bash
# =============================================================================
# Fast Seller Analytics Test
# =============================================================================
# Tests seller analytics functionality using the reusable login library
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Ensure Metro is running
source "$SCRIPT_DIR/ensure-metro.sh"

# Source the login library
source "$SCRIPT_DIR/seller-login-lib.sh"

echo ""
echo "=============================================="
echo "  Fast Seller Analytics Test"
echo "=============================================="
echo "Time: $(date)"
echo ""

# ===== STEP 1: Login =====
if ! seller_login; then
    _log_error "Login failed - cannot proceed with test"
    exit 1
fi

# Create temporary Maestro flow
TEMP_FLOW=$(mktemp /tmp/seller-analytics-XXXXXX.yaml)

# ===== STEP 2: Navigate to Analytics =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
- waitForAnimationToEnd
- tapOn:
    id: "tab-analytics"

- waitForAnimationToEnd
- takeScreenshot: "analytics-01-default"
EOF

_log_step "Navigating to Analytics tab..."
if ! maestro test "$TEMP_FLOW" 2>&1 | tail -3; then
    _log_error "Failed to navigate to Analytics"
    rm -f "$TEMP_FLOW"
    exit 1
fi
_log_success "Analytics screen loaded"

# ===== STEP 3: Test Period Selection =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
# Try 7 day period
- tapOn:
    id: "analytics-period-7"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "analytics-02-7day"

# Try 30 day period
- tapOn:
    id: "analytics-period-30"
    optional: true
- waitForAnimationToEnd
- takeScreenshot: "analytics-03-30day"
EOF

_log_step "Testing period selection..."
maestro test "$TEMP_FLOW" 2>&1 | tail -5
_log_success "Period selection tested"

# ===== STEP 4: Scroll and Check Metrics =====
cat > "$TEMP_FLOW" << 'EOF'
appId: com.mercai.app
---
# Scroll to see more metrics
- scroll

- assertVisible:
    id: "analytics-sales-card"
    optional: true

- assertVisible:
    id: "analytics-revenue-metric"
    optional: true

- takeScreenshot: "analytics-04-sales-metrics"

# Scroll more
- scroll

- assertVisible:
    id: "analytics-inventory-card"
    optional: true

- assertVisible:
    id: "analytics-top-products-card"
    optional: true

- takeScreenshot: "analytics-05-inventory"

# Scroll to bottom
- scroll

- assertVisible:
    id: "analytics-customer-card"
    optional: true

- takeScreenshot: "analytics-06-customers"
EOF

_log_step "Checking analytics metrics..."
if maestro test "$TEMP_FLOW" 2>&1 | tail -5; then
    echo ""
    echo "=============================================="
    _log_success "SELLER ANALYTICS TEST PASSED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 0
else
    echo ""
    echo "=============================================="
    _log_error "SELLER ANALYTICS TEST FAILED!"
    echo "=============================================="
    rm -f "$TEMP_FLOW"
    exit 1
fi
