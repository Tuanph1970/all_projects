# E2E Testing Progress - Ceramic Marketplace Mobile App

**Testing Framework:** Maestro + ADB Hybrid (Character-by-Character Input)
**Last Updated:** January 13, 2026 (Phase F Seller Fulfillment Extended Tests Implemented)
**Status:** Active Development

---

## Overview

This document tracks the E2E test cases for the Ceramic Marketplace mobile application using Maestro testing framework with hybrid ADB input approach.

> **Note:** All legacy YAML tests have been removed due to Maestro 2.x compatibility issues. The project now uses shell-based test scripts with hybrid Maestro + ADB approach for reliable text input.

---

## Testing Architecture

### Hybrid Approach (Maestro + ADB)

Due to Maestro 2.x text input reliability issues, we use a **hybrid testing approach**:

- **Maestro**: App launching, element detection, tapping, scrolling, screenshots, assertions
- **ADB**: Character-by-character text input (30ms delay per character) for 100% reliability

### Directory Structure

```
maestro/
├── scripts/                    # Test scripts and libraries
│   ├── seller-login-lib.sh     # Reusable seller login library
│   ├── customer-login-lib.sh   # Reusable customer login library
│   ├── ensure-metro.sh         # Metro bundler utility
│   ├── fast-seller-*.sh        # Seller test scripts
│   ├── fast-customer-*.sh      # Customer test scripts
│   └── run-all-seller-tests.sh # Test suite runner
├── config/                     # Configuration files
└── flows/                      # Reusable flow fragments
```

---

## Test Status Legend

| Status | Symbol | Description |
|--------|--------|-------------|
| Implemented | ✅ | Test script exists and working |
| Planned | 📋 | Test case defined but not implemented |
| Not Applicable | ➖ | Removed or not needed |

---

## Implemented Test Scripts

### Seller Test Scripts

| Script | Description | Test Cases Covered | Status |
|--------|-------------|-------------------|--------|
| `fast-seller-login-test.sh` | Seller authentication | AUTH-002 | ✅ |
| `fast-seller-analytics-test.sh` | Analytics dashboard | ANA-001 to ANA-005 | ✅ |
| `fast-seller-product-management-test.sh` | Product list & management | SPM-003, SPM-004, SPM-005 | ✅ |
| `fast-seller-add-product-test.sh` | Add new product | SPM-001, SPM-002 | ✅ |
| `fast-seller-add-5-products-test.sh` | Bulk product creation | SPM-001 (bulk) | ✅ |
| `fast-seller-add-products-v2.sh` | Add products v2 | SPM-001 | ✅ |
| `fast-seller-edit-products-test.sh` | Edit existing products | SPM-006 | ✅ |
| `fast-seller-delete-product-test.sh` | Delete product | SPM-009 | ✅ |
| `fast-seller-update-stock-test.sh` | Update product stock | SPM-007 | ✅ |
| `fast-seller-deactivate-product-test.sh` | Deactivate product | SPM-008 | ✅ |
| `fast-seller-order-fulfillment-test.sh` | Order management | FUL-001, FUL-002, FUL-004, FUL-008 | ✅ |
| `fast-seller-reject-order-test.sh` | Reject pending order | FUL-003 | ✅ |
| `fast-seller-add-tracking-test.sh` | Add tracking information | FUL-005 | ✅ |
| `fast-seller-deliver-order-test.sh` | Mark order as delivered | FUL-006 | ✅ |
| `run-all-seller-tests.sh` | Run all seller tests | All seller tests | ✅ |
| `run-phase-f-tests.sh` | Run all Phase F tests | FUL-003, FUL-005, FUL-006 | ✅ |

### Authentication Edge Case Test Scripts

