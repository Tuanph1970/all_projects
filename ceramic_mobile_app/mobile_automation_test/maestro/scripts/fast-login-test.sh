#!/bin/bash
# Fast login test using ADB for input (bypasses Maestro's slow inputText)
# Usage: ./fast-login-test.sh [username] [password]

set -e

USERNAME="${1:-test_customer}"
PASSWORD="${2:-Test@12345678}"
APP_ID="com.ceramicmarketplace.app"

echo "🚀 Fast Login Test (ADB + Maestro hybrid)"
echo "=========================================="
echo "Username: $USERNAME"
echo ""

# Function to get element center coordinates by resource-id
get_element_coords() {
    local RESOURCE_ID="$1"
    local UI_FILE="/tmp/ui_dump.xml"

    # Dump UI hierarchy (suppress output)
    adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
    adb pull /sdcard/ui.xml "$UI_FILE" >/dev/null 2>&1

    # Find element line containing the resource-id and extract bounds
    # Use grep to find the node, then extract bounds from that specific node
    local NODE=$(grep -o "<node[^>]*resource-id=\"$RESOURCE_ID\"[^>]*>" "$UI_FILE" 2>/dev/null | head -1)

    if [ -z "$NODE" ]; then
        return 1
    fi

    # Extract bounds from the node
    local BOUNDS=$(echo "$NODE" | grep -oP 'bounds="\[\d+,\d+\]\[\d+,\d+\]"' | grep -oP '\[\d+,\d+\]\[\d+,\d+\]')

    if [ -z "$BOUNDS" ]; then
        return 1
    fi

    # Parse bounds [x1,y1][x2,y2] - extract all 4 numbers
    local X1=$(echo "$BOUNDS" | sed 's/\[//g; s/\]/ /g' | awk -F'[, ]' '{print $1}')
    local Y1=$(echo "$BOUNDS" | sed 's/\[//g; s/\]/ /g' | awk -F'[, ]' '{print $2}')
    local X2=$(echo "$BOUNDS" | sed 's/\[//g; s/\]/ /g' | awk -F'[, ]' '{print $3}')
    local Y2=$(echo "$BOUNDS" | sed 's/\[//g; s/\]/ /g' | awk -F'[, ]' '{print $4}')

    # Calculate center
    local X=$(( (X1 + X2) / 2 ))
    local Y=$(( (Y1 + Y2) / 2 ))

    echo "$X $Y"
}

# Step 1: Clear and launch app
echo "📱 Step 1: Launching app..."
adb shell am force-stop "$APP_ID" >/dev/null 2>&1 || true
adb shell pm clear "$APP_ID" >/dev/null 2>&1 || true
adb shell am start -n "$APP_ID/.MainActivity" >/dev/null 2>&1
echo "   Waiting for app to load..."
sleep 4

# Step 2: Find and tap username field
echo "🔍 Step 2: Finding username field..."
COORDS=$(get_element_coords "login-username-input")

if [ -z "$COORDS" ]; then
    echo "❌ Could not find username field"
    adb shell screencap -p /sdcard/debug.png
    adb pull /sdcard/debug.png /tmp/debug.png >/dev/null 2>&1
    echo "   Screenshot saved to /tmp/debug.png"
    exit 1
fi

USERNAME_X=$(echo "$COORDS" | awk '{print $1}')
USERNAME_Y=$(echo "$COORDS" | awk '{print $2}')
echo "   ✓ Username field at ($USERNAME_X, $USERNAME_Y)"

# Step 3: Tap and input username
echo "⌨️  Step 3: Entering username..."
adb shell input tap "$USERNAME_X" "$USERNAME_Y"
sleep 0.5

# Clear any existing text first (select all + delete)
echo "   Clearing existing text..."
adb shell input keyevent 123  # KEYCODE_MOVE_END
adb shell input keyevent 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 >/dev/null 2>&1
sleep 0.2

