# API Mismatch Analysis: Frontend vs Backend

**Generated:** 2026-01-13
**Purpose:** Document unmatched API endpoints between frontend calls and backend implementations

---

## Summary

| Category | Frontend Only | Backend Only | Total Mismatches |
|----------|---------------|--------------|------------------|
| Products | 12 | 15 | 27 |
| Orders | 3 | 5 | 8 |
| Seller Analytics | 1 | 0 | 1 |
| Chat | 0 | 3 | 3 |
| Reviews | 0 | 3 | 3 |
| Users | 0 | 2 | 2 |
| **Total** | **16** | **28** | **44** |

---

## SECTION A: Frontend API Calls NOT Implemented in Backend

These are API calls made by the frontend that have no corresponding backend implementation.

### A.1 Product Service (`productService.js`)

| # | Function | Frontend Endpoint | HTTP Method | Priority | Notes |
|---|----------|-------------------|-------------|----------|-------|
| 1 | `getProductBySlug()` | `/api/v1/products/slug/{slug}` | GET | Medium | Backend only supports `/{product_id}`, not slug-based lookup |
| 2 | `getCategoryById()` | `/api/v1/products/categories/{id}` | GET | Low | Backend has `/categories` list but no single category GET |
| 3 | `getNewProducts()` | `/api/v1/products/new?limit={n}` | GET | Medium | No endpoint for new products sorted by creation date |
| 4 | `getDiscountedProducts()` | `/api/v1/products/discounted?limit={n}` | GET | Medium | No endpoint for products on sale/discount |
| 5 | `getProductVariants()` | `/api/v1/products/{productId}/variants` | GET | High | Product variant system not implemented in backend |
| 6 | `checkAvailability()` | `/api/v1/products/{productId}/availability` | GET | Medium | Real-time availability check not implemented |
| 7 | `getPriceHistory()` | `/api/v1/products/{productId}/price-history?days={n}` | GET | Low | Price tracking not implemented |
| 8 | `getProductSpecifications()` | `/api/v1/products/{productId}/specifications` | GET | Medium | Dedicated specifications endpoint missing |
| 9 | `compareProducts()` | `/api/v1/products/compare?ids={ids}` | GET | Low | Product comparison feature not implemented |
| 10 | `getBrands()` | `/brands` | GET | Medium | Brands system not implemented (also missing `/api/v1` prefix) |
| 11 | `getProductTags()` | `/api/v1/products/{productId}/tags` | GET | Low | Product tagging system not implemented |
| 12 | `getProductAttributes()` | `/api/v1/products/{productId}/attributes` | GET | Medium | Product attributes endpoint missing |

**Implementation Notes:**
- Items marked as TODO in frontend code
- `getProductVariants()` is HIGH priority - commonly needed for e-commerce
- `getBrands()` has incorrect URL (missing `/api/v1` prefix)

---

### A.2 Order Service (`customerOrderService.js`)

| # | Function | Frontend Endpoint | HTTP Method | Priority | Notes |
|---|----------|-------------------|-------------|----------|-------|
| 1 | `cancelOrder()` | `/api/v1/orders/{orderId}/cancel` | POST | **High** | Frontend expects POST to `/cancel`, backend uses PUT to `/{order_id}` with status change |

**Implementation Notes:**
- Backend requires using `PUT /api/v1/orders/{order_id}` with `status: "cancelled"` in body
- Frontend expects dedicated `/cancel` endpoint for clearer API semantics

---

### A.3 Order Fulfillment Service (`orderFulfillmentService.js`)

| # | Function | Frontend Endpoint | HTTP Method | Priority | Notes |
|---|----------|-------------------|-------------|----------|-------|
| 1 | `updateOrderStatus()` | `PUT /api/v1/orders/{orderId}` | PUT | **Mismatch** | Frontend uses PUT to `/orders/{id}`, backend order-fulfillment uses PATCH to `/orders/{id}/status` |
| 2 | `shipOrder()` | `PUT /api/v1/orders/{orderId}` | PUT | **Mismatch** | Frontend uses PUT, backend has dedicated `POST /orders/{id}/ship` |