| Script | Description | Test Cases Covered | Status |
|--------|-------------|-------------------|--------|
| `fast-auth-invalid-password-test.sh` | Invalid password validation | AUTH-003 | ✅ |
| `fast-auth-nonexistent-user-test.sh` | Non-existent user validation | AUTH-004 | ✅ |
| `fast-auth-empty-fields-test.sh` | Empty fields validation | AUTH-005 | ✅ |
| `fast-auth-customer-registration-test.sh` | Customer registration | AUTH-006 | ✅ |
| `fast-auth-seller-registration-test.sh` | Seller registration | AUTH-007 | ✅ |
| `fast-auth-logout-test.sh` | Logout flow (customer & seller) | AUTH-009 | ✅ |
| `run-all-auth-tests.sh` | Run all auth tests | All auth tests | ✅ |

### Customer Test Scripts

| Script | Description | Test Cases Covered | Status |
|--------|-------------|-------------------|--------|
| `fast-customer-login-test.sh` | Customer authentication | AUTH-001 | ✅ |
| `fast-customer-order-test.sh` | Customer order flow | PROD-001, PROD-006, CART-001, ORD-001 | ✅ |
| `fast-complete-order-flow-test.sh` | Complete order lifecycle | Full E2E flow | ✅ |
| `fast-customer-filter-category-test.sh` | Filter products by category | PROD-003 | ✅ |
| `fast-customer-filter-price-test.sh` | Filter products by price range | PROD-004 | ✅ |
| `fast-customer-sort-products-test.sh` | Sort products | PROD-005 | ✅ |
| `setup-phase-c-test-data.sh` | Setup test data via API | Prerequisite data | ✅ |
| `run-phase-c-tests.sh` | Run all Phase C tests | PROD-003, 004, 005 | ✅ |
| `fast-customer-update-cart-quantity-test.sh` | Update cart item quantity | CART-002 | ✅ |
| `fast-customer-remove-cart-item-test.sh` | Remove item from cart | CART-003 | ✅ |
| `run-phase-d-tests.sh` | Run all Phase D cart tests | CART-002, CART-003 | ✅ |
| `fast-customer-checkout-address-test.sh` | Add shipping address during checkout | ORD-002 | ✅ |
| `fast-customer-order-history-test.sh` | View order history | ORD-005 | ✅ |
| `fast-customer-order-details-test.sh` | View order details | ORD-006 | ✅ |
| `run-phase-e-tests.sh` | Run all Phase E order tests | ORD-002, ORD-005, ORD-006 | ✅ |

### Reusable Libraries

| Library | Description | Functions Provided |
|---------|-------------|-------------------|
| `seller-login-lib.sh` | Seller login & navigation | `seller_login()`, `navigate_to_*()` |
| `customer-login-lib.sh` | Customer login & navigation | `customer_login()`, `navigate_to_*()` |
| `ensure-metro.sh` | Metro bundler management | Metro status check & wait |

---

## Test Case Mapping

### Authentication Tests

| # | Test Case | Role | Status | Script |
|---|-----------|------|--------|--------|
| AUTH-001 | Customer Login | Customer | ✅ | `fast-customer-login-test.sh` |
| AUTH-002 | Seller Login | Seller | ✅ | `fast-seller-login-test.sh` |
| AUTH-003 | Login with Invalid Password | All | ✅ | `fast-auth-invalid-password-test.sh` |
| AUTH-004 | Login with Non-existent User | All | ✅ | `fast-auth-nonexistent-user-test.sh` |
| AUTH-005 | Login with Empty Fields | All | ✅ | `fast-auth-empty-fields-test.sh` |
| AUTH-006 | Customer Registration | Customer | ✅ | `fast-auth-customer-registration-test.sh` |
| AUTH-007 | Seller Registration | Seller | ✅ | `fast-auth-seller-registration-test.sh` |
| AUTH-009 | Logout Flow | All | ✅ | `fast-auth-logout-test.sh` |

### Product Browsing (Customer)

| # | Test Case | Status | Script |
|---|-----------|--------|--------|
| PROD-001 | Browse Product Catalog | ✅ | `fast-customer-order-test.sh` |
| PROD-002 | Search Products by Keyword | ✅ | `fast-customer-order-test.sh` |
| PROD-006 | View Product Details | ✅ | `fast-customer-order-test.sh` |
| PROD-003 | Filter by Category | ✅ | `fast-customer-filter-category-test.sh` |
| PROD-004 | Filter by Price Range | ✅ | `fast-customer-filter-price-test.sh` |
| PROD-005 | Sort Products | ✅ | `fast-customer-sort-products-test.sh` |

