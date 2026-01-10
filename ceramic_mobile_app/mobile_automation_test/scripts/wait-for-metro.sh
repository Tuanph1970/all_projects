#!/bin/bash
# =============================================================================
# wait-for-metro.sh - Wait for Metro bundler to be ready
# =============================================================================
# This is a wrapper script that delegates to the main ensure-metro.sh
#
# Usage:
#   ./wait-for-metro.sh              # Wait for Metro (default 120s timeout)
#   ./wait-for-metro.sh --timeout 60 # Custom timeout
#
# This script replaces the old wait-for-metro.js and provides:
#   - Consistent behavior with other Metro scripts
#   - No Node.js dependency
#   - Same timeout (120s) as the original JS version
# =============================================================================

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
MAESTRO_SCRIPTS_DIR="$SCRIPT_DIR/../maestro/scripts"

# Default timeout matches original wait-for-metro.js (120s)
TIMEOUT="${METRO_TIMEOUT:-120}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout|-t)
            TIMEOUT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Wait for Metro bundler to become ready."
            echo ""
            echo "Options:"
            echo "  --timeout, -t N   Set timeout in seconds (default: 120)"
            echo "  --help, -h        Show this help"
            echo ""
            echo "This script only waits for Metro - it does not start it."
            echo "Use ensure-metro.sh if you want to auto-start Metro."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Delegate to ensure-metro.sh with --wait-only mode
export METRO_TIMEOUT="$TIMEOUT"
exec "$MAESTRO_SCRIPTS_DIR/ensure-metro.sh" --wait-only
