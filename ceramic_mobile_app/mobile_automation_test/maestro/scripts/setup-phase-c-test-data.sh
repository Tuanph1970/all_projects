#!/bin/bash
# =============================================================================
# Setup Phase C Test Data - Customer Product Browsing Tests
# =============================================================================
# Creates prerequisite data for Phase C E2E tests via backend API:
# - Register seller and customer accounts
# - Create 9 products across 3 different categories (3 products each)
#
# Prerequisites:
# - Backend API running on localhost:8002 (auth) and localhost:8000 (products)
# - Fresh database (no existing test_seller_user or test_customer_user)
# =============================================================================

set -e

# Get script directory and source test configuration
SCRIPT_DIR="$(dirname "$(realpath "$0")")"
source "$SCRIPT_DIR/test_config.sh"

# Configuration - API endpoints
AUTH_API_BASE="${API_BASE_URL}/api/v1"
PRODUCT_API_BASE="${API_BASE_URL}/api/v1"

# Use credentials from test_config.sh
# CUSTOMER_USERNAME, CUSTOMER_PASSWORD, CUSTOMER_EMAIL are set in test_config.sh
# SELLER_USERNAME, SELLER_PASSWORD, SELLER_EMAIL are set in test_config.sh
SELLER_FULLNAME="${SELLER_FULL_NAME:-Test Seller}"
SELLER_PHONE="1234567890"
CUSTOMER_FULLNAME="${CUSTOMER_FULL_NAME:-Test Customer}"
CUSTOMER_PHONE="0987654321"

# Logging functions are inherited from test_config.sh
log_step() { _log_step "$1"; }
log_success() { _log_success "$1"; }
log_error() { _log_error "$1"; }
log_info() { _log_info "$1"; }

# Store tokens
SELLER_TOKEN=""
CUSTOMER_TOKEN=""

# =============================================================================
# Helper Functions
# =============================================================================

check_api_health() {
    log_step "Checking API health..."

    # Check API by testing products endpoint (works through nginx)
    local response=$(curl -s -o /dev/null -w "%{http_code}" "${PRODUCT_API_BASE}/products/" 2>/dev/null)
    if [[ "$response" == "200" ]]; then
        log_success "API is healthy (via ${PRODUCT_API_BASE})"
        return 0
    fi

    # Try alternate endpoints
    response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8002/api/v1/products/" 2>/dev/null)
    if [[ "$response" == "200" ]]; then
        # Update to use Traefik directly
        AUTH_API_BASE="http://localhost:8002/api/v1"
        PRODUCT_API_BASE="http://localhost:8002/api/v1"
        log_success "API is healthy (via Traefik port 8002)"
        return 0
    fi

    log_error "API is not accessible. Tried:"
    log_error "  - ${PRODUCT_API_BASE}/products/"
    log_error "  - http://localhost:8002/api/v1/products/"
    return 1
}

register_user() {
    local username="$1"
    local password="$2"
    local email="$3"
    local fullname="$4"
    local phone="$5"
    local role="$6"

    log_step "Registering $role: $username..."

    local response=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_API_BASE}/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"$username\",
            \"email\": \"$email\",
            \"password\": \"$password\",
            \"full_name\": \"$fullname\",
            \"phone_number\": \"$phone\",
            \"role\": \"$role\"
        }")

    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        log_success "Registered $role: $username"
        return 0
    elif [[ "$body" == *"already"* ]] || [[ "$body" == *"taken"* ]]; then
        log_info "$role already exists: $username"
        return 0
    else
        log_error "Failed to register $role: $username (HTTP $http_code)"
        echo "Response: $body"
        return 1
    fi
}

login_user() {
    local username="$1"
    local password="$2"
    local role="$3"

    log_step "Logging in as $role: $username..." >&2

    local response=$(curl -s -w "\n%{http_code}" -X POST "${AUTH_API_BASE}/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"$username\",
            \"password\": \"$password\"
        }")

    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]]; then
        local token=$(echo "$body" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        if [[ -n "$token" ]]; then
            log_success "Logged in as $role" >&2
            echo "$token"
            return 0
        else
            log_error "Failed to extract token from response" >&2
            echo "Response: $body" >&2
            return 1
        fi
    else
        log_error "Failed to login as $role (HTTP $http_code)" >&2
        echo "Response: $body" >&2
        return 1
    fi
}

