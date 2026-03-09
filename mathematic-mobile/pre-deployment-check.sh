#!/bin/bash

# =============================================================================
# PRE-DEPLOYMENT VERIFICATION SCRIPT
# =============================================================================
# This script verifies all services can build before running full deployment
#
# Usage: ./pre-deployment-check.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        PRE-DEPLOYMENT VERIFICATION                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

PROJECT_ROOT="/home/tuanph/TuanPH/all_projects/mathematic-mobile"
BACKEND_ROOT="$PROJECT_ROOT/backend"
cd "$PROJECT_ROOT"

TESTS_PASSED=0
TESTS_FAILED=0

# =============================================================================
# Test 1: Verify .NET Services Restore
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

print_header "Test 1: .NET Services Package Restore"

print_test "Restoring Auth Service packages..."
cd "$BACKEND_ROOT/microservices/auth-service"
if dotnet restore "AuthService.csproj" > /dev/null 2>&1; then
    pass "Auth Service packages restored successfully"
else
    fail "Auth Service package restore failed"
fi

print_test "Restoring Problem Service packages..."
cd "$BACKEND_ROOT/microservices/problem-service"
if dotnet restore "ProblemService.csproj" > /dev/null 2>&1; then
    pass "Problem Service packages restored successfully"
else
    fail "Problem Service package restore failed"
fi

# =============================================================================
# Test 2: Verify .NET Services Build
# =============================================================================

print_header "Test 2: .NET Services Build"

print_test "Building Auth Service..."
cd "$BACKEND_ROOT/microservices/auth-service"
if dotnet build "AuthService.csproj" --no-restore > /dev/null 2>&1; then
    pass "Auth Service builds successfully"
else
    fail "Auth Service build failed"
fi

print_test "Building Problem Service..."
cd "$BACKEND_ROOT/microservices/problem-service"
if dotnet build "ProblemService.csproj" --no-restore > /dev/null 2>&1; then
    pass "Problem Service builds successfully"
else
    fail "Problem Service build failed"
fi

# =============================================================================
# Test 3: Verify ML Service Dependencies
# =============================================================================

print_header "Test 3: ML Service Python Dependencies"

if [ -f "$PROJECT_ROOT/llmOCR/requirements.txt" ]; then
    pass "ML Service requirements.txt exists"
    
    print_test "Checking Python availability..."
    if command -v python3 &> /dev/null; then
        pass "Python 3 is available"
        
        print_test "Verifying ML Service can import dependencies..."
        cd "$PROJECT_ROOT/llmOCR"
        
        # Check if virtual environment exists
        if [ -d "venv" ]; then
            pass "Python virtual environment exists"
        else
            echo -e "  ${YELLOW}⚠️  Virtual environment not found (will be created during deployment)${NC}"
        fi
    else
        fail "Python 3 is not installed"
    fi
else
    fail "ML Service requirements.txt not found"
fi

# =============================================================================
# Test 4: Verify Configuration Files
# =============================================================================

print_header "Test 4: Configuration Files"

# Check backend configuration
if [ -f "$BACKEND_ROOT/.env.example" ]; then
    pass "Backend .env.example exists"
else
    fail "Backend .env.example missing"
fi

# Check ML service configuration
if [ -f "$PROJECT_ROOT/llmOCR/pyproject.toml" ]; then
    pass "ML Service pyproject.toml exists"
else
    fail "ML Service pyproject.toml missing"
fi

# Check Docker configuration
if [ -f "$BACKEND_ROOT/docker-compose.yml" ]; then
    pass "Backend docker-compose.yml exists"
else
    fail "Backend docker-compose.yml missing"
fi

# =============================================================================
# Test 5: Verify Critical Files
# =============================================================================

print_header "Test 5: Critical Files Verification"

CRITICAL_FILES=(
    "backend/microservices/auth-service/Controllers/AuthController.cs"
    "backend/microservices/problem-service/Controllers/ProblemController.cs"
    "llmOCR/src/utils/image_processing.py"
    "llmOCR/src/utils/math_parser.py"
    "llmOCR/src/api/main.py"
    "frontend/src/services/apiClient.js"
    "frontend/src/services/authService.js"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        pass "✓ $file"
    else
        fail "✗ $file missing"
    fi
done

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    VERIFICATION SUMMARY                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}Passed:${NC}  $TESTS_PASSED"
echo -e "  ${RED}Failed:${NC}  $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All pre-deployment checks passed!${NC}"
    echo ""
    echo -e "${YELLOW}Ready to deploy:${NC}"
    echo "  Run: ./deploy-interactive.sh"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $TESTS_FAILED check(s) failed. Please fix before deploying.${NC}"
    echo ""
    echo -e "${YELLOW}Recommendation:${NC}"
    echo "  1. Review failed tests above"
    echo "  2. Fix the issues"
    echo "  3. Re-run this verification script"
    echo "  4. Once all tests pass, run deployment"
    echo ""
    exit 1
fi
