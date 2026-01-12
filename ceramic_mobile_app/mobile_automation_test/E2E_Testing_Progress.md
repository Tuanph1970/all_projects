# E2E Testing Progress - Ceramic Marketplace Mobile App

**Testing Framework:** Maestro + ADB Hybrid (Character-by-Character Input)
**Last Updated:** January 12, 2026 (Phase B Seller Product Management Implemented)
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
| `run-all-seller-tests.sh` | Run all seller tests | All seller tests | ✅ |

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
| PROD-003 | Filter by Category | 📋 | - |
| PROD-004 | Filter by Price Range | 📋 | - |
| PROD-005 | Sort Products | 📋 | - |

### Shopping Cart (Customer)

| # | Test Case | Status | Script |
|---|-----------|--------|--------|
| CART-001 | Add Product to Cart | ✅ | `fast-customer-order-test.sh` |
| CART-002 | Update Cart Quantity | 📋 | - |
| CART-003 | Remove Item from Cart | 📋 | - |
| CART-004 | View Cart Summary | ✅ | `fast-customer-order-test.sh` |

### Checkout & Orders (Customer)

| # | Test Case | Status | Script |
|---|-----------|--------|--------|
| ORD-001 | Complete Checkout Flow | ✅ | `fast-customer-order-test.sh` |
| ORD-002 | Add Shipping Address | 📋 | - |
| ORD-005 | View Order History | 📋 | - |
| ORD-006 | View Order Details | 📋 | - |

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
| FUL-004 | Mark Order as Shipped | ✅ | `fast-seller-order-fulfillment-test.sh` |
| FUL-008 | Filter Orders by Status | ✅ | `fast-seller-order-fulfillment-test.sh` |
| FUL-003 | Reject Order | 📋 | - |
| FUL-005 | Add Tracking Information | 📋 | - |
| FUL-006 | Mark Order as Delivered | 📋 | - |

---

## Test Progress Summary

### By Implementation Status

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Implemented | 36 | 72% |
| 📋 Planned | 14 | 28% |
| **Total** | **50** | **100%** |

### By Feature Area

| Area | Implemented | Planned | Total |
|------|-------------|---------|-------|
| Authentication | 8 | 0 | 8 |
| Product Browsing | 3 | 3 | 6 |
| Shopping Cart | 2 | 2 | 4 |
| Checkout & Orders | 1 | 3 | 4 |
| Seller Dashboard | 3 | 0 | 3 |
| Product Management | 9 | 0 | 9 |
| Seller Analytics | 5 | 0 | 5 |
| Order Fulfillment | 4 | 3 | 7 |
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

## Recent Changes (January 12, 2026)

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

### Next Priority
- [ ] Product filtering (category, price, sort)
- [ ] Cart operations (update, remove)
- [ ] Order tracking
- [ ] Profile management

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

### Phase C: Customer Product Browsing (Extended)
> **Priority:** Medium | **Dependency:** Seller must have uploaded products

Customers need products in the system to browse/filter.

| Order | Test ID | Test Case | Role | Dependency |
|-------|---------|-----------|------|------------|
| C.1 | PROD-003 | Filter Products by Category | Customer | Products exist in system |
| C.2 | PROD-004 | Filter Products by Price Range | Customer | Products exist in system |
| C.3 | PROD-005 | Sort Products | Customer | Products exist in system |

---

### Phase D: Customer Cart Operations (Extended)
> **Priority:** Medium | **Dependency:** Customer must have items in cart

Cart operations require products to be added first.

| Order | Test ID | Test Case | Role | Dependency |
|-------|---------|-----------|------|------------|
| D.1 | CART-002 | Update Cart Quantity | Customer | CART-001 ✅ (Add to Cart) |
| D.2 | CART-003 | Remove Item from Cart | Customer | CART-001 ✅ (Add to Cart) |

---

### Phase E: Customer Order Management (Extended)
> **Priority:** Medium | **Dependency:** Customer must have placed orders

Order viewing requires completed orders.

| Order | Test ID | Test Case | Role | Dependency |
|-------|---------|-----------|------|------------|
| E.1 | ORD-002 | Add Shipping Address | Customer | Before checkout |
| E.2 | ORD-005 | View Order History | Customer | ORD-001 ✅ (Checkout complete) |
| E.3 | ORD-006 | View Order Details | Customer | ORD-001 ✅ (Checkout complete) |

---

### Phase F: Seller Order Fulfillment (Extended)
> **Priority:** Medium | **Dependency:** Customer must place order to seller

Seller can only process orders after customers place them.

| Order | Test ID | Test Case | Role | Dependency |
|-------|---------|-----------|------|------------|
| F.1 | FUL-003 | Reject Order | Seller | Customer places order → FUL-001 ✅ |
| F.2 | FUL-005 | Add Tracking Information | Seller | FUL-004 ✅ (Order shipped) |
| F.3 | FUL-006 | Mark Order as Delivered | Seller | FUL-004 ✅ (Order shipped) |

---

## Implementation Order Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED EXECUTION ORDER                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE A: Authentication (No Dependencies)                      │
│  ┌───────────────────────────────────────────────┐              │
│  │ A.1 → A.2 → A.3 → A.4 → A.5 → A.6            │              │
│  │ (Can run in parallel - no dependencies)       │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE B: Seller Product Setup                                  │
│  ┌───────────────────────────────────────────────┐              │
│  │ B.1 (Stock) → B.2 (Deactivate)               │              │
│  │ (Seller prepares inventory)                   │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE C: Customer Browsing                                     │
│  ┌───────────────────────────────────────────────┐              │
│  │ C.1 (Category) → C.2 (Price) → C.3 (Sort)    │              │
│  │ (Customer explores products)                  │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE D: Customer Cart                                         │
│  ┌───────────────────────────────────────────────┐              │
│  │ D.1 (Update Qty) → D.2 (Remove)              │              │
│  │ (Customer manages cart)                       │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE E: Customer Orders                                       │
│  ┌───────────────────────────────────────────────┐              │
│  │ E.1 (Address) → E.2 (History) → E.3 (Detail) │              │
│  │ (Customer completes & tracks orders)          │              │
│  └───────────────────────────────────────────────┘              │
│                           │                                     │
│                           ▼                                     │
│  PHASE F: Seller Fulfillment                                    │
│  ┌───────────────────────────────────────────────┐              │
│  │ F.1 (Reject) → F.2 (Tracking) → F.3 (Deliver)│              │
│  │ (Seller processes customer orders)            │              │
│  └───────────────────────────────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference: Remaining Tasks (11 Total)

| Phase | Count | Tests | Status |
|-------|-------|-------|--------|
| A - Authentication | 0 | ~~AUTH-003, 004, 005, 006, 007, 009~~ | ✅ COMPLETE |
| B - Seller Products | 0 | ~~SPM-007, 008~~ | ✅ COMPLETE |
| C - Customer Browsing | 3 | PROD-003, 004, 005 | 📋 Pending |
| D - Customer Cart | 2 | CART-002, 003 | 📋 Pending |
| E - Customer Orders | 3 | ORD-002, 005, 006 | 📋 Pending |
| F - Seller Fulfillment | 3 | FUL-003, 005, 006 | 📋 Pending |
| **Total Remaining** | **11** | | |

---

**Maintained by:** Development Team
**Review Frequency:** Weekly
