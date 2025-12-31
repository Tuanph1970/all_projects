#!/bin/bash
# Load test runner script for Stock Helper microservices
# Usage: ./run_load_test.sh [scenario] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
HOST="${HOST:-http://localhost}"
SCENARIO="${1:-smoke}"
USERS="${USERS:-50}"
SPAWN_RATE="${SPAWN_RATE:-5}"
RUN_TIME="${RUN_TIME:-5m}"
HEADLESS="${HEADLESS:-true}"
REPORT_DIR="${REPORT_DIR:-./reports}"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           Stock Helper Load Testing Suite                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo "Usage: $0 [scenario] [options]"
    echo ""
    echo "Scenarios:"
    echo "  smoke       Quick smoke test (5 users, 1 min)"
    echo "  load        Normal load test (50 users, 5 min)"
    echo "  stress      Stress test (up to 2000 users, 12 min)"
    echo "  spike       Spike test (sudden surge to 500 users)"
    echo "  soak        Soak test (30 users, 30 min)"
    echo "  breakpoint  Find breaking point (up to 1000 users)"
    echo "  custom      Custom parameters"
    echo ""
    echo "Options:"
    echo "  --host URL        Target host (default: http://localhost)"
    echo "  --users N         Number of users"
    echo "  --spawn-rate N    Users spawned per second"
    echo "  --run-time T      Test duration (e.g., 5m, 1h)"
    echo "  --headless        Run without web UI (default)"
    echo "  --web             Run with web UI on port 8089"
    echo "  --report-dir DIR  Output directory for reports"
    echo "  --tags TAGS       Filter tests by tags"
    echo ""
    echo "Examples:"
    echo "  $0 smoke"
    echo "  $0 load --host http://staging.example.com"
    echo "  $0 custom --users 100 --spawn-rate 10 --run-time 10m"
    echo "  $0 stress --tags cpu-intensive"
}

setup_scenario() {
    local scenario=$1

    case $scenario in
        smoke)
            USERS=5
            SPAWN_RATE=1
            RUN_TIME="1m"
            LOCUST_FILE="locustfile.py"
            echo -e "${GREEN}Running SMOKE test: Quick functionality check${NC}"
            ;;
        load)
            USERS=50
            SPAWN_RATE=5
            RUN_TIME="5m"
            LOCUST_FILE="locustfile.py"
            echo -e "${GREEN}Running LOAD test: Normal load simulation${NC}"
            ;;
        stress)
            USERS=200
            SPAWN_RATE=10
            RUN_TIME="12m"
            LOCUST_FILE="scenarios/stress_test.py"
            echo -e "${YELLOW}Running STRESS test: Finding breaking points${NC}"
            ;;
        spike)
            RUN_TIME="5m"
            LOCUST_FILE="scenarios/spike_test.py"
            echo -e "${YELLOW}Running SPIKE test: Sudden traffic surge${NC}"
            ;;
        soak)
            USERS=30
            SPAWN_RATE=2
            RUN_TIME="30m"
            LOCUST_FILE="scenarios/soak_test.py"
            echo -e "${GREEN}Running SOAK test: Long-running stability${NC}"
            ;;
        breakpoint)
            USERS=1000
            SPAWN_RATE=20
            RUN_TIME="15m"
            LOCUST_FILE="locustfile.py"
            echo -e "${RED}Running BREAKPOINT test: Maximum capacity${NC}"
            ;;
        custom)
            LOCUST_FILE="locustfile.py"
            echo -e "${BLUE}Running CUSTOM test with provided parameters${NC}"
            ;;
        *)
            echo -e "${RED}Unknown scenario: $scenario${NC}"
            print_usage
            exit 1
            ;;
    esac
}

parse_args() {
    shift # Remove scenario argument

    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                HOST="$2"
                shift 2
                ;;
            --users)
                USERS="$2"
                shift 2
                ;;
            --spawn-rate)
                SPAWN_RATE="$2"
                shift 2
                ;;
            --run-time)
                RUN_TIME="$2"
                shift 2
                ;;
            --headless)
                HEADLESS="true"
                shift
                ;;
            --web)
                HEADLESS="false"
                shift
                ;;
            --report-dir)
                REPORT_DIR="$2"
                shift 2
                ;;
            --tags)
                TAGS="$2"
                shift 2
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                print_usage
                exit 1
                ;;
        esac
    done
}

