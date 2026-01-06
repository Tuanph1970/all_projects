#!/bin/bash
# Fast login wrapper - uses ADB for text input, then Maestro for verification
# Usage: ./fast-login-wrapper.sh [username] [password]

set -e

USERNAME="${1:-test_customer}"
PASSWORD="${2:-Test@12345678}"
APP_ID="com.ceramicmarketplace.app"

echo "🚀 Fast Login Test"
echo "==================="

# Step 1: Launch app with clear state
echo "📱 Launching app..."
adb shell am force-stop "$APP_ID"
adb shell pm clear "$APP_ID"
adb shell am start -n "$APP_ID/.MainActivity"

# Wait for app to load
sleep 3

# Step 2: Tap username field (coordinates may need adjustment)
echo "⌨️  Entering credentials with fast ADB input..."

# Find and tap username field by resource-id
adb shell "input tap \$(dumpsys window | grep -oP 'login-username-input.*?(\d+),(\d+)' | head -1 | grep -oP '\d+' | head -2 | tr '\n' ' ')" 2>/dev/null || {
    # Fallback: use uiautomator to find element
    adb shell uiautomator dump /dev/tty 2>/dev/null | grep -q "login-username-input" && {
        # Get bounds and tap center
        BOUNDS=$(adb shell uiautomator dump /dev/tty 2>/dev/null | grep -oP 'resource-id="[^"]*login-username-input[^"]*"[^>]*bounds="\[\d+,\d+\]\[\d+,\d+\]"' | grep -oP '\[\d+,\d+\]\[\d+,\d+\]')
        if [ -n "$BOUNDS" ]; then
            X1=$(echo "$BOUNDS" | grep -oP '(?<=\[)\d+' | head -1)
            Y1=$(echo "$BOUNDS" | grep -oP '(?<=,)\d+' | head -1)
            X2=$(echo "$BOUNDS" | grep -oP '(?<=\[)\d+' | tail -1)
            Y2=$(echo "$BOUNDS" | grep -oP '(?<=,)\d+' | tail -1)
            X=$(( (X1 + X2) / 2 ))
            Y=$(( (Y1 + Y2) / 2 ))
            adb shell input tap $X $Y
        fi
    }
}

sleep 0.5

# Input username (fast - entire string at once)
adb shell input text "${USERNAME//[@#\$%^&*()!]/_}"
sleep 0.3

# Tap password field and input
adb shell input keyevent 61  # TAB key
sleep 0.3

# Input password (fast - entire string at once)
# Escape special characters for ADB
ESCAPED_PASSWORD=$(echo "$PASSWORD" | sed 's/@/\\@/g; s/#/\\#/g; s/\$/\\$/g')
adb shell input text "$ESCAPED_PASSWORD"
sleep 0.3

# Hide keyboard
adb shell input keyevent 66  # ENTER key (or tap login button)

echo "✅ Credentials entered via fast ADB input"
echo ""
echo "📋 Now running Maestro verification..."

# Step 3: Run Maestro for verification only
cd "$(dirname "$0")/.."
maestro test tests/auth/login-verify.yaml