**Critical Issue:**
- Frontend `orderFulfillmentService.js` calls wrong endpoints
- Backend has dedicated order-fulfillment router at `/api/v1/order-fulfillment/`
- Frontend calls `/api/v1/orders/` instead

**Fix Required:**
```javascript
// Current (WRONG):
PUT /api/v1/orders/{orderId}

// Should be:
PATCH /api/v1/order-fulfillment/orders/{orderId}/status
POST /api/v1/order-fulfillment/orders/{orderId}/ship
```

---

### A.4 Seller Analytics Service (`sellerAnalyticsService.js`)

| # | Function | Frontend Endpoint | HTTP Method | Priority | Notes |
|---|----------|-------------------|-------------|----------|-------|
| 1 | `scheduleReport()` | `/api/v1/seller/analytics/analytics/schedule-report` | POST | Low | Report scheduling not implemented in backend |

**Implementation Notes:**
- Backend analytics routes don't include scheduled reporting feature
- Would require background job system (Celery/APScheduler)

---

## SECTION B: Backend Endpoints NOT Called by Frontend

These are implemented backend endpoints with no corresponding frontend integration.

### B.1 Products Router (`/api/v1/products`)

| # | Route | HTTP Method | Handler | Priority | Notes |
|---|-------|-------------|---------|----------|-------|
| 1 | `/trending` | GET | `get_trending_products()` | Medium | Trending products based on views/sales |
| 2 | `/categories/{category_id}/products` | GET | `get_products_by_category()` | Low | Alternative to query param approach |
| 3 | `/search/advanced` | GET | `advanced_search()` | Medium | Advanced search with complex filters |
| 4 | `/home/featured` | GET | `get_home_featured_products()` | Low | Duplicate of `/featured`? |
| 5 | `/stats/catalog` | GET | `get_catalog_stats()` | Low | Catalog statistics |
| 6 | `/search/suggestions` | GET | `get_search_suggestions()` | **High** | Autocomplete/suggestions for search |
| 7 | `/filters/options` | GET | `get_filter_options()` | **High** | Available filter options for UI |
| 8 | `/{product_id}/view` | POST | `track_product_view()` | Medium | View tracking for analytics |
| 9 | `/{product_id}/similar` | GET | `get_similar_products()` | Medium | Similar products (vs related) |
| 10 | `/{product_id}/images` | POST | `add_product_image()` | Medium | Add images to product |
| 11 | `/{product_id}/images/{image_id}/primary` | PUT | `set_primary_image()` | Medium | Set primary product image |
| 12 | `/{product_id}/images/reorder` | PUT | `reorder_product_images()` | Low | Reorder product images |
| 13 | `/catalog/paginated` | GET | `get_paginated_products()` | Low | Alternative pagination endpoint |
| 14 | `/categories/{category_id}/showcase` | GET | `get_category_showcase()` | Low | Category showcase feature |
| 15 | `/analytics/trending` | GET | `get_trending_analytics()` | Low | Trending analytics data |

**Implementation Notes:**
- `/search/suggestions` and `/filters/options` would significantly improve UX
- `/{product_id}/view` needed for proper analytics tracking
- Image management endpoints not utilized in frontend

---

### B.2 Orders Router (`/api/v1/orders`)

| # | Route | HTTP Method | Handler | Priority | Notes |
|---|-------|-------------|---------|----------|-------|
| 1 | `/` | POST | `create_order()` | Low | Frontend uses `/checkout` instead |

**Note:** This is a minor difference - both approaches work, but having both might cause confusion.

---

### B.3 Order Fulfillment Router (`/api/v1/order-fulfillment`)

| # | Route | HTTP Method | Handler | Priority | Notes |
|---|-------|-------------|---------|----------|-------|
| 1 | `/orders` | GET | `get_seller_orders()` | **Critical** | Frontend calls wrong base path |
| 2 | `/orders/{order_id}` | GET | `get_order_details()` | **Critical** | Frontend calls wrong base path |
| 3 | `/orders/{order_id}/status` | PATCH | `update_order_status()` | **Critical** | Frontend uses PUT to wrong endpoint |
| 4 | `/orders/bulk/update-status` | POST | `bulk_update_order_status()` | Medium | Bulk operations not utilized |
| 5 | `/orders/analytics/fulfillment` | GET | `get_fulfillment_analytics()` | Medium | Analytics endpoint exists but may not be called correctly |