check_services() {
    echo -e "${BLUE}Checking service availability...${NC}"

    local services=(
        "auth:8007"
        "stock-data:8001"
        "portfolio:8003"
        "analysis:8004"
    )

    local all_up=true

    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        url="${HOST/localhost/localhost}:${port}/health/live"

        if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
            echo -e "  ${GREEN}✓${NC} $name service is up"
        else
            echo -e "  ${RED}✗${NC} $name service is not responding"
            all_up=false
        fi
    done

    if [ "$all_up" = false ]; then
        echo -e "${YELLOW}Warning: Some services are not available${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

prepare_reports() {
    mkdir -p "$REPORT_DIR"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    REPORT_PREFIX="${REPORT_DIR}/${SCENARIO}_${TIMESTAMP}"

    echo -e "${BLUE}Reports will be saved to: ${REPORT_PREFIX}*${NC}"
}

run_locust() {
    cd "$SCRIPT_DIR"

    local cmd="locust -f $LOCUST_FILE --host=$HOST"

    if [ "$HEADLESS" = "true" ]; then
        cmd="$cmd --headless"
        cmd="$cmd --users $USERS"
        cmd="$cmd --spawn-rate $SPAWN_RATE"
        cmd="$cmd --run-time $RUN_TIME"
        cmd="$cmd --html ${REPORT_PREFIX}.html"
        cmd="$cmd --csv ${REPORT_PREFIX}"
    fi

    if [ -n "$TAGS" ]; then
        cmd="$cmd --tags $TAGS"
    fi

    echo ""
    echo -e "${BLUE}Executing: $cmd${NC}"
    echo ""

    eval $cmd

    return $?
}

generate_summary() {
    if [ -f "${REPORT_PREFIX}_stats.csv" ]; then
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}                    TEST SUMMARY                            ${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
        echo ""

        # Parse CSV and display summary
        if command -v python3 &> /dev/null; then
            python3 << EOF
import csv
import sys

try:
    with open('${REPORT_PREFIX}_stats.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if rows:
        total_row = [r for r in rows if r['Name'] == 'Aggregated']
        if total_row:
            t = total_row[0]
            print(f"Total Requests:    {t.get('Request Count', 'N/A')}")
            print(f"Failure Count:     {t.get('Failure Count', 'N/A')}")
            print(f"Avg Response Time: {t.get('Average Response Time', 'N/A')} ms")
            print(f"Min Response Time: {t.get('Min Response Time', 'N/A')} ms")
            print(f"Max Response Time: {t.get('Max Response Time', 'N/A')} ms")
            print(f"Requests/sec:      {t.get('Requests/s', 'N/A')}")

except Exception as e:
    print(f"Could not parse results: {e}")
EOF
        fi

        echo ""
        echo -e "HTML Report: ${GREEN}${REPORT_PREFIX}.html${NC}"
        echo -e "CSV Stats:   ${GREEN}${REPORT_PREFIX}_stats.csv${NC}"
        echo ""
    fi
}

main() {
    print_banner

    if [ $# -eq 0 ]; then
        print_usage
        exit 0
    fi

    SCENARIO="$1"
    setup_scenario "$SCENARIO"
    parse_args "$@"

    echo ""
    echo "Configuration:"
    echo "  Host:       $HOST"
    echo "  Scenario:   $SCENARIO"
    echo "  Users:      $USERS"
    echo "  Spawn Rate: $SPAWN_RATE"
    echo "  Duration:   $RUN_TIME"
    echo "  Headless:   $HEADLESS"
    echo ""

    check_services
    prepare_reports

    echo ""
    echo -e "${GREEN}Starting load test...${NC}"
    echo ""

    if run_locust; then
        generate_summary
        echo -e "${GREEN}Load test completed successfully!${NC}"
    else
        echo -e "${RED}Load test failed!${NC}"
        exit 1
    fi
}

main "$@"
