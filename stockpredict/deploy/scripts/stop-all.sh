#!/bin/bash
# =============================================================================
# Stop All Services - Ceramic + Stock Helper
# =============================================================================
# Usage:
#   ./stop-all.sh [options]
#
# Options:
#   --ceramic-only   Stop only Ceramic API
#   --stock-only     Stop only Stock Helper
#   --react          Also stop React dev server
#   --volumes        Remove volumes (data will be lost!)
#   --all            Stop everything including React
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
CERAMIC_DIR="$BASE_DIR/../ceramic_mobile_app/back_end"
STOCK_DIR="$BASE_DIR/stock_microservices"

# Default options
STOP_CERAMIC=true
STOP_STOCK=true
STOP_REACT=false
REMOVE_VOLUMES=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ceramic-only)
            STOP_CERAMIC=true
            STOP_STOCK=false
            shift
            ;;
        --stock-only)
            STOP_CERAMIC=false
            STOP_STOCK=true
            shift
            ;;
        --react)
            STOP_REACT=true
            shift
            ;;
        --volumes|-v)
            REMOVE_VOLUMES=true
            shift
            ;;
        --all)
            STOP_CERAMIC=true
            STOP_STOCK=true
            STOP_REACT=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}"
echo "============================================"
echo "       Stopping Services"
echo "============================================"
echo -e "${NC}"

VOLUME_FLAG=""
if [ "$REMOVE_VOLUMES" = true ]; then
    VOLUME_FLAG="-v"
    echo -e "${RED}WARNING: Volumes will be removed!${NC}"
fi

# Stop Ceramic
if [ "$STOP_CERAMIC" = true ]; then
    echo -e "${YELLOW}Stopping Ceramic API...${NC}"
    cd "$CERAMIC_DIR"

    # Try both compose files
    docker-compose -f docker-compose.local.yml down $VOLUME_FLAG 2>/dev/null || true
    docker-compose -f docker-compose.prod.yml down $VOLUME_FLAG 2>/dev/null || true

    echo -e "${GREEN}✓ Ceramic API stopped${NC}"
fi

# Stop Stock Helper
if [ "$STOP_STOCK" = true ]; then
    echo -e "${YELLOW}Stopping Stock Helper microservices...${NC}"
    cd "$STOCK_DIR"

    # Try both configurations
    docker-compose -f docker-compose.yml -f docker-compose.local.yml down $VOLUME_FLAG 2>/dev/null || true
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml down $VOLUME_FLAG 2>/dev/null || true

    echo -e "${GREEN}✓ Stock Helper stopped${NC}"
fi

# Stop React
if [ "$STOP_REACT" = true ]; then
    echo -e "${YELLOW}Stopping React development server...${NC}"
    pkill -f "react-scripts start" 2>/dev/null || true
    echo -e "${GREEN}✓ React server stopped${NC}"
fi

echo ""
echo -e "${GREEN}All requested services have been stopped.${NC}"

# Show remaining containers
REMAINING=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "ceramic|stock" || true)
if [ -n "$REMAINING" ]; then
    echo ""
    echo -e "${YELLOW}Note: Some containers may still be running:${NC}"
    echo "$REMAINING"
fi