**Critical Issue:**
- Frontend `orderFulfillmentService.js` uses base path `/api/v1/orders/`
- Backend defines these endpoints under `/api/v1/order-fulfillment/`
- This is a **major routing mismatch**

---

### B.4 Chat Router (`/api/v1/chat`)

| # | Route | HTTP Method | Handler | Priority | Notes |
|---|-------|-------------|---------|----------|-------|
| 1 | `/rooms/{chat_room_id}/messages` | POST | `send_message()` | Low | Frontend uses WebSocket for sending |
| 2 | `/online-users` | GET | `get_online_users()` | Medium | Online status feature not used in UI |
| 3 | `/rooms/{chat_room_id}/typing` | GET | `get_typing_users()` | Low | Frontend handles typing via WebSocket |

**Implementation Notes:**
- Backend supports both REST and WebSocket for messaging
- Frontend only uses WebSocket for real-time features
- `/online-users` could enhance chat UI

---

### B.5 Reviews Router (`/api/v1/reviews`)

| # | Route | HTTP Method | Handler | Priority | Notes |
|---|-------|-------------|---------|----------|-------|
| 1 | `/` | POST | `create_review()` | **High** | Review creation not implemented in frontend |
| 2 | `/{review_id}` | PUT | `update_review()` | Medium | Review editing not implemented |
| 3 | `/{review_id}/helpful` | POST | `mark_review_helpful()` | Medium | "Helpful" voting not implemented |

**Implementation Notes:**
- Frontend can read reviews but cannot create/modify them
- Review system is incomplete on frontend side

---

### B.6 Users Router (`/api/v1/users`)

| # | Route | HTTP Method | Handler | Priority | Notes |
|---|-------|-------------|---------|----------|-------|
| 1 | `/` | GET | `read_users()` | Low | Admin feature - list all users |
| 2 | `/{user_id}` | GET | `read_user()` | Low | View other user profiles |

**Implementation Notes:**
- These are likely admin-only endpoints
- May be used for seller viewing customer profiles in future

---

## SECTION C: API Path Mismatches (Same Feature, Different Paths)

These are cases where frontend and backend implement the same feature but use different URL paths.

### C.1 Order Fulfillment Base Path

| Feature | Frontend Path | Backend Path | Impact |
|---------|---------------|--------------|--------|
| Get seller orders | `/api/v1/orders/` | `/api/v1/order-fulfillment/orders` | **BROKEN** |
| Get order details | `/api/v1/orders/{id}` | `/api/v1/order-fulfillment/orders/{id}` | **BROKEN** |
| Update order status | `PUT /api/v1/orders/{id}` | `PATCH /api/v1/order-fulfillment/orders/{id}/status` | **BROKEN** |
| Ship order | `PUT /api/v1/orders/{id}` | `POST /api/v1/order-fulfillment/orders/{id}/ship` | **BROKEN** |
| Get order stats | `/api/v1/orders/stats/overview` | `/api/v1/order-fulfillment/orders/stats/overview` | **BROKEN** |
| Process return | `/api/v1/orders/{id}/return` | `/api/v1/order-fulfillment/orders/{id}/return` | **BROKEN** |
| Process refund | `/api/v1/orders/{id}/refund` | `/api/v1/order-fulfillment/orders/{id}/refund` | **BROKEN** |
| Get pending returns | `/api/v1/orders/returns/pending` | `/api/v1/order-fulfillment/orders/returns/pending` | **BROKEN** |
| Fulfillment analytics | `/api/v1/orders/analytics/fulfillment` | `/api/v1/order-fulfillment/orders/analytics/fulfillment` | **BROKEN** |

**Root Cause:** Frontend `orderFulfillmentService.js` uses wrong base URL.

**Fix Required in `orderFulfillmentService.js`:**
```javascript
// Change from:
const BASE_URL = '/api/v1/orders';

// To:
const BASE_URL = '/api/v1/order-fulfillment/orders';
```