create_category() {
    local name="$1"
    local description="$2"

    log_step "Creating category: $name..." >&2

    local response=$(curl -s -w "\n%{http_code}" -X POST "${PRODUCT_API_BASE}/products/categories" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"$name\",
            \"description\": \"$description\"
        }")

    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        local category_id=$(echo "$body" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
        log_success "Created category: $name (ID: $category_id)" >&2
        echo "$category_id"
        return 0
    else
        log_error "Failed to create category: $name (HTTP $http_code)" >&2
        echo "Response: $body" >&2
        return 1
    fi
}

get_categories() {
    log_step "Fetching categories..." >&2

    local response=$(curl -s -w "\n%{http_code}" -X GET "${PRODUCT_API_BASE}/products/categories")
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]]; then
        log_success "Fetched categories" >&2
        echo "$body"
        return 0
    else
        log_error "Failed to fetch categories (HTTP $http_code)" >&2
        echo "Response: $body" >&2
        return 1
    fi
}

create_product() {
    local token="$1"
    local name="$2"
    local description="$3"
    local price="$4"
    local quantity="$5"
    local category_id="$6"

    log_step "Creating product: $name (Category ID: $category_id, Price: \$$price)..."

    local response=$(curl -s -w "\n%{http_code}" -X POST "${PRODUCT_API_BASE}/products/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -d "{
            \"name\": \"$name\",
            \"description\": \"$description\",
            \"price\": $price,
            \"quantity_available\": $quantity,
            \"category_id\": $category_id
        }")

    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        local product_id=$(echo "$body" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
        log_success "Created product: $name (ID: $product_id)"
        return 0
    else
        log_error "Failed to create product: $name (HTTP $http_code)"
        echo "Response: $body"
        return 1
    fi
}

# =============================================================================
# Main Setup Flow
# =============================================================================

main() {
    echo ""
    echo "=============================================="
    echo "  Phase C Test Data Setup"
    echo "=============================================="
    echo "Creating prerequisite data for E2E tests:"
    echo "  - Seller account: $SELLER_USERNAME"
    echo "  - Customer account: $CUSTOMER_USERNAME"
    echo "  - 9 products across 3 categories"
    echo "=============================================="
    echo "Time: $(date)"
    echo ""

    # Step 1: Check API health
    if ! check_api_health; then
        log_error "API health check failed. Make sure backend services are running."
        exit 1
    fi

    echo ""
    echo "----------------------------------------------"
    echo "  Step 1: Register Users"
    echo "----------------------------------------------"

    # Step 2: Register seller account
    if ! register_user "$SELLER_USERNAME" "$SELLER_PASSWORD" "$SELLER_EMAIL" "$SELLER_FULLNAME" "$SELLER_PHONE" "seller"; then
        log_error "Failed to register seller account"
        exit 1
    fi

    # Step 3: Register customer account
    if ! register_user "$CUSTOMER_USERNAME" "$CUSTOMER_PASSWORD" "$CUSTOMER_EMAIL" "$CUSTOMER_FULLNAME" "$CUSTOMER_PHONE" "customer"; then
        log_error "Failed to register customer account"
        exit 1
    fi

    echo ""
    echo "----------------------------------------------"
    echo "  Step 2: Login as Seller"
    echo "----------------------------------------------"

    # Step 4: Login as seller to get token
    SELLER_TOKEN=$(login_user "$SELLER_USERNAME" "$SELLER_PASSWORD" "seller")
    if [[ -z "$SELLER_TOKEN" ]] || [[ "$SELLER_TOKEN" == *"FAIL"* ]]; then
        log_error "Failed to get seller token"
        exit 1
    fi

    echo ""
    echo "----------------------------------------------"
    echo "  Step 3: Create/Fetch Categories"
    echo "----------------------------------------------"

    # Step 5: Check existing categories first
    local categories_json=$(get_categories)
    local category_ids=$(echo "$categories_json" | grep -o '"id":[0-9]*' | cut -d':' -f2 | head -3)
    local cat_array=($category_ids)

    # If we don't have 3 categories, create them
    if [[ ${#cat_array[@]} -lt 3 ]]; then
        log_info "Found ${#cat_array[@]} categories. Creating required categories..."

        # Create Category 1: Tableware
        local CAT1=$(create_category "Tableware" "Ceramic plates, bowls, cups and dining accessories")
        if [[ -z "$CAT1" ]] || [[ "$CAT1" == *"FAIL"* ]] || [[ "$CAT1" == *"Response"* ]]; then
            log_error "Failed to create Tableware category"
            exit 1
        fi

        # Create Category 2: Decorative
        local CAT2=$(create_category "Decorative" "Decorative vases, sculptures and art pieces")
        if [[ -z "$CAT2" ]] || [[ "$CAT2" == *"FAIL"* ]] || [[ "$CAT2" == *"Response"* ]]; then
            log_error "Failed to create Decorative category"
            exit 1
        fi

        # Create Category 3: Tiles
        local CAT3=$(create_category "Tiles" "Ceramic tiles for floors, walls and backsplashes")
        if [[ -z "$CAT3" ]] || [[ "$CAT3" == *"FAIL"* ]] || [[ "$CAT3" == *"Response"* ]]; then
            log_error "Failed to create Tiles category"
            exit 1
        fi

        log_success "Created 3 categories successfully"
    else
        local CAT1="${cat_array[0]}"
        local CAT2="${cat_array[1]}"
        local CAT3="${cat_array[2]}"
        log_info "Using existing categories"
    fi

    log_info "Using category IDs: $CAT1, $CAT2, $CAT3"

    echo ""
    echo "----------------------------------------------"
    echo "  Step 4: Create Products"
    echo "----------------------------------------------"

    # Step 6: Create 9 products (3 per category with different price ranges)

    # Category 1 Products (e.g., Tableware) - Low to Medium price
    create_product "$SELLER_TOKEN" "Ceramic Dinner Plate Set" "Beautiful handcrafted ceramic dinner plates perfect for everyday dining. Set of 4 plates with elegant design." 29.99 50 "$CAT1"
    create_product "$SELLER_TOKEN" "Classic Bowl Collection" "Versatile ceramic bowls ideal for soups, salads, and cereal. Modern minimalist design." 19.99 75 "$CAT1"
    create_product "$SELLER_TOKEN" "Premium Tea Cup Set" "Elegant ceramic tea cups with matching saucers. Perfect for afternoon tea service." 45.99 30 "$CAT1"

    # Category 2 Products (e.g., Decorative Items) - Medium to High price
    create_product "$SELLER_TOKEN" "Artisan Ceramic Vase" "Stunning handmade decorative vase with unique glaze finish. Perfect centerpiece for any room." 89.99 20 "$CAT2"
    create_product "$SELLER_TOKEN" "Modern Wall Art Sculpture" "Contemporary ceramic wall sculpture featuring abstract design. Adds artistic flair to your space." 129.99 15 "$CAT2"
    create_product "$SELLER_TOKEN" "Garden Ceramic Figurine" "Charming outdoor ceramic figurine for garden decoration. Weather-resistant finish." 59.99 40 "$CAT2"

    # Category 3 Products (e.g., Tiles) - Various prices for price filter testing
    create_product "$SELLER_TOKEN" "Mosaic Floor Tile Pack" "Premium ceramic mosaic tiles for flooring. Pack of 10 sq ft. Multiple patterns available." 149.99 100 "$CAT3"
    create_product "$SELLER_TOKEN" "Kitchen Backsplash Tiles" "Stylish ceramic tiles perfect for kitchen backsplash. Easy to install and clean." 24.99 200 "$CAT3"
    create_product "$SELLER_TOKEN" "Decorative Wall Tile Set" "Artistic ceramic wall tiles with hand-painted designs. Set of 6 tiles." 79.99 60 "$CAT3"

    echo ""
    echo "----------------------------------------------"
    echo "  Step 5: Mark Products as Featured"
    echo "----------------------------------------------"

    # Get first 3 product IDs and mark as featured for HomeScreen display
    log_step "Marking products as featured for HomeScreen..."
    local product_ids=$(curl -s "${PRODUCT_API_BASE}/products/?limit=3" | grep -o '"id":[0-9]*' | cut -d':' -f2 | head -3)
    for id in $product_ids; do
        curl -s -X PUT "${PRODUCT_API_BASE}/products/$id" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $SELLER_TOKEN" \
            -d '{"is_featured": true}' > /dev/null 2>&1
    done
    log_success "Marked 3 products as featured"

    echo ""
    echo "=============================================="
    echo -e "${GREEN}[SUCCESS]${NC} Phase C Test Data Setup Complete!"
    echo "=============================================="
    echo ""
    echo "Created:"
    echo "  - Seller: $SELLER_USERNAME"
    echo "  - Customer: $CUSTOMER_USERNAME"
    echo "  - 9 Products across 3 categories"
    echo ""
    echo "Product Price Ranges:"
    echo "  - \$19.99 - \$45.99 (Category 1 - Tableware)"
    echo "  - \$59.99 - \$129.99 (Category 2 - Decorative)"
    echo "  - \$24.99 - \$149.99 (Category 3 - Tiles)"
    echo ""
    echo "You can now run Phase C E2E tests:"
    echo "  ./fast-customer-filter-category-test.sh  (PROD-003)"
    echo "  ./fast-customer-filter-price-test.sh     (PROD-004)"
    echo "  ./fast-customer-sort-products-test.sh    (PROD-005)"
    echo "=============================================="

    return 0
}

# Run main
main "$@"
