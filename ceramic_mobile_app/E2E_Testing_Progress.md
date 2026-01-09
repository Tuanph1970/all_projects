# E2E Testing Progress - Ceramic Marketplace Mobile App

**Testing Framework:** Maestro + ADB Hybrid
**Last Updated:** January 9, 2026
**Status:** Active Development

---

## Overview

This document tracks the E2E test cases for the Ceramic Marketplace mobile application using Maestro testing framework. Tests are organized by user role and feature domain.

---

## Hybrid Testing Approach (ADB + Maestro)

Due to Maestro 2.x having extremely slow text input (5 seconds per character), we implemented a **hybrid testing approach** that combines:

- **Maestro**: App launching, element detection, tapping, scrolling, screenshots, assertions
- **ADB (Android Debug Bridge)**: Fast text input using `adb shell input text`

### Fast Seller Test Scripts

Located in `mobile_automation_test/maestro/scripts/`:

| Script | Description | Status |
|--------|-------------|--------|
| `fast-seller-login-test.sh` | Seller login with fast ADB input | ✅ Passing |
| `fast-seller-analytics-test.sh` | Analytics dashboard testing | ✅ Passing |
| `fast-seller-product-management-test.sh` | Product list & management | ✅ Passing |
| `fast-seller-add-product-test.sh` | Add new product with form filling | ✅ Passing |
| `run-all-seller-tests.sh` | Run entire seller test suite | ✅ Available |

### Running Fast Tests

```bash
# Navigate to maestro directory
cd mobile_automation_test/maestro

# Run individual fast test
./scripts/fast-seller-login-test.sh
./scripts/fast-seller-analytics-test.sh
./scripts/fast-seller-product-management-test.sh
./scripts/fast-seller-add-product-test.sh

# Run all seller tests
./scripts/run-all-seller-tests.sh
```

---

## User Roles

The application supports three user roles:

| Role | Description | Access Level |
|------|-------------|--------------|
| **Customer** | End users who browse and purchase ceramic products | Product browsing, cart, orders, reviews, chat |
| **Seller** | Artisans and vendors who sell ceramic products | All customer features + product management, dashboard, analytics, order fulfillment |
| **Dual** | Users with both customer and seller capabilities | Full access to all features with role switching |

---

## Test Status Legend

| Status | Symbol | Description |
|--------|--------|-------------|
| Implemented | ✅ | Test case is implemented and passing |
| In Progress | 🔄 | Test case is being developed |
| Planned | 📋 | Test case is defined but not yet implemented |
| Blocked | ⚠️ | Test case blocked by dependencies/issues |
| Not Started | ⬜ | Test case not yet planned in detail |

---

## Test Case Summary

### Authentication Tests

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| AUTH-001 | Successful Customer Login | Customer | ✅ | `tests/auth/login.yaml` | P0 |
| AUTH-002 | Successful Seller Login | Seller | ✅ | `flows/seller-login-flow.yaml` | P0 |
| AUTH-003 | Login with Invalid Password | All | ✅ | `tests/auth/login-failure.yaml` | P1 |
| AUTH-004 | Login with Non-existent User | All | ✅ | `tests/auth/login-failure.yaml` | P1 |
| AUTH-005 | Login with Empty Fields | All | ✅ | `tests/auth/login-failure.yaml` | P1 |
| AUTH-006 | Customer Registration | Customer | ✅ | `tests/auth/register.yaml` | P0 |
| AUTH-007 | Seller Registration | Seller | 📋 | - | P1 |
| AUTH-008 | Dual Role Registration | Dual | 📋 | - | P2 |
| AUTH-009 | Logout Flow | All | ✅ | `tests/auth/logout.yaml` | P0 |
| AUTH-010 | Change Password | All | ✅ | `tests/auth/change-password.yaml` | P1 |
| AUTH-011 | Forgot Password Request | All | ✅ | `tests/auth/reset-password.yaml` | P1 |
| AUTH-012 | Password Reset with Token | All | 📋 | - | P2 |
| AUTH-013 | Email Verification Flow | All | 📋 | - | P2 |
| AUTH-014 | Resend Verification Email | All | 📋 | - | P3 |
| AUTH-015 | Role Switch (Dual User) | Dual | 📋 | - | P2 |
| AUTH-016 | Session Persistence | All | 📋 | - | P2 |
| AUTH-017 | Token Refresh | All | 📋 | - | P2 |