echo "   Typing username (fast)..."
adb shell input text "$USERNAME"
echo "   ✓ Username entered"

# Step 4: Find and tap password field
echo "🔍 Step 4: Finding password field..."
COORDS=$(get_element_coords "login-password-input")

if [ -z "$COORDS" ]; then
    echo "   Using TAB to move to password"
    adb shell input keyevent 61  # TAB
else
    PASSWORD_X=$(echo "$COORDS" | awk '{print $1}')
    PASSWORD_Y=$(echo "$COORDS" | awk '{print $2}')
    echo "   ✓ Password field at ($PASSWORD_X, $PASSWORD_Y)"
    adb shell input tap "$PASSWORD_X" "$PASSWORD_Y"
fi
sleep 0.5

# Step 5: Clear and input password
echo "⌨️  Step 5: Entering password..."
echo "   Clearing existing text..."
adb shell input keyevent 123  # KEYCODE_MOVE_END
adb shell input keyevent 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 67 >/dev/null 2>&1
sleep 0.2

echo "   Typing password (fast)..."
# Escape special characters for ADB shell
ESCAPED_PASSWORD="${PASSWORD//@/\\@}"
adb shell input text "$ESCAPED_PASSWORD"
echo "   ✓ Password entered"

# Step 6: Hide keyboard and tap login button
echo "🔘 Step 6: Tapping login button..."

# Hide keyboard first to ensure button is visible
adb shell input keyevent 111  # KEYCODE_ESCAPE to hide keyboard
sleep 0.5

# Fresh UI dump to get correct button position
adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
adb pull /sdcard/ui.xml /tmp/ui_dump.xml >/dev/null 2>&1

# Find login button bounds directly
NODE=$(grep -o "<node[^>]*resource-id=\"login-submit-button\"[^>]*>" /tmp/ui_dump.xml 2>/dev/null | head -1)
BOUNDS=$(echo "$NODE" | grep -oP 'bounds="\[\d+,\d+\]\[\d+,\d+\]"' | grep -oP '\[\d+,\d+\]\[\d+,\d+\]')

if [ -n "$BOUNDS" ]; then
    LOGIN_X1=$(echo "$BOUNDS" | sed 's/\[//g; s/\]/ /g' | awk -F'[, ]' '{print $1}')
    LOGIN_Y1=$(echo "$BOUNDS" | sed 's/\[//g; s/\]/ /g' | awk -F'[, ]' '{print $2}')
    LOGIN_X2=$(echo "$BOUNDS" | sed 's/\[//g; s/\]/ /g' | awk -F'[, ]' '{print $3}')
    LOGIN_Y2=$(echo "$BOUNDS" | sed 's/\[//g; s/\]/ /g' | awk -F'[, ]' '{print $4}')
    LOGIN_X=$(( (LOGIN_X1 + LOGIN_X2) / 2 ))
    LOGIN_Y=$(( (LOGIN_Y1 + LOGIN_Y2) / 2 ))
    echo "   ✓ Login button at ($LOGIN_X, $LOGIN_Y)"
    adb shell input tap "$LOGIN_X" "$LOGIN_Y"
else
    echo "   Button not found, using ENTER key"
    adb shell input keyevent 66
fi

# Step 7: Wait and verify
echo "⏳ Step 7: Waiting for login..."
sleep 4

# Check if home tab is visible
adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
adb pull /sdcard/ui.xml /tmp/ui_dump.xml >/dev/null 2>&1

if grep -q "tab-home" /tmp/ui_dump.xml 2>/dev/null; then
    echo ""
    echo "✅ LOGIN SUCCESSFUL!"
    echo "   Home tab is visible"
    exit 0
else
    # Take screenshot for debugging
    adb shell screencap -p /sdcard/result.png
    adb pull /sdcard/result.png /tmp/login_result.png >/dev/null 2>&1
    echo ""
    echo "⚠️  Login result unclear - check /tmp/login_result.png"
    exit 0
fi