### Shopping Cart (Customer)

| # | Test Case | Status | Script |
|---|-----------|--------|--------|
| CART-001 | Add Product to Cart | ✅ | `fast-customer-order-test.sh` |
| CART-002 | Update Cart Quantity | ✅ | `fast-customer-update-cart-quantity-test.sh` |
| CART-003 | Remove Item from Cart | ✅ | `fast-customer-remove-cart-item-test.sh` |
| CART-004 | View Cart Summary | ✅ | `fast-customer-order-test.sh` |

### Checkout & Orders (Customer)

| # | Test Case | Status | Script |
|---|-----------|--------|--------|
| ORD-001 | Complete Checkout Flow | ✅ | `fast-customer-order-test.sh` |
| ORD-002 | Add Shipping Address | ✅ | `fast-customer-checkout-address-test.sh` |
| ORD-005 | View Order History | ✅ | `fast-customer-order-history-test.sh` |
| ORD-006 | View Order Details | ✅ | `fast-customer-order-details-test.sh` |

### Seller Dashboard

| # | Test Case | Status | Script |
|---|-----------|--------|--------|
| DASH-001 | View Dashboard Overview | ✅ | `fast-seller-login-test.sh` |
| DASH-002 | View Sales Statistics | ✅ | `fast-seller-analytics-test.sh` |
| DASH-005 | View Sales Chart | ✅ | `fast-seller-analytics-test.sh` |

### Product Management (Seller)

| # | Test Case | Status | Script |
|---|-----------|--------|--------|
| SPM-001 | Add New Product | ✅ | `fast-seller-add-product-test.sh` |
| SPM-002 | Add Product with Images | ✅ | `fast-seller-add-product-test.sh` |
| SPM-003 | View Product List | ✅ | `fast-seller-product-management-test.sh` |
| SPM-004 | Search My Products | ✅ | `fast-seller-product-management-test.sh` |
| SPM-005 | Filter Products by Status | ✅ | `fast-seller-product-management-test.sh` |
| SPM-006 | Edit Product Details | ✅ | `fast-seller-edit-products-test.sh` |
| SPM-007 | Update Product Stock | ✅ | `fast-seller-update-stock-test.sh` |
| SPM-008 | Deactivate Product | ✅ | `fast-seller-deactivate-product-test.sh` |
| SPM-009 | Delete Product | ✅ | `fast-seller-delete-product-test.sh` |

### Seller Analytics

| # | Test Case | Status | Script |
|---|-----------|--------|--------|
| ANA-001 | View Sales Analytics | ✅ | `fast-seller-analytics-test.sh` |
| ANA-002 | View Revenue Trends | ✅ | `fast-seller-analytics-test.sh` |
| ANA-003 | View Inventory Status | ✅ | `fast-seller-analytics-test.sh` |
| ANA-004 | View Top Products | ✅ | `fast-seller-analytics-test.sh` |
| ANA-005 | Select Analytics Period | ✅ | `fast-seller-analytics-test.sh` |

### Order Fulfillment (Seller)

| # | Test Case | Status | Script |
|---|-----------|--------|--------|
| FUL-001 | View Incoming Orders | ✅ | `fast-seller-order-fulfillment-test.sh` |
| FUL-002 | Accept Order | ✅ | `fast-seller-order-fulfillment-test.sh` |
| FUL-003 | Reject Order | ✅ | `fast-seller-reject-order-test.sh` |
| FUL-004 | Mark Order as Shipped | ✅ | `fast-seller-order-fulfillment-test.sh` |
| FUL-005 | Add Tracking Information | ✅ | `fast-seller-add-tracking-test.sh` |
| FUL-006 | Mark Order as Delivered | ✅ | `fast-seller-deliver-order-test.sh` |
| FUL-008 | Filter Orders by Status | ✅ | `fast-seller-order-fulfillment-test.sh` |

