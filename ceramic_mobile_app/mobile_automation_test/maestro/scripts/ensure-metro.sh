#!/bin/bash
# =============================================================================
# ensure-metro.sh - Ensures Metro bundler is running before tests
# =============================================================================
# Usage:
#   Source this script at the beginning of test scripts:
#     source "$(dirname "$0")/ensure-metro.sh"
#
#   Or run directly with options:
#     ./ensure-metro.sh                  # Ensure Metro (start if needed)
#     ./ensure-metro.sh --wait-only      # Only wait, don't start
#     ./ensure-metro.sh --check          # Just check status, exit 0/1
#     ./ensure-metro.sh --kill           # Kill existing Metro processes
#     ./ensure-metro.sh --restart        # Kill and restart Metro
# =============================================================================

# Configuration - can be overridden via environment variables
FRONT_END_DIR="${FRONT_END_DIR:-/home/home/all_projects/ceramic_mobile_app/front_end}"
METRO_PORT="${METRO_PORT:-8081}"
METRO_TIMEOUT="${METRO_TIMEOUT:-90}"
METRO_LOG="${METRO_LOG:-/tmp/metro-bundler.log}"

# Mode flags
WAIT_ONLY_MODE=false
CHECK_ONLY_MODE=false
KILL_MODE=false
RESTART_MODE=false

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

# Wait for Metro to become ready (without starting it)
wait_for_metro() {
    echo -e "${BLUE}[METRO]${NC} Waiting for Metro bundler to start..."
    local count=0
    while [ $count -lt $METRO_TIMEOUT ]; do
        if check_metro; then
            echo -e "${GREEN}[METRO]${NC} Metro is ready!"
            return 0
        fi
        sleep 2
        count=$((count + 2))
        if [ $((count % 10)) -eq 0 ] && [ $count -gt 0 ]; then
            echo -e "${YELLOW}[METRO]${NC} Still waiting... (${count}s/${METRO_TIMEOUT}s)"
        fi
    done
    echo -e "${RED}[METRO]${NC} Metro failed to start within ${METRO_TIMEOUT}s"
    return 1
}

# Main function to ensure Metro is running
ensure_metro() {
    echo -e "${BLUE}[METRO]${NC} Checking Metro status..."

    if check_metro; then
        echo -e "${GREEN}[METRO]${NC} Metro is already running and responsive"
        return 0
    fi

    # In wait-only mode, don't start Metro
    if [ "$WAIT_ONLY_MODE" = true ]; then
        echo -e "${YELLOW}[METRO]${NC} Wait-only mode: Metro not running, waiting..."
        wait_for_metro
        return $?
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

# Parse command line arguments when run directly
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --wait-only)
                WAIT_ONLY_MODE=true
                shift
                ;;
            --check)
                CHECK_ONLY_MODE=true
                shift
                ;;
            --kill)
                KILL_MODE=true
                shift
                ;;
            --restart)
                RESTART_MODE=true
                shift
                ;;
            --timeout)
                METRO_TIMEOUT="$2"
                shift 2
                ;;
            --port)
                METRO_PORT="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --wait-only    Only wait for Metro, don't start it"
                echo "  --check        Just check if Metro is running (exit 0/1)"
                echo "  --kill         Kill existing Metro processes"
                echo "  --restart      Kill and restart Metro"
                echo "  --timeout N    Set timeout in seconds (default: 90)"
                echo "  --port N       Set Metro port (default: 8081)"
                echo "  --help, -h     Show this help"
                exit 0
                ;;
            *)
                echo -e "${RED}[METRO]${NC} Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Main execution when run directly (not sourced)
main() {
    parse_args "$@"

    if [ "$CHECK_ONLY_MODE" = true ]; then
        if check_metro; then
            echo -e "${GREEN}[METRO]${NC} Metro is running"
            exit 0
        else
            echo -e "${RED}[METRO]${NC} Metro is not running"
            exit 1
        fi
    fi

    if [ "$KILL_MODE" = true ]; then
        kill_metro
        exit 0
    fi

    if [ "$RESTART_MODE" = true ]; then
        kill_metro
        start_metro
        exit $?
    fi

    ensure_metro
    exit $?
}

# Detect if script is being sourced or run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being run directly
    main "$@"
else
    # Script is being sourced - auto-run ensure_metro
    ensure_metro
fi
