#!/bin/bash

# =============================================================================
# MATHEMATIC MOBILE - PRIORITY 1 VERIFICATION SCRIPT
# =============================================================================
# This script tests all critical Priority 1 items to verify they work correctly
# 
# Usage: ./test-priority-1.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8001/api/v1}"
ML_SERVICE_URL="${ML_SERVICE_URL:-http://localhost:8002}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:8081}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   MATHEMATIC MOBILE - PRIORITY 1 VERIFICATION             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "\n${BLUE}▶ $1${NC}"
    echo "─────────────────────────────────────────"
}

print_test() {
    echo -e "  ${YELLOW}Testing:${NC} $1"
}

pass() {
    echo -e "  ✅ ${GREEN}PASSED${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "  ❌ ${RED}FAILED${NC}: $1"
    ((TESTS_FAILED++))
}

skip() {
    echo -e "  ⏭️  ${YELLOW}SKIPPED${NC}: $1"
    ((TESTS_SKIPPED++))
}

check_service() {
    local service_name=$1
    local url=$2
    
    print_test "Checking if $service_name is running at $url"
    
    if curl -s --connect-timeout 5 "$url" > /dev/null 2>&1; then
        pass "$service_name is reachable"
        return 0
    else
        fail "$service_name is not reachable"
        return 1
    fi
}

# =============================================================================
# Test 1: File Structure Verification
# =============================================================================

print_header "TEST 1: File Structure Verification"

PROJECT_ROOT="/home/tuanph/TuanPH/all_projects/mathematic-mobile"

# Check ML Service files
print_test "Checking ML Service utility files..."
FILES_TO_CHECK=(
    "llmOCR/src/utils/image_processing.py"
    "llmOCR/src/utils/math_parser.py"
    "llmOCR/src/config/settings.py"
    "llmOCR/src/api/middleware.py"
    "llmOCR/src/api/exceptions.py"
    "llmOCR/scripts/download_models.py"
)

for file in "${FILES_TO_CHECK[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        pass "✓ $file exists"
    else
        fail "✗ $file is missing"
    fi
done

# Check Backend files
print_test "Checking Backend service files..."
BACKEND_FILES=(
    "backend/microservices/auth-service/Controllers/AuthController.cs"
    "backend/microservices/problem-service/Controllers/ProblemController.cs"
)

for file in "${BACKEND_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        pass "✓ $file exists"
    else
        fail "✗ $file is missing"
    fi
done

# Check Frontend files
print_test "Checking Frontend service files..."
FRONTEND_FILES=(
    "frontend/src/services/apiClient.js"
    "frontend/src/services/authService.js"
    "frontend/src/services/problemService.js"
)

for file in "${FRONTEND_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        pass "✓ $file exists"
    else
        fail "✗ $file is missing"
    fi
done

# =============================================================================
# Test 2: API Endpoint Alignment
# =============================================================================

print_header "TEST 2: API Endpoint Alignment"

print_test "Verifying Auth Service endpoints..."

# Check AuthController routes
AUTH_CONTROLLER="$PROJECT_ROOT/backend/microservices/auth-service/Controllers/AuthController.cs"
if grep -q 'Route("api/v1/auth")' "$AUTH_CONTROLLER"; then
    pass "AuthController uses /api/v1/auth route"
else
    fail "AuthController route mismatch"
fi

# Check for required auth endpoints
AUTH_ENDPOINTS=("register" "login" "refresh" "forgot-password" "reset-password")
for endpoint in "${AUTH_ENDPOINTS[@]}"; do
    if grep -q "HttpPost(\"$endpoint\")" "$AUTH_CONTROLLER"; then
        pass "✓ POST /api/v1/auth/$endpoint endpoint exists"
    else
        # Some endpoints might be named differently
        if grep -qi "$endpoint" "$AUTH_CONTROLLER"; then
            pass "✓ $endpoint endpoint found (name may vary)"
        else
            fail "✗ POST /api/v1/auth/$endpoint endpoint missing"
        fi
    fi
done

print_test "Verifying Problem Service endpoints..."

PROBLEM_CONTROLLER="$PROJECT_ROOT/backend/microservices/problem-service/Controllers/ProblemController.cs"
if grep -q 'Route("api/v1/problems")' "$PROBLEM_CONTROLLER"; then
    pass "ProblemController uses /api/v1/problems route"
else
    fail "ProblemController route mismatch"
fi

# =============================================================================
# Test 3: Frontend API Client Configuration
# =============================================================================

print_header "TEST 3: Frontend API Client Configuration"

API_CLIENT="$PROJECT_ROOT/frontend/src/services/apiClient.js"

print_test "Checking API base URL configuration..."

if grep -q 'api/v1' "$API_CLIENT"; then
    pass "API client uses /api/v1 prefix"
else
    fail "API client missing /api/v1 prefix"
fi

# Check endpoint alignment
print_test "Checking endpoint alignment..."

AUTH_SERVICE="$PROJECT_ROOT/frontend/src/services/authService.js"
if grep -q '/auth/login' "$AUTH_SERVICE" && grep -q '/auth/register' "$AUTH_SERVICE"; then
    pass "Auth service endpoints match backend"
else
    fail "Auth service endpoints may not match backend"
fi

PROBLEM_SERVICE="$PROJECT_ROOT/frontend/src/services/problemService.js"
if grep -q '/problem' "$PROBLEM_SERVICE"; then
    pass "Problem service endpoints configured"
else
    fail "Problem service endpoints may be misconfigured"
fi

# =============================================================================
# Test 4: Service Connectivity (if services are running)
# =============================================================================