---

## Test Progress Summary

### By Implementation Status

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Implemented | 45 | 90% |
| 📋 Planned | 5 | 10% |
| **Total** | **50** | **100%** |

### By Feature Area

| Area | Implemented | Planned | Total |
|------|-------------|---------|-------|
| Authentication | 8 | 0 | 8 |
| Product Browsing | 6 | 0 | 6 |
| Shopping Cart | 4 | 0 | 4 |
| Checkout & Orders | 4 | 0 | 4 |
| Seller Dashboard | 3 | 0 | 3 |
| Product Management | 9 | 0 | 9 |
| Seller Analytics | 5 | 0 | 5 |
| Order Fulfillment | 7 | 0 | 7 |
| Complete Flows | 1 | 0 | 1 |

---

## Running Tests

### Prerequisites

1. Android emulator running
2. Metro bundler running (`npx expo start`)
3. Backend server running (port 8002)
4. Maestro installed (`~/.maestro/bin`)
5. Java 17+ installed

### Run Individual Tests

```bash
cd mobile_automation_test/maestro/scripts

# Seller tests
./fast-seller-login-test.sh
./fast-seller-analytics-test.sh
./fast-seller-product-management-test.sh
./fast-seller-add-product-test.sh
./fast-seller-edit-products-test.sh
./fast-seller-delete-product-test.sh
./fast-seller-update-stock-test.sh
./fast-seller-deactivate-product-test.sh
./fast-seller-order-fulfillment-test.sh

# Customer tests
./fast-customer-login-test.sh
./fast-customer-order-test.sh
./fast-complete-order-flow-test.sh

# Phase C - Customer Product Browsing tests
./fast-customer-filter-category-test.sh   # PROD-003
./fast-customer-filter-price-test.sh      # PROD-004
./fast-customer-sort-products-test.sh     # PROD-005
```

### Run All Seller Tests

```bash
cd mobile_automation_test/maestro/scripts
./run-all-seller-tests.sh
```

### Run All Authentication Tests

```bash
cd mobile_automation_test/maestro/scripts
./run-all-auth-tests.sh           # Run all auth tests
./run-all-auth-tests.sh --quick   # Run only edge case tests (003-005)
```

### Run All Phase C Tests (Customer Product Browsing)

```bash
cd mobile_automation_test/maestro/scripts
./setup-phase-c-test-data.sh      # Setup test data (run once for fresh DB)
./run-phase-c-tests.sh            # Run all Phase C tests
./run-phase-c-tests.sh --setup    # Run setup + all tests
./run-phase-c-tests.sh --quick    # Run only PROD-003 (quick test)
```

### Run Individual Authentication Tests

```bash
cd mobile_automation_test/maestro/scripts

# Edge case tests
./fast-auth-invalid-password-test.sh    # AUTH-003
./fast-auth-nonexistent-user-test.sh    # AUTH-004
./fast-auth-empty-fields-test.sh        # AUTH-005

# Registration tests
./fast-auth-customer-registration-test.sh  # AUTH-006
./fast-auth-seller-registration-test.sh    # AUTH-007

# Logout test
./fast-auth-logout-test.sh              # AUTH-009
```

---

## Test Credentials

### Seller Account
- **Username:** `test_seller_user`
- **Password:** `Testseller@123456`

### Customer Account
- **Username:** `test_customer_user`
- **Password:** `@Test_customer@1234`

---

## Recent Changes (January 13, 2026)

### Phase E Customer Order Tests Implemented ✅

All Phase E customer order management tests have been implemented:

| Test ID | Script | Description |
|---------|--------|-------------|
| ORD-002 | `fast-customer-checkout-address-test.sh` | Tests adding shipping address during checkout |
| ORD-005 | `fast-customer-order-history-test.sh` | Tests viewing order history from Profile |
| ORD-006 | `fast-customer-order-details-test.sh` | Tests viewing specific order details |

