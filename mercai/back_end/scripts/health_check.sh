#!/bin/bash
# =============================================================================
# Mercai - Microservices Health Check Script
# =============================================================================
# Usage: ./scripts/health_check.sh [options]
# Options:
#   -v, --verbose    Show detailed output
#   -j, --json       Output in JSON format
#   -s, --service    Check specific service (auth|product|order|chat|seller)
#   -h, --help       Show help message
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TRAEFIK_HOST="${TRAEFIK_HOST:-localhost}"
TRAEFIK_PORT="${TRAEFIK_PORT:-80}"
TIMEOUT="${HEALTH_CHECK_TIMEOUT:-5}"

# Service definitions
declare -A SERVICES=(
    ["auth"]="auth-service:8001"
    ["product"]="product-service:8002"
    ["order"]="order-service:8003"
    ["chat"]="chat-service:8004"
    ["seller"]="seller-service:8005"
)

declare -A SERVICE_ENDPOINTS=(
    ["auth"]="/api/v1/auth"
    ["product"]="/api/v1/products"
    ["order"]="/api/v1/orders"
    ["chat"]="/api/v1/chat"
    ["seller"]="/api/v1/seller"
)

# Infrastructure services
declare -A INFRA_SERVICES=(
    ["traefik"]="localhost:8080"
    ["redis"]="redis:6379"
    ["mysql"]="db:3306"
)

# Flags
VERBOSE=false
JSON_OUTPUT=false
SPECIFIC_SERVICE=""

# Results
declare -A RESULTS
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# =============================================================================
# Functions
# =============================================================================

show_help() {
    echo "Mercai - Microservices Health Check"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -v, --verbose    Show detailed output"
    echo "  -j, --json       Output in JSON format"
    echo "  -s, --service    Check specific service (auth|product|order|chat|seller|all)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Check all services"
    echo "  $0 -v                 # Verbose output"
    echo "  $0 -s auth            # Check only auth service"
    echo "  $0 -j                 # JSON output"
}

log_info() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${GREEN}[✓]${NC} $1"
    fi
}

log_error() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${RED}[✗]${NC} $1"
    fi
}

log_warning() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${YELLOW}[!]${NC} $1"
    fi
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 is required but not installed"
        exit 1
    fi
}

# Check if a service health endpoint responds
check_service_health() {
    local service_name=$1
    local service_addr=$2
    local start_time=$(date +%s%N)

    # Try direct container health check first
    local response=$(docker exec mercai_${service_name}_service curl -sf "http://localhost:${service_addr##*:}/health" 2>/dev/null || echo "FAILED")

    local end_time=$(date +%s%N)
    local duration=$(( (end_time - start_time) / 1000000 ))

    if [ "$response" != "FAILED" ] && echo "$response" | grep -q "healthy"; then
        RESULTS["$service_name"]="healthy:${duration}ms"
        ((PASSED_CHECKS++))
        if [ "$VERBOSE" = true ]; then
            log_success "$service_name: healthy (${duration}ms)"
            echo "    Response: $response"
        else
            log_success "$service_name: healthy (${duration}ms)"
        fi
        return 0
    else
        RESULTS["$service_name"]="unhealthy:${duration}ms"
        ((FAILED_CHECKS++))
        log_error "$service_name: unhealthy"
        return 1
    fi
}

# Check via Traefik gateway
check_service_via_gateway() {
    local service_name=$1
    local endpoint=$2
    local start_time=$(date +%s%N)

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time $TIMEOUT \
        "http://${TRAEFIK_HOST}:${TRAEFIK_PORT}${endpoint}" 2>/dev/null || echo "000")

    local end_time=$(date +%s%N)
    local duration=$(( (end_time - start_time) / 1000000 ))

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 500 ]; then
        if [ "$VERBOSE" = true ]; then
            log_success "$service_name via gateway: OK (HTTP $http_code, ${duration}ms)"
        fi
        return 0
    else
        if [ "$VERBOSE" = true ]; then
            log_warning "$service_name via gateway: HTTP $http_code (${duration}ms)"
        fi
        return 1
    fi
}

# Check Docker container status
check_container_status() {
    local container_name=$1
    local status=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null || echo "not_found")
    local health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")

    if [ "$status" = "running" ]; then
        if [ "$health" = "healthy" ] || [ "$health" = "none" ]; then
            return 0
        fi
    fi
    return 1
}

