#!/bin/bash
#
# Health Check Script
# Verifies all services are healthy before cutover operations
#
# Usage:
#   ./health_check.sh
#   ./health_check.sh --verbose
#

set -e

# Configuration
VERBOSE="${1:-}"
TIMEOUT=5

# Service endpoints
declare -A SERVICES=(
    ["auth-service"]="http://auth-service:8007/health/ready"
    ["stock-data-service"]="http://stock-data-service:8001/health/ready"
    ["portfolio-service"]="http://portfolio-service:8003/health/ready"
    ["prediction-service"]="http://prediction-service:8002/health/ready"
    ["analysis-service"]="http://analysis-service:8004/health/ready"
    ["ai-insights-service"]="http://ai-insights-service:8005/health/ready"
    ["chatbot-service"]="http://chatbot-service:8006/health/ready"
    ["feature-flags"]="http://feature-flags:8010/health/ready"
    ["traefik"]="http://traefik:8080/ping"
    ["redis"]="http://redis:6379"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "=========================================="
echo "   SERVICE HEALTH CHECK"
echo "=========================================="
echo ""

HEALTHY=0
UNHEALTHY=0
TOTAL=${#SERVICES[@]}

for service in "${!SERVICES[@]}"; do
    url="${SERVICES[$service]}"

    # Special handling for Redis (not HTTP)
    if [[ "$service" == "redis" ]]; then
        if redis-cli -h redis ping >/dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} ${service}"
            ((HEALTHY++))
        else
            echo -e "  ${RED}✗${NC} ${service} - Connection failed"
            ((UNHEALTHY++))
        fi
        continue
    fi

    # HTTP health check
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout ${TIMEOUT} "${url}" 2>/dev/null) || response="000"

    if [[ "$response" == "200" ]]; then
        echo -e "  ${GREEN}✓${NC} ${service}"
        ((HEALTHY++))

        if [[ "$VERBOSE" == "--verbose" ]]; then
            details=$(curl -s --connect-timeout ${TIMEOUT} "${url}" 2>/dev/null | head -c 200)
            echo "      ${details}"
        fi
    else
        echo -e "  ${RED}✗${NC} ${service} - HTTP ${response}"
        ((UNHEALTHY++))
    fi
done

echo ""
echo "=========================================="
echo "   SUMMARY"
echo "=========================================="
echo ""
echo -e "  Healthy:   ${GREEN}${HEALTHY}${NC} / ${TOTAL}"
echo -e "  Unhealthy: ${RED}${UNHEALTHY}${NC} / ${TOTAL}"
echo ""

if [[ $UNHEALTHY -gt 0 ]]; then
    echo -e "${RED}Some services are unhealthy. Cutover not recommended.${NC}"
    exit 1
else
    echo -e "${GREEN}All services are healthy. Safe to proceed with cutover.${NC}"
    exit 0
fi
