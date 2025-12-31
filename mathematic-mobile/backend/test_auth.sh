#!/bin/bash

# Mathematics Solver API Authentication Test Script

echo "🧪 Testing Mathematics Solver Backend Authentication System"
echo "==========================================================="

API_URL="http://localhost:5000/api/auth"
CONTENT_TYPE="Content-Type: application/json"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_test_header() {
    echo ""
    echo -e "${YELLOW}📋 Test: $1${NC}"
    echo "-------------------"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Test 1: Register a new user
print_test_header "User Registration"
REGISTER_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST "$API_URL/register" \
    -H "$CONTENT_TYPE" \
    -d '{
        "username": "testuser123",
        "email": "test@example.com",
        "password": "Test123!",
        "confirmPassword": "Test123!"
    }')

REGISTER_HTTP_STATUS=$(echo "$REGISTER_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
REGISTER_BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

if [ "$REGISTER_HTTP_STATUS" = "200" ]; then
    print_success "User registration successful"
    TOKEN=$(echo "$REGISTER_BODY" | jq -r '.token // empty')
    if [ -n "$TOKEN" ]; then
        print_success "JWT token received: ${TOKEN:0:20}..."
    else
        print_error "No JWT token in response"
    fi
else
    print_error "Registration failed with status: $REGISTER_HTTP_STATUS"
    echo "Response: $REGISTER_BODY"
fi

# Test 2: Login with the same user
print_test_header "User Login"
LOGIN_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST "$API_URL/login" \
    -H "$CONTENT_TYPE" \
    -d '{
        "username": "testuser123",
        "password": "Test123!"
    }')

LOGIN_HTTP_STATUS=$(echo "$LOGIN_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | sed '$d')

if [ "$LOGIN_HTTP_STATUS" = "200" ]; then
    print_success "User login successful"
    LOGIN_TOKEN=$(echo "$LOGIN_BODY" | jq -r '.token // empty')
    if [ -n "$LOGIN_TOKEN" ]; then
        print_success "JWT token received: ${LOGIN_TOKEN:0:20}..."
    else
        print_error "No JWT token in response"
    fi
else
    print_error "Login failed with status: $LOGIN_HTTP_STATUS"
    echo "Response: $LOGIN_BODY"
fi

# Test 3: Invalid login attempt
print_test_header "Invalid Login Test"
INVALID_LOGIN_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST "$API_URL/login" \
    -H "$CONTENT_TYPE" \
    -d '{
        "username": "testuser123",
        "password": "wrongpassword"
    }')

INVALID_LOGIN_HTTP_STATUS=$(echo "$INVALID_LOGIN_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
INVALID_LOGIN_BODY=$(echo "$INVALID_LOGIN_RESPONSE" | sed '$d')

if [ "$INVALID_LOGIN_HTTP_STATUS" = "401" ]; then
    print_success "Invalid login correctly rejected with 401"
else
    print_error "Invalid login test failed with status: $INVALID_LOGIN_HTTP_STATUS"
    echo "Response: $INVALID_LOGIN_BODY"
fi

# Test 4: Duplicate registration
print_test_header "Duplicate Registration Test"
DUPLICATE_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST "$API_URL/register" \
    -H "$CONTENT_TYPE" \
    -d '{
        "username": "testuser123",
        "email": "test@example.com",
        "password": "Test123!",
        "confirmPassword": "Test123!"
    }')

DUPLICATE_HTTP_STATUS=$(echo "$DUPLICATE_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
DUPLICATE_BODY=$(echo "$DUPLICATE_RESPONSE" | sed '$d')

if [ "$DUPLICATE_HTTP_STATUS" = "400" ]; then
    print_success "Duplicate registration correctly rejected with 400"
else
    print_error "Duplicate registration test failed with status: $DUPLICATE_HTTP_STATUS"
    echo "Response: $DUPLICATE_BODY"
fi

# Test 5: Invalid registration data
print_test_header "Invalid Registration Data Test"
INVALID_REG_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -X POST "$API_URL/register" \
    -H "$CONTENT_TYPE" \
    -d '{
        "username": "ab",
        "email": "invalid-email",
        "password": "123",
        "confirmPassword": "456"
    }')

INVALID_REG_HTTP_STATUS=$(echo "$INVALID_REG_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
INVALID_REG_BODY=$(echo "$INVALID_REG_RESPONSE" | sed '$d')

if [ "$INVALID_REG_HTTP_STATUS" = "400" ]; then
    print_success "Invalid registration data correctly rejected with 400"
else
    print_error "Invalid registration test failed with status: $INVALID_REG_HTTP_STATUS"
    echo "Response: $INVALID_REG_BODY"
fi

echo ""
echo "🏁 Test Summary"
echo "==============="
print_info "To run these tests:"
print_info "1. Make sure MySQL is running with the configured database"
print_info "2. Start the API: cd src/Presentation && dotnet run"
print_info "3. Run this script: ./test_auth.sh"
echo ""
print_info "Expected API endpoints:"
print_info "• POST /api/auth/register - User registration"
print_info "• POST /api/auth/login - User authentication"
echo ""
print_info "API Documentation: https://localhost:5001/swagger (when running in development)"