**New Scripts Added:**
- `fast-customer-checkout-address-test.sh` - ORD-002 shipping address test
- `fast-customer-order-history-test.sh` - ORD-005 order history test
- `fast-customer-order-details-test.sh` - ORD-006 order details test
- `run-phase-e-tests.sh` - Runs all Phase E tests with summary

**Frontend Components Created:**
- `customerOrderService.js` - Customer order API service for fetching orders
- `OrderHistoryScreen.jsx` - Order history list with testIDs (order-history-screen, order-history-card-{index}, etc.)
- `CustomerOrderDetailsScreen.jsx` - Order details view with testIDs (customer-order-details-screen, order-details-status, etc.)

**Frontend Updates:**
- `MainNavigator.jsx` - Added OrderHistory and CustomerOrderDetails screens
- `ProfileScreen.jsx` - Updated handleOrderHistory to navigate, added testID
- `en.js` / `vi.js` - Added orderHistory and orderDetails translations

---

## Previous Changes (January 12, 2026)

### Bug Fixes Applied During Phase C Testing ✅

During Phase C test verification, several frontend bugs were discovered and fixed:

| Issue | File | Fix Applied |
|-------|------|-------------|
| Render Error: Objects not valid as React child | `productSlice.js` | Added `extractErrorMessage()` helper to convert Pydantic validation errors to strings |
| Error display crash on HomeScreen | `HomeScreen.jsx` | Added safeguard to handle object errors: `typeof error === 'string' ? error : (error.msg \|\| JSON.stringify(error))` |
| Products not displaying (API response format) | `productService.js` | Fixed response wrapping - API returns array but Redux expected `{products, page, totalPages, hasMore}` format |
| Price display crash | `ProductListScreen.jsx` | Added `formatPrice()` helper to handle string prices from API |
| Featured products empty | `setup-phase-c-test-data.sh` | Added step to mark products as featured via API |
| Categories not existing | `setup-phase-c-test-data.sh` | Added category creation via API before products |

**All Phase C tests now pass after these fixes.**

---

### Phase C Customer Product Browsing Tests Implemented ✅

All Phase C customer product browsing tests have been implemented:

| Test ID | Script | Description |
|---------|--------|-------------|
| PROD-003 | `fast-customer-filter-category-test.sh` | Tests filtering products by category |
| PROD-004 | `fast-customer-filter-price-test.sh` | Tests filtering/sorting products by price |
| PROD-005 | `fast-customer-sort-products-test.sh` | Tests all sort options (newest, popular, price, rating) |

**New Scripts Added:**
- `setup-phase-c-test-data.sh` - Creates test users and 9 products via API
- `run-phase-c-tests.sh` - Runs all Phase C tests with summary

**Frontend Enhancements:**
- Added testID attributes to ProductListScreen.jsx for Maestro automation
- Added ProductListScreen to navigation stack
- Added "Browse All Products" button to HomeScreen
- Updated HomeScreen with navigation to ProductListScreen

**Note:** PROD-004 uses price sorting as the dedicated price filter UI (FAB) is not yet implemented. See **Frontend UI TODO** section for implementation details. Full price range filter test will be updated when the Filter FAB is enabled.

---

### Phase B Seller Product Management Tests Implemented ✅

All Phase B seller product management tests have been implemented:

| Test ID | Script | Description |
|---------|--------|-------------|
| SPM-007 | `fast-seller-update-stock-test.sh` | Tests updating product stock/inventory |
| SPM-008 | `fast-seller-deactivate-product-test.sh` | Tests deactivating/disabling a product |

**Bug Fixes:**
- Fixed `ensure-metro.sh` - Corrected FRONT_END_DIR path
- Fixed `fast-auth-empty-fields-test.sh` - Fixed bash arithmetic with `set -e`

---

## Previous Changes (January 10, 2026)

### Phase A Authentication Tests Implemented ✅

All Phase A authentication edge case tests have been implemented:

