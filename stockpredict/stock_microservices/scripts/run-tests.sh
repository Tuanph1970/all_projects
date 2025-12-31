#!/bin/bash
# =============================================================================
# Stock Helper Microservices - Test Runner Script
# =============================================================================
#
# Usage:
#   ./scripts/run-tests.sh [options]
#
# Options:
#   --integration    Run integration tests only
#   --e2e            Run end-to-end tests only
#   --performance    Run performance tests only
#   --all            Run all tests
#   --docker         Run tests in Docker environment
#   --local          Run tests against local services
#   --coverage       Generate coverage report
#   --verbose        Verbose output
#   --help           Show this help message
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="integration"
RUN_MODE="local"
COVERAGE=false
VERBOSE=false

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    head -25 "$0" | tail -20
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --integration)
            TEST_TYPE="integration"
            shift
            ;;
        --e2e)
            TEST_TYPE="e2e"
            shift
            ;;
        --performance)
            TEST_TYPE="performance"
            shift
            ;;
        --all)
            TEST_TYPE="all"
            shift
            ;;
        --docker)
            RUN_MODE="docker"
            shift
            ;;
        --local)
            RUN_MODE="local"
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Check services are running (for local mode)
check_services() {
    print_info "Checking service availability..."

    local services=(
        "localhost:8007:auth-service"
        "localhost:8001:stock-data-service"
        "localhost:8003:portfolio-service"
        "localhost:8002:prediction-service"
        "localhost:8004:analysis-service"
    )

    local all_healthy=true

    for service in "${services[@]}"; do
        IFS=':' read -r host port name <<< "$service"
        if curl -sf "http://$host:$port/health/live" > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓${NC} $name is healthy"
        else
            echo -e "  ${RED}✗${NC} $name is not responding"
            all_healthy=false
        fi
    done

    if [ "$all_healthy" = false ]; then
        print_error "Some services are not healthy. Please start them first."
        print_info "Run: docker-compose up -d"
        exit 1
    fi

    print_success "All services are healthy"
}

# Run tests locally
run_local_tests() {
    print_info "Running tests locally..."

    cd "$PROJECT_DIR"

    # Build pytest command
    local pytest_cmd="pytest"

    # Select test directory
    case $TEST_TYPE in
        integration)
            pytest_cmd="$pytest_cmd tests/integration"
            ;;
        e2e)
            pytest_cmd="$pytest_cmd tests/e2e"
            ;;
        performance)
            pytest_cmd="$pytest_cmd tests/performance"
            ;;
        all)
            pytest_cmd="$pytest_cmd tests/"
            ;;
    esac

    # Add options
    if [ "$VERBOSE" = true ]; then
        pytest_cmd="$pytest_cmd -v --tb=long"
    else
        pytest_cmd="$pytest_cmd -v --tb=short"
    fi

    if [ "$COVERAGE" = true ]; then
        pytest_cmd="$pytest_cmd --cov=. --cov-report=html:reports/coverage --cov-report=term-missing"
    fi

    # Add JUnit XML report
    pytest_cmd="$pytest_cmd --junitxml=reports/junit.xml"

    # Create reports directory
    mkdir -p reports

    print_info "Executing: $pytest_cmd"
    echo ""

    # Run tests
    eval "$pytest_cmd"
}

# Run tests in Docker
run_docker_tests() {
    print_info "Running tests in Docker environment..."

    cd "$PROJECT_DIR"

    # Build test environment
    print_info "Building test environment..."
    docker-compose -f docker-compose.test.yml build

    # Start services
    print_info "Starting test services..."
    docker-compose -f docker-compose.test.yml up -d mysql-test redis-test rabbitmq-test

    # Wait for databases
    print_info "Waiting for databases to be ready..."
    sleep 15

    # Start application services
    print_info "Starting application services..."
    docker-compose -f docker-compose.test.yml up -d \
        auth-service-test \
        stock-data-service-test \
        portfolio-service-test \
        prediction-service-test \
        analysis-service-test

    # Wait for services
    print_info "Waiting for services to be healthy..."
    sleep 30

    # Run tests
    print_info "Running tests..."
    docker-compose -f docker-compose.test.yml run --rm test-runner

    # Copy reports
    print_info "Copying test reports..."
    mkdir -p reports
    docker cp test-runner:/app/reports/. reports/ 2>/dev/null || true

    # Cleanup
    print_info "Cleaning up test environment..."
    docker-compose -f docker-compose.test.yml down -v

    print_success "Test run complete. Reports available in ./reports/"
}

# Main execution
main() {
    echo ""
    echo "=============================================="
    echo "  Stock Helper Microservices Test Runner"
    echo "=============================================="
    echo ""
    print_info "Test Type: $TEST_TYPE"
    print_info "Run Mode: $RUN_MODE"
    print_info "Coverage: $COVERAGE"
    print_info "Verbose: $VERBOSE"
    echo ""

    if [ "$RUN_MODE" = "docker" ]; then
        run_docker_tests
    else
        check_services
        run_local_tests
    fi

    echo ""
    print_success "Test execution completed!"
}

main