# Check infrastructure services
check_infrastructure() {
    log_info "Checking infrastructure services..."
    echo ""

    # Check MySQL
    ((TOTAL_CHECKS++))
    if docker exec mercai_mysql mysqladmin ping -h localhost -u root -p${DB_ROOT_PASSWORD:-rootpassword} --silent 2>/dev/null; then
        RESULTS["mysql"]="healthy"
        ((PASSED_CHECKS++))
        log_success "MySQL: healthy"
    else
        RESULTS["mysql"]="unhealthy"
        ((FAILED_CHECKS++))
        log_error "MySQL: unhealthy"
    fi

    # Check Redis
    ((TOTAL_CHECKS++))
    if docker exec mercai_redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        RESULTS["redis"]="healthy"
        ((PASSED_CHECKS++))
        log_success "Redis: healthy"
    else
        RESULTS["redis"]="unhealthy"
        ((FAILED_CHECKS++))
        log_error "Redis: unhealthy"
    fi

    # Check Traefik
    ((TOTAL_CHECKS++))
    if curl -sf "http://localhost:8080/api/overview" --max-time $TIMEOUT >/dev/null 2>&1; then
        RESULTS["traefik"]="healthy"
        ((PASSED_CHECKS++))
        log_success "Traefik: healthy"
    else
        RESULTS["traefik"]="unhealthy"
        ((FAILED_CHECKS++))
        log_error "Traefik: unhealthy"
    fi

    echo ""
}

# Check all microservices
check_microservices() {
    log_info "Checking microservices..."
    echo ""

    for service in "${!SERVICES[@]}"; do
        if [ -n "$SPECIFIC_SERVICE" ] && [ "$SPECIFIC_SERVICE" != "$service" ] && [ "$SPECIFIC_SERVICE" != "all" ]; then
            continue
        fi

        ((TOTAL_CHECKS++))
        check_service_health "$service" "${SERVICES[$service]}"

        # Also check via gateway if verbose
        if [ "$VERBOSE" = true ]; then
            check_service_via_gateway "$service" "${SERVICE_ENDPOINTS[$service]}"
        fi
    done

    echo ""
}

# Generate JSON output
output_json() {
    echo "{"
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"summary\": {"
    echo "    \"total\": $TOTAL_CHECKS,"
    echo "    \"passed\": $PASSED_CHECKS,"
    echo "    \"failed\": $FAILED_CHECKS,"
    echo "    \"status\": \"$([ $FAILED_CHECKS -eq 0 ] && echo 'healthy' || echo 'degraded')\""
    echo "  },"
    echo "  \"services\": {"

    local first=true
    for service in "${!RESULTS[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            echo ","
        fi
        local status="${RESULTS[$service]%%:*}"
        local latency="${RESULTS[$service]#*:}"
        echo -n "    \"$service\": {\"status\": \"$status\", \"latency\": \"$latency\"}"
    done

    echo ""
    echo "  }"
    echo "}"
}

# Print summary
print_summary() {
    echo "============================================="
    echo "Health Check Summary"
    echo "============================================="
    echo -e "Total Checks:  ${BLUE}$TOTAL_CHECKS${NC}"
    echo -e "Passed:        ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Failed:        ${RED}$FAILED_CHECKS${NC}"
    echo ""

    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "Overall Status: ${GREEN}HEALTHY${NC}"
        exit 0
    else
        echo -e "Overall Status: ${RED}DEGRADED${NC}"
        exit 1
    fi
}

# =============================================================================
# Main
# =============================================================================

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -j|--json)
            JSON_OUTPUT=true
            shift
            ;;
        -s|--service)
            SPECIFIC_SERVICE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check required commands
check_command "docker"
check_command "curl"

# Run health checks
if [ "$JSON_OUTPUT" = false ]; then
    echo ""
    echo "============================================="
    echo "Mercai - Health Check"
    echo "============================================="
    echo "Timestamp: $(date)"
    echo ""
fi

if [ -z "$SPECIFIC_SERVICE" ] || [ "$SPECIFIC_SERVICE" = "all" ]; then
    check_infrastructure
fi

check_microservices

# Output results
if [ "$JSON_OUTPUT" = true ]; then
    output_json
else
    print_summary
fi