---

### Customer Features

#### Product Browsing

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| PROD-001 | Browse Product Catalog | Customer | ✅ | `tests/product/browse-products.yaml` | P0 |
| PROD-002 | Search Products by Keyword | Customer | ✅ | `tests/product/browse-products.yaml` | P0 |
| PROD-003 | Filter Products by Category | Customer | ✅ | `tests/product/browse-products.yaml` | P1 |
| PROD-004 | Filter Products by Price Range | Customer | 📋 | - | P2 |
| PROD-005 | Sort Products (Price/Date/Name) | Customer | 📋 | - | P2 |
| PROD-006 | View Product Details | Customer | ✅ | `tests/product/browse-products.yaml` | P0 |
| PROD-007 | View Product Image Gallery | Customer | 📋 | - | P2 |
| PROD-008 | View Seller Information | Customer | 📋 | - | P3 |
| PROD-009 | View Product Reviews | Customer | 📋 | - | P2 |
| PROD-010 | View Related Products | Customer | 📋 | - | P3 |

#### Shopping Cart

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| CART-001 | Add Product to Cart | Customer | ✅ | `tests/cart/add-to-cart.yaml` | P0 |
| CART-002 | Update Cart Item Quantity | Customer | ✅ | `tests/cart/add-to-cart.yaml` | P1 |
| CART-003 | Remove Item from Cart | Customer | ✅ | `tests/cart/add-to-cart.yaml` | P1 |
| CART-004 | View Cart Summary | Customer | ✅ | `tests/cart/add-to-cart.yaml` | P0 |
| CART-005 | Cart Persistence After Logout | Customer | 📋 | - | P2 |
| CART-006 | Add Multiple Products to Cart | Customer | 📋 | - | P2 |
| CART-007 | Cart Total Calculation | Customer | 📋 | - | P1 |
| CART-008 | Out of Stock Item Handling | Customer | 📋 | - | P2 |

#### Checkout & Orders

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| ORD-001 | Complete Checkout Flow | Customer | 📋 | - | P0 |
| ORD-002 | Add Shipping Address | Customer | 📋 | - | P1 |
| ORD-003 | Select Shipping Address | Customer | 📋 | - | P1 |
| ORD-004 | View Order Confirmation | Customer | 📋 | - | P1 |
| ORD-005 | View Order History | Customer | 📋 | - | P1 |
| ORD-006 | View Order Details | Customer | 📋 | - | P1 |
| ORD-007 | Track Order Status | Customer | 📋 | - | P2 |
| ORD-008 | Cancel Order | Customer | 📋 | - | P2 |

#### Reviews & Ratings

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| REV-001 | Submit Product Review | Customer | 📋 | - | P2 |
| REV-002 | Rate Product (Stars) | Customer | 📋 | - | P2 |
| REV-003 | Edit Review | Customer | 📋 | - | P3 |
| REV-004 | Delete Review | Customer | 📋 | - | P3 |
| REV-005 | View My Reviews | Customer | 📋 | - | P3 |

#### Chat & Communication

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| CHAT-001 | Start Chat with Seller | Customer | 📋 | - | P2 |
| CHAT-002 | Send Text Message | Customer | 📋 | - | P2 |
| CHAT-003 | Send Image in Chat | Customer | 📋 | - | P3 |
| CHAT-004 | View Chat History | Customer | 📋 | - | P2 |
| CHAT-005 | Chat Notifications | Customer | 📋 | - | P3 |

#### Profile Management

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| PROF-001 | View Profile | Customer | 📋 | - | P2 |
| PROF-002 | Edit Profile Information | Customer | 📋 | - | P2 |
| PROF-003 | Update Profile Photo | Customer | 📋 | - | P3 |
| PROF-004 | Manage Shipping Addresses | Customer | 📋 | - | P2 |

---

### Seller Features

#### Seller Dashboard

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| DASH-001 | View Dashboard Overview | Seller | ✅ | `tests/seller/dashboard.yaml` | P0 |
| DASH-002 | View Sales Statistics | Seller | ✅ | `tests/seller/dashboard.yaml` | P1 |
| DASH-003 | View Recent Orders Widget | Seller | ✅ | `tests/seller/dashboard.yaml` | P1 |
| DASH-004 | View Alert Notifications | Seller | ✅ | `tests/seller/dashboard.yaml` | P2 |
| DASH-005 | View Sales Chart | Seller | ✅ | `tests/seller/dashboard.yaml` | P2 |
| DASH-006 | Dashboard Data Refresh | Seller | 📋 | - | P3 |
| DASH-007 | Select Time Period Filter | Seller | 📋 | - | P2 |