---

### C.2 Seller Services Base Path

| Feature | Frontend Path | Backend Path | Match |
|---------|---------------|--------------|-------|
| Dashboard overview | `/api/v1/seller/dashboard/overview` | `/api/v1/seller-dashboard/dashboard/overview` | **MISMATCH** |
| Sales chart | `/api/v1/seller/dashboard/sales-chart` | `/api/v1/seller-dashboard/dashboard/sales-chart` | **MISMATCH** |
| Top products | `/api/v1/seller/dashboard/top-products` | `/api/v1/seller-dashboard/dashboard/top-products` | **MISMATCH** |
| Products management | `/api/v1/seller/products/management` | `/api/v1/seller-dashboard/products/management` | **MISMATCH** |
| Upload image | `/api/v1/seller/upload-image` | `/api/v1/seller-dashboard/upload-image` | **MISMATCH** |
| Bulk update status | `/api/v1/seller/bulk-operations/update-status` | `/api/v1/seller-dashboard/bulk-operations/update-status` | **MISMATCH** |
| Bulk update prices | `/api/v1/seller/bulk-operations/update-prices` | `/api/v1/seller-dashboard/bulk-operations/update-prices` | **MISMATCH** |
| Delete product | `/api/v1/seller/products/{id}` | `/api/v1/seller-dashboard/products/{id}` | **MISMATCH** |

**Root Cause:** Frontend `sellerService.js` uses `/api/v1/seller/` while backend uses `/api/v1/seller-dashboard/`.

**Fix Options:**
1. Update frontend to use `/api/v1/seller-dashboard/`
2. Update backend router prefix from `seller-dashboard` to `seller`
3. Add route aliases in backend

---

### C.3 Seller Analytics Base Path

| Feature | Frontend Path | Backend Path | Match |
|---------|---------------|--------------|-------|
| Dashboard analytics | `/api/v1/seller/analytics/analytics/dashboard` | `/api/v1/seller-analytics/analytics/dashboard` | **MISMATCH** |
| Revenue trends | `/api/v1/seller/analytics/analytics/revenue-trends` | `/api/v1/seller-analytics/analytics/revenue-trends` | **MISMATCH** |
| Category performance | `/api/v1/seller/analytics/analytics/category-performance` | `/api/v1/seller-analytics/analytics/category-performance` | **MISMATCH** |
| Customer demographics | `/api/v1/seller/analytics/analytics/customer-demographics` | `/api/v1/seller-analytics/analytics/customer-demographics` | **MISMATCH** |
| Performance metrics | `/api/v1/seller/analytics/analytics/performance-metrics` | `/api/v1/seller-analytics/analytics/performance-metrics` | **MISMATCH** |
| Top products | `/api/v1/seller/analytics/analytics/top-products` | `/api/v1/seller-analytics/analytics/top-products` | **MISMATCH** |
| Comparison | `/api/v1/seller/analytics/analytics/comparison` | `/api/v1/seller-analytics/analytics/comparison` | **MISMATCH** |

**Root Cause:** Frontend `sellerAnalyticsService.js` uses `/api/v1/seller/analytics/` while backend uses `/api/v1/seller-analytics/`.

---

### C.4 Seller Profile Base Path

| Feature | Frontend Path | Backend Path | Match |
|---------|---------------|--------------|-------|
| Get profile | `/api/v1/seller/profile/profile` | `/api/v1/seller-profile/profile` | **MISMATCH** |
| Update profile | `/api/v1/seller/profile/profile` | `/api/v1/seller-profile/profile` | **MISMATCH** |
| Get store | `/api/v1/seller/profile/store` | `/api/v1/seller-profile/store` | **MISMATCH** |
| Create theme | `/api/v1/seller/profile/themes` | `/api/v1/seller-profile/themes` | **MISMATCH** |
| Update theme | `/api/v1/seller/profile/themes/{id}` | `/api/v1/seller-profile/themes/{id}` | **MISMATCH** |
| Activate theme | `/api/v1/seller/profile/themes/{id}/activate` | `/api/v1/seller-profile/themes/{id}/activate` | **MISMATCH** |
| Delete theme | `/api/v1/seller/profile/themes/{id}` | `/api/v1/seller-profile/themes/{id}` | **MISMATCH** |
| Public store | `/api/v1/seller/profile/public/{id}` | `/api/v1/seller-profile/public/{id}` | **MISMATCH** |
| Store analytics | `/api/v1/seller/profile/analytics` | `/api/v1/seller-profile/analytics` | **MISMATCH** |
| Store stats | `/api/v1/seller/profile/stats` | `/api/v1/seller-profile/stats` | **MISMATCH** |
| Upload logo | `/api/v1/seller/profile/upload-logo` | `/api/v1/seller-profile/upload-logo` | **MISMATCH** |
| Upload banner | `/api/v1/seller/profile/upload-banner` | `/api/v1/seller-profile/upload-banner` | **MISMATCH** |
| Request verification | `/api/v1/seller/profile/verify` | `/api/v1/seller-profile/verify` | **MISMATCH** |