| Test ID | Script | Description |
|---------|--------|-------------|
| AUTH-003 | `fast-auth-invalid-password-test.sh` | Tests login rejection with wrong password |
| AUTH-004 | `fast-auth-nonexistent-user-test.sh` | Tests login rejection for non-existent users |
| AUTH-005 | `fast-auth-empty-fields-test.sh` | Tests validation for empty form fields |
| AUTH-006 | `fast-auth-customer-registration-test.sh` | Tests customer account registration flow |
| AUTH-007 | `fast-auth-seller-registration-test.sh` | Tests seller account registration flow |
| AUTH-009 | `fast-auth-logout-test.sh` | Tests logout for both customer and seller |

**Test Runner Added:**
- `run-all-auth-tests.sh` - Runs all authentication tests with summary
- Supports `--quick` flag for running only edge case tests

### Previous Cleanup
- Removed all broken YAML tests in `tests/` directory
- Removed `test-suites.yaml` (referenced deleted tests)
- Removed redundant runner scripts:
  - `scripts/maestro-quick-test.sh`
  - `scripts/run-test-suite.sh`
  - `scripts/run-maestro-tests.sh`

### Input Method Fix
- Fixed text input reliability issue
- Changed from clipboard-based to character-by-character ADB input
- 30ms delay per character ensures 100% reliable text entry
- Updated both `seller-login-lib.sh` and `customer-login-lib.sh`

---

## Roadmap

### Completed
- [x] Seller authentication
- [x] Customer authentication
- [x] Seller dashboard & analytics
- [x] Product management (CRUD)
- [x] Order fulfillment
- [x] Customer order flow
- [x] Complete E2E order lifecycle
- [x] **Authentication edge cases (Phase A complete!)**
  - [x] Invalid password validation (AUTH-003)
  - [x] Non-existent user validation (AUTH-004)
  - [x] Empty fields validation (AUTH-005)
  - [x] Customer registration (AUTH-006)
  - [x] Seller registration (AUTH-007)
  - [x] Logout flow (AUTH-009)
- [x] **Seller Product Management Extended (Phase B complete!)**
  - [x] Update Product Stock (SPM-007)
  - [x] Deactivate Product (SPM-008)
- [x] **Customer Product Browsing Extended (Phase C complete!)**
  - [x] Filter Products by Category (PROD-003)
  - [x] Filter Products by Price Range (PROD-004)
  - [x] Sort Products (PROD-005)
- [x] **Customer Cart Operations (Phase D complete!)**
  - [x] Update Cart Quantity (CART-002)
  - [x] Remove Item from Cart (CART-003)
- [x] **Customer Order Management (Phase E complete!)**
  - [x] Add Shipping Address (ORD-002)
  - [x] View Order History (ORD-005)
  - [x] View Order Details (ORD-006)

### Next Priority
- [x] Seller order fulfillment extended (FUL-003, FUL-005, FUL-006) ✅ COMPLETE
- [ ] Profile management

### Frontend UI TODO
- [ ] **Price Filter UI (Filter FAB)** - Implement price range filter modal in ProductListScreen
  - Currently commented out in `ProductListScreen.jsx` (lines 449-455)
  - Should include min/max price inputs
  - Update PROD-004 test once implemented to use actual price filter UI

### Future
- [ ] Chat functionality
- [ ] Reviews and ratings
- [ ] Dual role features
- [ ] Error handling scenarios

---

## References