#### Product Management

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| SPM-001 | Add New Product | Seller | ✅ | `tests/seller/add-product.yaml` | P0 |
| SPM-002 | Add Product with Images | Seller | ✅ | `tests/seller/add-product.yaml` | P1 |
| SPM-003 | View Product List | Seller | ✅ | `tests/seller/product-management.yaml` | P0 |
| SPM-004 | Search My Products | Seller | ✅ | `tests/seller/product-management.yaml` | P1 |
| SPM-005 | Filter Products by Status | Seller | ✅ | `tests/seller/product-management.yaml` | P2 |
| SPM-006 | Edit Product Details | Seller | 📋 | - | P1 |
| SPM-007 | Update Product Stock | Seller | 📋 | - | P1 |
| SPM-008 | Deactivate Product | Seller | 📋 | - | P2 |
| SPM-009 | Delete Product | Seller | 📋 | - | P2 |
| SPM-010 | Bulk Product Operations | Seller | ✅ | `tests/seller/product-management.yaml` | P2 |
| SPM-011 | Set Product as Featured | Seller | 📋 | - | P3 |

#### Seller Analytics

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| ANA-001 | View Sales Analytics | Seller | ✅ | `tests/seller/analytics.yaml` | P1 |
| ANA-002 | View Revenue Trends | Seller | ✅ | `tests/seller/analytics.yaml` | P1 |
| ANA-003 | View Inventory Status | Seller | ✅ | `tests/seller/analytics.yaml` | P2 |
| ANA-004 | View Top Products | Seller | ✅ | `tests/seller/analytics.yaml` | P2 |
| ANA-005 | Select Analytics Period | Seller | ✅ | `tests/seller/analytics.yaml` | P2 |
| ANA-006 | Export Analytics Data | Seller | 📋 | - | P3 |
| ANA-007 | View Customer Demographics | Seller | 📋 | - | P3 |

#### Order Fulfillment

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| FUL-001 | View Incoming Orders | Seller | 📋 | - | P0 |
| FUL-002 | Accept Order | Seller | 📋 | - | P0 |
| FUL-003 | Reject Order | Seller | 📋 | - | P1 |
| FUL-004 | Mark Order as Shipped | Seller | 📋 | - | P0 |
| FUL-005 | Add Tracking Information | Seller | 📋 | - | P1 |
| FUL-006 | Mark Order as Delivered | Seller | 📋 | - | P1 |
| FUL-007 | View Order History | Seller | 📋 | - | P2 |
| FUL-008 | Filter Orders by Status | Seller | 📋 | - | P2 |

#### Seller Profile

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| SPR-001 | View Seller Profile | Seller | 📋 | - | P2 |
| SPR-002 | Edit Shop Information | Seller | 📋 | - | P2 |
| SPR-003 | Update Shop Banner | Seller | 📋 | - | P3 |
| SPR-004 | Update Business License | Seller | 📋 | - | P3 |

---

### Dual Role Features

| # | Test Case | Role | Status | File | Priority |
|---|-----------|------|--------|------|----------|
| DUAL-001 | Switch from Customer to Seller | Dual | 📋 | - | P1 |
| DUAL-002 | Switch from Seller to Customer | Dual | 📋 | - | P1 |
| DUAL-003 | Access Customer Features in Dual Mode | Dual | 📋 | - | P2 |
| DUAL-004 | Access Seller Features in Dual Mode | Dual | 📋 | - | P2 |
| DUAL-005 | Upgrade from Customer to Dual | Dual | 📋 | - | P2 |
| DUAL-006 | Upgrade from Seller to Dual | Dual | 📋 | - | P2 |

---

## Test Progress Summary

### By Status

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Implemented | 26 | 27% |
| ✅ Fast Scripts (Hybrid) | 4 | 4% |
| 📋 Planned | 66 | 69% |
| 🔄 In Progress | 0 | 0% |
| ⚠️ Blocked | 0 | 0% |
| **Total** | **96** | **100%** |

### Fast Seller Test Scripts (Hybrid ADB + Maestro)