**Root Cause:** Frontend `sellerProfileService.js` uses `/api/v1/seller/profile/` while backend uses `/api/v1/seller-profile/`.

---

## SECTION D: HTTP Method Mismatches

| Feature | Frontend Method | Backend Method | Service File |
|---------|----------------|----------------|--------------|
| Cancel order | POST | PUT (generic update) | `customerOrderService.js` |
| Update order status | PUT | PATCH | `orderFulfillmentService.js` |
| Ship order | PUT | POST | `orderFulfillmentService.js` |

---

## SECTION E: Implementation Priority Matrix

### Critical (Must Fix - Currently Broken)

| # | Issue | Files Affected | Effort |
|---|-------|----------------|--------|
| 1 | Order fulfillment base path mismatch | `orderFulfillmentService.js` | Low |
| 2 | Seller dashboard base path mismatch | `sellerService.js` | Low |
| 3 | Seller analytics base path mismatch | `sellerAnalyticsService.js` | Low |
| 4 | Seller profile base path mismatch | `sellerProfileService.js` | Low |

### High Priority (Important Features Missing)

| # | Feature | Type | Effort |
|---|---------|------|--------|
| 1 | Product variants system | Backend implementation | High |
| 2 | Review creation in frontend | Frontend implementation | Medium |
| 3 | Search suggestions | Frontend integration | Low |
| 4 | Filter options | Frontend integration | Low |
| 5 | Dedicated cancel order endpoint | Backend implementation | Low |

### Medium Priority (Nice to Have)

| # | Feature | Type | Effort |
|---|---------|------|--------|
| 1 | Product slug lookup | Backend implementation | Low |
| 2 | New products endpoint | Backend implementation | Low |
| 3 | Discounted products endpoint | Backend implementation | Low |
| 4 | Product view tracking | Frontend integration | Low |
| 5 | Online users in chat | Frontend integration | Low |
| 6 | Trending products | Frontend integration | Low |
| 7 | Product availability check | Backend implementation | Medium |
| 8 | Product specifications endpoint | Backend implementation | Medium |
| 9 | Product attributes endpoint | Backend implementation | Medium |

### Low Priority (Future Enhancements)

| # | Feature | Type | Effort |
|---|---------|------|--------|
| 1 | Price history tracking | Backend implementation | Medium |
| 2 | Product comparison | Backend + Frontend | High |
| 3 | Brands system | Backend + Frontend | Medium |
| 4 | Product tags | Backend + Frontend | Medium |
| 5 | Scheduled analytics reports | Backend implementation | High |
| 6 | Review helpful voting | Frontend integration | Low |
| 7 | Review editing | Frontend implementation | Medium |

---

## SECTION F: Recommended Fixes

### F.1 Immediate Fixes (Path Corrections)

**File: `front_end/src/services/orderFulfillmentService.js`**
```javascript
// Line ~15: Change
const BASE_URL = '/api/v1/orders';
// To:
const BASE_URL = '/api/v1/order-fulfillment/orders';

// Also update shipOrder function to use POST instead of PUT
// And updateOrderStatus to use PATCH to /status endpoint
```