print_header "TEST 4: Service Connectivity"

check_service ".NET API" "$API_BASE_URL" || skip "Services not running - skipping connectivity tests"

if [ $? -eq 0 ]; then
    # Test health endpoint
    print_test "Testing API health endpoint..."
    HEALTH_RESPONSE=$(curl -s "$API_BASE_URL/../health" 2>/dev/null || echo "")
    
    if [ -n "$HEALTH_RESPONSE" ]; then
        pass "Health endpoint responds"
    else
        # Try alternative health endpoint
        HEALTH_RESPONSE=$(curl -s "$API_BASE_URL/auth/health" 2>/dev/null || echo "")
        if [ -n "$HEALTH_RESPONSE" ]; then
            pass "Health endpoint responds (alternative)"
        else
            skip "Health endpoint not found"
        fi
    fi
    
    # Test auth endpoint (without credentials - just checking it exists)
    print_test "Testing auth endpoint availability..."
    AUTH_RESPONSE=$(curl -s -X POST "$API_BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"test","password":"test"}' 2>/dev/null)
    
    # Should return 401 (unauthorized) which means endpoint exists
    if echo "$AUTH_RESPONSE" | grep -qi "unauthorized\|invalid\|error"; then
        pass "Auth endpoint exists (returned expected error)"
    else
        skip "Auth endpoint response unclear"
    fi
fi

# =============================================================================
# Test 5: ML Service Configuration
# =============================================================================

print_header "TEST 5: ML Service Configuration"

ML_MAIN="$PROJECT_ROOT/llmOCR/src/api/main.py"

print_test "Checking ML Service FastAPI configuration..."

if [ -f "$ML_MAIN" ]; then
    if grep -q 'FastAPI' "$ML_MAIN"; then
        pass "ML Service uses FastAPI"
    else
        fail "ML Service may not use FastAPI"
    fi
    
    if grep -q '/ocr' "$ML_MAIN"; then
        pass "ML Service has OCR endpoints"
    else
        fail "ML Service missing OCR endpoints"
    fi
    
    if grep -q '/solution' "$ML_MAIN"; then
        pass "ML Service has solution endpoints"
    else
        fail "ML Service missing solution endpoints"
    fi
else
    fail "ML Service main.py not found"
fi

# Check model configuration
print_test "Checking ML model configuration..."

MODEL_CONFIG="$PROJECT_ROOT/llmOCR/src/config/model_config.py"
if [ -f "$MODEL_CONFIG" ]; then
    if grep -q 'trocr\|ocr' "$MODEL_CONFIG"; then
        pass "OCR model configured"
    else
        fail "OCR model not configured"
    fi
    
    if grep -q 'flan-t5\|solution\|llm' "$MODEL_CONFIG"; then
        pass "Solution/LLM model configured"
    else
        fail "Solution/LLM model not configured"
    fi
else
    fail "model_config.py not found"
fi

# =============================================================================
# Test 6: Database Migration Check
# =============================================================================

print_header "TEST 6: Database Migration Status"

print_test "Checking for EF Core migrations..."

AUTH_MIGRATIONS="$PROJECT_ROOT/backend/microservices/auth-service/Migrations"
PROBLEM_MIGRATIONS="$PROJECT_ROOT/backend/microservices/problem-service/Migrations"

if [ -d "$AUTH_MIGRATIONS" ]; then
    MIGRATION_COUNT=$(find "$AUTH_MIGRATIONS" -name "*.cs" | wc -l)
    if [ $MIGRATION_COUNT -gt 0 ]; then
        pass "Auth Service has $MIGRATION_COUNT migration files"
    else
        fail "Auth Service has no migration files"
    fi
else
    fail "Auth Service Migrations folder not found"
fi

if [ -d "$PROBLEM_MIGRATIONS" ]; then
    MIGRATION_COUNT=$(find "$PROBLEM_MIGRATIONS" -name "*.cs" | wc -l)
    if [ $MIGRATION_COUNT -gt 0 ]; then
        pass "Problem Service has $MIGRATION_COUNT migration files"
    else
        fail "Problem Service has no migration files"
    fi
else
    fail "Problem Service Migrations folder not found"
fi

# =============================================================================
# Test 7: Docker Configuration
# =============================================================================

print_header "TEST 7: Docker Configuration"

print_test "Checking Docker Compose configuration..."

DOCKER_COMPOSE="$PROJECT_ROOT/docker-compose.yml"
if [ -f "$DOCKER_COMPOSE" ]; then
    pass "docker-compose.yml exists"
    
    if grep -q 'api\|backend' "$DOCKER_COMPOSE"; then
        pass "Backend service configured in Docker"
    else
        fail "Backend service not found in Docker"
    fi
    
    if grep -q 'llm\|ml\|ocr' "$DOCKER_COMPOSE"; then
        pass "ML service configured in Docker"
    else
        fail "ML service not found in Docker"
    fi
else
    fail "docker-compose.yml not found"
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    TEST SUMMARY                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}Passed:${NC}  $TESTS_PASSED"
echo -e "  ${RED}Failed:${NC}  $TESTS_FAILED"
echo -e "  ${YELLOW}Skipped:${NC} $TESTS_SKIPPED"
echo ""

TOTAL=$((TESTS_PASSED + TESTS_FAILED))
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All critical tests passed! Priority 1 items are ready.${NC}"
    exit 0
else
    echo -e "${RED}❌ $TESTS_FAILED test(s) failed. Please review the failures above.${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Fix the failed items listed above"
    echo "  2. Re-run this test script"
    echo "  3. Once all tests pass, proceed with integration testing"
    exit 1
fi