| Test Script | Tests Covered | Status |
|-------------|---------------|--------|
| `fast-seller-login-test.sh` | AUTH-002 | ✅ Passing |
| `fast-seller-analytics-test.sh` | ANA-001 to ANA-005 | ✅ Passing |
| `fast-seller-product-management-test.sh` | SPM-003, SPM-004, SPM-010 | ✅ Passing |
| `fast-seller-add-product-test.sh` | SPM-001, SPM-002 | ✅ Passing |

### By Role Coverage

| Role | Implemented | Planned | Total |
|------|-------------|---------|-------|
| Customer | 10 | 38 | 48 |
| Seller | 16 | 22 | 38 |
| Dual | 0 | 6 | 6 |
| All (Auth) | 10 | 7 | 17 |

### By Priority

| Priority | Implemented | Planned | Total |
|----------|-------------|---------|-------|
| P0 (Critical) | 12 | 3 | 15 |
| P1 (High) | 12 | 14 | 26 |
| P2 (Medium) | 6 | 34 | 40 |
| P3 (Low) | 0 | 15 | 15 |

---

## Test Suites

The following test suites are configured in `test-suites.yaml`:

### Smoke Test Suite
**Purpose:** Critical user journeys for quick validation
**Timeout:** 30 minutes
**Tests:**
- Login (Customer)
- Register
- Browse Products
- Add to Cart
- Seller Dashboard

### Authentication Test Suite
**Purpose:** Complete authentication coverage
**Timeout:** 20 minutes
**Tests:**
- Login Success
- Login Failure Scenarios
- Register
- Logout
- Change Password
- Reset Password

### Seller Test Suite
**Purpose:** Seller feature validation
**Timeout:** 25 minutes
**Tests:**
- Dashboard
- Add Product
- Product Management
- Analytics

### Customer Test Suite
**Purpose:** Customer shopping journey
**Timeout:** 20 minutes
**Tests:**
- Browse Products
- Add to Cart

### Regression Test Suite
**Purpose:** Full regression coverage
**Timeout:** 60 minutes
**Tests:**
- All authentication tests
- Product browsing
- Cart operations
- Seller dashboard and products

### Quick Test Suite
**Purpose:** Essential tests for rapid feedback
**Timeout:** 10 minutes
**Tests:**
- Login
- Seller Dashboard

### Fast Seller Test Suite (Hybrid)
**Purpose:** Complete seller flow validation with fast ADB input
**Timeout:** 15 minutes
**Scripts:**
- `fast-seller-login-test.sh` - Seller authentication
- `fast-seller-analytics-test.sh` - Analytics dashboard & metrics
- `fast-seller-product-management-test.sh` - Product list & management
- `fast-seller-add-product-test.sh` - Product creation flow

**Run Command:** `./scripts/run-all-seller-tests.sh`

---

## Test Execution Commands

```bash
# Navigate to test directory
cd mobile_automation_test/maestro

# Run individual test
maestro test tests/auth/login.yaml

# Run test suite
maestro test --suite=smoke
maestro test --suite=auth
maestro test --suite=seller
maestro test --suite=customer
maestro test --suite=regression
maestro test --suite=quick

# Run with specific device
maestro test --device=emulator-5554 tests/auth/login.yaml

# Run all tests in a directory
maestro test tests/auth/
maestro test tests/seller/

# Generate HTML report
maestro test --format=html --output=reports/ tests/auth/
```

---

## Test Environment Configuration

### Required Environment Variables

```yaml
# Test credentials (defined in config/maestro.yaml)
TEST_CUSTOMER_USERNAME: "test_customer"
TEST_SELLER_USERNAME: "test_seller"
TEST_PASSWORD: "Test@12345678"

# API endpoints
API_BASE_URL: "http://localhost:8002"
AUTH_SERVICE_URL: "http://localhost:8002/api/auth"
PRODUCT_SERVICE_URL: "http://localhost:8002/api/products"
ORDER_SERVICE_URL: "http://localhost:8002/api/orders"
SELLER_SERVICE_URL: "http://localhost:8002/api/sellers"
```

### Device Configurations

| Platform | Device | API/Version |
|----------|--------|-------------|
| Android | Pixel_4 | API 30 |
| iOS | iPhone 14 | iOS 16.0 |

---

## Roadmap