- [Maestro Documentation](https://maestro.mobile.dev/)
- [ADB Input Commands](https://developer.android.com/studio/command-line/adb)

---

## Remaining Tasks - Ordered by Dependencies

The following tasks are ordered based on logical dependencies between user roles and features.

### Phase A: Authentication Foundation ✅ COMPLETED
> **Priority:** High | **Status:** All tests implemented!

These tests validate authentication edge cases and don't depend on other features.

| Order | Test ID | Test Case | Role | Status | Script |
|-------|---------|-----------|------|--------|--------|
| A.1 | AUTH-003 | Login with Invalid Password | All | ✅ | `fast-auth-invalid-password-test.sh` |
| A.2 | AUTH-004 | Login with Non-existent User | All | ✅ | `fast-auth-nonexistent-user-test.sh` |
| A.3 | AUTH-005 | Login with Empty Fields | All | ✅ | `fast-auth-empty-fields-test.sh` |
| A.4 | AUTH-006 | Customer Registration | Customer | ✅ | `fast-auth-customer-registration-test.sh` |
| A.5 | AUTH-007 | Seller Registration | Seller | ✅ | `fast-auth-seller-registration-test.sh` |
| A.6 | AUTH-009 | Logout Flow | All | ✅ | `fast-auth-logout-test.sh` |

---

### Phase B: Seller Product Management (Extended) ✅ COMPLETED
> **Priority:** High | **Status:** All tests implemented!

Seller must prepare products before customers can browse/purchase.

| Order | Test ID | Test Case | Role | Status | Script |
|-------|---------|-----------|------|--------|--------|
| B.1 | SPM-007 | Update Product Stock | Seller | ✅ | `fast-seller-update-stock-test.sh` |
| B.2 | SPM-008 | Deactivate Product | Seller | ✅ | `fast-seller-deactivate-product-test.sh` |

---

### Phase C: Customer Product Browsing (Extended) ✅ COMPLETED
> **Priority:** Medium | **Status:** All tests implemented!

Customers need products in the system to browse/filter.

| Order | Test ID | Test Case | Role | Status | Script |
|-------|---------|-----------|------|--------|--------|
| C.1 | PROD-003 | Filter Products by Category | Customer | ✅ | `fast-customer-filter-category-test.sh` |
| C.2 | PROD-004 | Filter Products by Price Range | Customer | ✅ | `fast-customer-filter-price-test.sh` |
| C.3 | PROD-005 | Sort Products | Customer | ✅ | `fast-customer-sort-products-test.sh` |

---

### Phase D: Customer Cart Operations (Extended) ✅ COMPLETE
> **Priority:** Medium | **Dependency:** Customer must have items in cart
> **Status:** ✅ COMPLETED on January 13, 2026

Cart operations require products to be added first.

| Order | Test ID | Test Case | Role | Status | Script |
|-------|---------|-----------|------|--------|--------|
| D.1 | CART-002 | Update Cart Quantity | Customer | ✅ | `fast-customer-update-cart-quantity-test.sh` |
| D.2 | CART-003 | Remove Item from Cart | Customer | ✅ | `fast-customer-remove-cart-item-test.sh` |

**Test Runner:** `run-phase-d-tests.sh`

**Bug Fixes Applied:**
- Fixed CartScreen.jsx `cart.items` undefined check
- Fixed cart API trailing slash to avoid 307 redirect losing auth header
- Fixed price parsing with `parseFloat()` for string values from API

---

### Phase E: Customer Order Management (Extended) ✅ COMPLETE
> **Priority:** Medium | **Dependency:** Customer must have placed orders
> **Status:** ✅ COMPLETED on January 13, 2026

Order viewing requires completed orders.

| Order | Test ID | Test Case | Role | Status | Script |
|-------|---------|-----------|------|--------|--------|
| E.1 | ORD-002 | Add Shipping Address | Customer | ✅ | `fast-customer-checkout-address-test.sh` |
| E.2 | ORD-005 | View Order History | Customer | ✅ | `fast-customer-order-history-test.sh` |
| E.3 | ORD-006 | View Order Details | Customer | ✅ | `fast-customer-order-details-test.sh` |

**Test Runner:** `run-phase-e-tests.sh`

**Frontend Components Created:**
- `customerOrderService.js` - Customer order API service
- `OrderHistoryScreen.jsx` - Order history list screen with testIDs
- `CustomerOrderDetailsScreen.jsx` - Order details view with testIDs
- Updated `MainNavigator.jsx` - Added new screens to navigation
- Updated `ProfileScreen.jsx` - Added navigation to Order History
- Added translations in `en.js` and `vi.js` for orderHistory and orderDetails

**Bug Fixes Applied During Phase E Testing:**
- `CheckoutScreen.jsx` - Added `formatPrice()` helper to safely handle price values that may be strings, numbers, or undefined
- `CheckoutScreen.jsx` - Added optional chaining (`cart.summary?.`) for safer property access to prevent crashes
- `CheckoutScreen.jsx` - Fixed shipping amount check to handle string "0" and "0.00" values
- `CheckoutScreen.jsx` - Updated success alert navigation from `OrderDetails` to `OrderHistory`

**All Phase E tests now pass after these fixes.**

---

### Phase F: Seller Order Fulfillment (Extended) ✅ COMPLETE
> **Priority:** Medium | **Dependency:** Customer must place order to seller
> **Status:** ✅ COMPLETED on January 13, 2026

Seller can only process orders after customers place them.

| Order | Test ID | Test Case | Role | Status | Script |
|-------|---------|-----------|------|--------|--------|
| F.1 | FUL-003 | Reject Order | Seller | ✅ | `fast-seller-reject-order-test.sh` |
| F.2 | FUL-005 | Add Tracking Information | Seller | ✅ | `fast-seller-add-tracking-test.sh` |
| F.3 | FUL-006 | Mark Order as Delivered | Seller | ✅ | `fast-seller-deliver-order-test.sh` |

**Test Runner:** `run-phase-f-tests.sh`

**Frontend Updates:**
- `OrderDetailsScreen.jsx` - Added testIDs, reject modal, tracking modal, and deliver button

---

## Implementation Order Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED EXECUTION ORDER                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE A: Authentication (No Dependencies) ✅ COMPLETE          │
│  ┌───────────────────────────────────────────────┐              │
│  │ A.1 → A.2 → A.3 → A.4 → A.5 → A.6            │              │
│  │ (Can run in parallel - no dependencies)       │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE B: Seller Product Setup ✅ COMPLETE                      │
│  ┌───────────────────────────────────────────────┐              │
│  │ B.1 (Stock) → B.2 (Deactivate)               │              │
│  │ (Seller prepares inventory)                   │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE C: Customer Browsing ✅ COMPLETE                         │
│  ┌───────────────────────────────────────────────┐              │
│  │ C.1 (Category) → C.2 (Price) → C.3 (Sort)    │              │
│  │ (Customer explores products)                  │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE D: Customer Cart ✅ COMPLETE                              │
│  ┌───────────────────────────────────────────────┐              │
│  │ D.1 (Update Qty) → D.2 (Remove)              │              │
│  │ (Customer manages cart)                       │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE E: Customer Orders ✅ COMPLETE                            │
│  ┌───────────────────────────────────────────────┐              │
│  │ E.1 (Address) → E.2 (History) → E.3 (Detail) │              │
│  │ (Customer completes & tracks orders)          │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE F: Seller Fulfillment ✅ COMPLETE                         │
│  ┌───────────────────────────────────────────────┐              │
│  │ F.1 (Reject) → F.2 (Tracking) → F.3 (Deliver)│              │
│  │ (Seller processes customer orders)            │              │
│  └───────────────────────────────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference: All Phases Complete!

| Phase | Count | Tests | Status |
|-------|-------|-------|--------|
| A - Authentication | 0 | ~~AUTH-003, 004, 005, 006, 007, 009~~ | ✅ COMPLETE |
| B - Seller Products | 0 | ~~SPM-007, 008~~ | ✅ COMPLETE |
| C - Customer Browsing | 0 | ~~PROD-003, 004, 005~~ | ✅ COMPLETE |
| D - Customer Cart | 0 | ~~CART-002, 003~~ | ✅ COMPLETE |
| E - Customer Orders | 0 | ~~ORD-002, 005, 006~~ | ✅ COMPLETE |
| F - Seller Fulfillment | 0 | ~~FUL-003, 005, 006~~ | ✅ COMPLETE |
| **Total Remaining** | **0** | | **ALL PHASES COMPLETE!** |

---

**Maintained by:** Development Team
**Review Frequency:** Weekly