**File: `front_end/src/services/sellerService.js`**
```javascript
// Update all endpoints from:
/api/v1/seller/dashboard/...
/api/v1/seller/products/...
/api/v1/seller/bulk-operations/...
/api/v1/seller/upload-image

// To:
/api/v1/seller-dashboard/dashboard/...
/api/v1/seller-dashboard/products/...
/api/v1/seller-dashboard/bulk-operations/...
/api/v1/seller-dashboard/upload-image
```

**File: `front_end/src/services/sellerAnalyticsService.js`**
```javascript
// Update BASE_URL from:
/api/v1/seller/analytics
// To:
/api/v1/seller-analytics
```

**File: `front_end/src/services/sellerProfileService.js`**
```javascript
// Update BASE_URL from:
/api/v1/seller/profile
// To:
/api/v1/seller-profile
```

### F.2 Backend Endpoints to Add

```python
# In products.py router:
@router.get("/slug/{slug}")
async def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get product by slug"""
    pass

@router.get("/new")
async def get_new_products(limit: int = 10, db: Session = Depends(get_db)):
    """Get newest products"""
    pass

@router.get("/discounted")
async def get_discounted_products(limit: int = 10, db: Session = Depends(get_db)):
    """Get discounted products"""
    pass

@router.get("/categories/{category_id}")
async def get_category_by_id(category_id: int, db: Session = Depends(get_db)):
    """Get single category"""
    pass

@router.get("/{product_id}/variants")
async def get_product_variants(product_id: int, db: Session = Depends(get_db)):
    """Get product variants"""
    pass

@router.get("/{product_id}/availability")
async def check_product_availability(product_id: int, db: Session = Depends(get_db)):
    """Check product availability"""
    pass

@router.get("/{product_id}/specifications")
async def get_product_specifications(product_id: int, db: Session = Depends(get_db)):
    """Get product specifications"""
    pass

# In orders.py router:
@router.post("/{order_id}/cancel")
async def cancel_order(order_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Cancel an order"""
    pass
```

### F.3 Frontend Integrations to Add

```javascript
// In productService.js - Integrate existing backend endpoints:
export const getTrendingProducts = async (limit = 10) => {
  return apiClient.get(`/api/v1/products/trending?limit=${limit}`);
};

export const getSearchSuggestions = async (query) => {
  return apiClient.get(`/api/v1/products/search/suggestions?q=${query}`);
};

export const getFilterOptions = async () => {
  return apiClient.get('/api/v1/products/filters/options');
};

export const trackProductView = async (productId) => {
  return apiClient.post(`/api/v1/products/${productId}/view`);
};

// In reviewService.js (new file or add to productService.js):
export const createReview = async (reviewData) => {
  return apiClient.post('/api/v1/reviews/', reviewData);
};

export const updateReview = async (reviewId, reviewData) => {
  return apiClient.put(`/api/v1/reviews/${reviewId}`, reviewData);
};

export const markReviewHelpful = async (reviewId) => {
  return apiClient.post(`/api/v1/reviews/${reviewId}/helpful`);
};
```

---

## Appendix: File Reference

### Frontend Service Files
- `/front_end/src/services/apiClient.js`
- `/front_end/src/services/authService.js`
- `/front_end/src/services/cartService.js`
- `/front_end/src/services/chatService.js`
- `/front_end/src/services/customerOrderService.js`
- `/front_end/src/services/orderFulfillmentService.js`
- `/front_end/src/services/productService.js`
- `/front_end/src/services/sellerAnalyticsService.js`
- `/front_end/src/services/sellerProfileService.js`
- `/front_end/src/services/sellerService.js`

### Backend Router Files
- `/back_end/app/routers/auth.py`
- `/back_end/app/routers/users.py`
- `/back_end/app/routers/products.py`
- `/back_end/app/routers/cart.py`
- `/back_end/app/routers/orders.py`
- `/back_end/app/routers/reviews.py`
- `/back_end/app/routers/order_fulfillment.py`
- `/back_end/app/routers/chat.py`
- `/back_end/app/routers/seller_profile.py`
- `/back_end/app/routers/seller_dashboard.py`
- `/back_end/app/routers/seller_analytics.py`

---

*Document generated by API analysis tool. Last updated: 2026-01-13*