### Phase 1: Core Authentication (Completed)
- [x] Login flows (customer, seller)
- [x] Registration flow
- [x] Logout flow
- [x] Password management

### Phase 2: Customer Shopping Journey (In Progress)
- [x] Product browsing
- [x] Cart operations
- [ ] Checkout flow
- [ ] Order management

### Phase 3: Seller Operations (Completed - Using Hybrid Approach)
- [x] Dashboard
- [x] Product management
- [x] Analytics
- [x] Add Product
- [x] Seller Login (Fast ADB)
- [ ] Order fulfillment

### Phase 4: Advanced Features (Planned)
- [ ] Chat functionality
- [ ] Reviews and ratings
- [ ] Profile management
- [ ] Dual role features

### Phase 5: Edge Cases & Error Handling (Planned)
- [ ] Network error handling
- [ ] Session timeout scenarios
- [ ] Input validation edge cases
- [ ] Concurrent user scenarios

---

## Recent Bug Fixes (January 9, 2026)

### Bug Fix Summary

During E2E testing of the Add Product flow, several bugs were discovered and fixed:

| Bug | File | Root Cause | Fix Applied |
|-----|------|------------|-------------|
| **"Product Not Found" error** | `front_end/src/store/slices/productSlice.js:100` | Method `productService.getProduct()` doesn't exist | Changed to `productService.getProductById()` |
| **Tags rendering crash** | `front_end/src/screens/product/ProductDetailsScreen.jsx:167-197` | `product.tags.map()` fails when tags is a string instead of array | Added string-to-array conversion with `Array.isArray()` check |
| **Navigation flow issue** | `mobile_automation_test/maestro/scripts/fast-seller-add-product-test.sh` | Test tried to tap FAB on Dashboard instead of Products tab | Added navigation to Products tab before tapping `product-management-fab-add` |
| **Keyboard popup blocking** | Same test script | Keyboard tutorial popup blocked form submission | Added popup dismissal step with "Done" button tap |

### Test Script Improvements

**`fast-seller-add-product-test.sh`** was updated with:
1. **Step 2**: Navigate to Products tab (`tab-products`) before adding product
2. **Step 3**: Tap correct FAB (`product-management-fab-add` instead of `seller-dashboard-fab-add`)
3. **Step 11**: Dismiss keyboard tutorial popup
4. **Step 12**: Multiple submit button tap strategies (by ID and by text)
5. **Step 13**: Handle success dialog and press back
6. **Step 14**: Verify product appears in list

### Verification

All fixes verified with successful test run:
- Product creation: ✅ Working
- Success dialog: ✅ Displayed correctly
- "VIEW PRODUCT" button: ✅ Now loads product details (no more "Product Not Found")
- Tags display: ✅ Renders as chips (handmade, ceramic, pottery)

---

## Known Issues & Blockers

| Issue | Impact | Status | Resolution |
|-------|--------|--------|------------|
| Maestro 2.x slow `inputText` | High - 5 sec/char text input | ✅ Resolved | Use hybrid ADB approach for text input |
| Maestro 2.x syntax changes | Medium - Some YAML commands incompatible | ⚠️ Workaround | Use shell scripts with dynamic YAML generation |
| Minor i18n issue on reviews | Low - Shows `{count}` placeholder | ⚠️ Known | Translation interpolation needs fix |

---

## Contributing

### Adding New Test Cases

1. Create test file in appropriate directory under `tests/`
2. Follow naming convention: `<action>-<feature>.yaml`
3. Add appropriate tags (auth, smoke, seller, customer, etc.)
4. Update this document with new test case entry
5. Add to relevant test suite in `test-suites.yaml`

### Test Case Template

```yaml
appId: com.ceramicmarketplace.app
name: "Feature - Test Description"
tags:
  - feature-tag
  - priority-tag

---

# Launch app
- launchApp:
    clearState: true
    permissions:
      notifications: allow

# Test steps
- waitForAnimationToEnd
- assertVisible:
    id: "element-id"

# Verify result
- takeScreenshot: "test-result"
```

---

## References

- [Maestro Documentation](https://maestro.mobile.dev/)
- [Project Test Pyramid Guide](./TEST_PYRAMID_GUIDE.md)
- [Testing Quick Start](./TESTING_QUICK_START.md)
- [Backend API Documentation](./back_end/README.md)

---

**Maintained by:** Development Team
**Review Frequency:** Weekly
