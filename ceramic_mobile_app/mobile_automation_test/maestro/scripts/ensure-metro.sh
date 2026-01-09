#!/bin/bash
# =============================================================================
# ensure-metro.sh - Ensures Metro bundler is running before tests
# =============================================================================
# Source this script at the beginning of test scripts:
#   source "$(dirname "$0")/ensure-metro.sh"
# =============================================================================

FRONT_END_DIR="/home/tuanph/TuanPH/all_projects/ceramic_mobile_app/front_end"
METRO_PORT=8081
METRO_TIMEOUT=90
METRO_LOG="/tmp/metro-bundler.log"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if Metro/Expo is running and responsive
check_metro() {
    # Try standard Metro status endpoint
    if curl -s "http://localhost:${METRO_PORT}/status" 2>/dev/null | grep -q "packager-status:running"; then
        return 0
    fi
    # Try Expo status endpoint
    if curl -s "http://localhost:${METRO_PORT}" 2>/dev/null | grep -q -i "expo\|metro\|react"; then
        return 0
    fi
    # Check if port is listening
    if nc -z localhost ${METRO_PORT} 2>/dev/null; then
        # Port is open, try to fetch something
        local response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${METRO_PORT}/" 2>/dev/null)
        if [ "$response" = "200" ] || [ "$response" = "404" ]; then
            return 0
        fi
    fi
    return 1
}

# Check if Metro/Expo process exists
check_metro_process() {
    pgrep -f "react-native.*start" > /dev/null 2>&1 || \
    pgrep -f "metro" > /dev/null 2>&1 || \
    pgrep -f "expo.*start" > /dev/null 2>&1 || \
    pgrep -f "start-expo" > /dev/null 2>&1
}

# Kill existing Metro/Expo processes
kill_metro() {
    echo -e "${YELLOW}[METRO]${NC} Killing existing Metro/Expo processes..."
    pkill -f "react-native.*start" 2>/dev/null
    pkill -f "metro" 2>/dev/null
    pkill -f "expo.*start" 2>/dev/null
    pkill -f "start-expo" 2>/dev/null
    sleep 2
}

# Start Metro bundler
start_metro() {
    echo -e "${YELLOW}[METRO]${NC} Starting Metro bundler..."
    echo -e "${BLUE}[METRO]${NC} Frontend dir: $FRONT_END_DIR"

    # Check if frontend directory exists
    if [ ! -d "$FRONT_END_DIR" ]; then
        echo -e "${RED}[METRO]${NC} Frontend directory not found: $FRONT_END_DIR"
        return 1
    fi

    # Start Metro in background using npm start (Expo project)
    cd "$FRONT_END_DIR"
    npm start > "$METRO_LOG" 2>&1 &
    METRO_PID=$!
    echo -e "${BLUE}[METRO]${NC} Metro PID: $METRO_PID"
    echo -e "${BLUE}[METRO]${NC} Metro log: $METRO_LOG"

    # Wait for Metro to be ready
    local count=0
    while [ $count -lt $METRO_TIMEOUT ]; do
        if check_metro; then
            echo -e "${GREEN}[METRO]${NC} Metro is ready!"
            # Give it a few more seconds to fully stabilize
            sleep 3
            return 0
        fi
        sleep 2
        count=$((count + 2))
        echo -e "${YELLOW}[METRO]${NC} Waiting for Metro... (${count}s/${METRO_TIMEOUT}s)"
    done

    echo -e "${RED}[METRO]${NC} Failed to start Metro within ${METRO_TIMEOUT}s"
    echo -e "${RED}[METRO]${NC} Check log: $METRO_LOG"
    tail -20 "$METRO_LOG" 2>/dev/null
    return 1
}

# Main function to ensure Metro is running
ensure_metro() {
    echo -e "${BLUE}[METRO]${NC} Checking Metro status..."

    if check_metro; then
        echo -e "${GREEN}[METRO]${NC} Metro is already running and responsive"
        return 0
    fi

    # Metro not responding, check if process exists
    if check_metro_process; then
        echo -e "${YELLOW}[METRO]${NC} Metro process exists but not responding, restarting..."
        kill_metro
    fi

    # Start fresh Metro
    start_metro
    return $?
}

# Auto-run when sourced
ensure_metro
