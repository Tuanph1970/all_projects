# ALL TEST CASES - Ceramic Mobile App

## Table of Contents
1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Product](#product)
4. [Cart](#cart)
5. [Orders](#orders)
6. [Reviews](#reviews)
7. [Seller Profile](#seller-profile)
8. [Business & Payment](#business--payment)

---

## Authentication

### API Endpoints
- POST `/api/v1/auth/register` - User registration
- POST `/api/v1/auth/login` - User login
- POST `/api/v1/auth/logout` - User logout
- POST `/api/v1/auth/refresh` - Refresh access token
- POST `/api/v1/auth/verify-email` - Verify email address
- POST `/api/v1/auth/resend-verification` - Resend verification email
- POST `/api/v1/auth/forgot-password` - Request password reset
- POST `/api/v1/auth/reset-password` - Reset password with token
- POST `/api/v1/auth/switch-role` - Switch user role (customer/seller/dual)
- GET `/api/v1/auth/me` - Get current user info

### Screens
- LoginScreen
- RegisterScreen
- ForgotPasswordScreen
- ResetPasswordScreen
- ChangePasswordScreen (Profile)

### Test Cases

#### TC-AUTH-001: Login with Valid Credentials (Customer)
- **Category**: Authentication
- **API**: POST `/api/v1/auth/login`
- **Test File**: `e2e/auth/login.test.js:30`
- **Priority**: High
- **Description**: Verify customer can login with valid username and password
- **Preconditions**: Test user account exists
- **Steps**:
  1. Launch app
  2. Enter valid username
  3. Enter valid password
  4. Tap login button
- **Expected Result**: Successfully logged in, navigates to home screen

#### TC-AUTH-002: Login with Valid Credentials (Seller)
- **Category**: Authentication
- **API**: POST `/api/v1/auth/login`
- **Test File**: `e2e/auth/login.test.js:271`
- **Priority**: High
- **Description**: Verify seller can login with valid credentials
- **Expected Result**: Successfully logged in, navigates to home screen

#### TC-AUTH-003: Login with Email
- **Category**: Authentication
- **API**: POST `/api/v1/auth/login`
- **Test File**: `e2e/auth/login.test.js:62`
- **Priority**: Medium
- **Description**: Verify user can login using email instead of username

#### TC-AUTH-004: Login Validation - Empty Username
- **Category**: Authentication
- **Test File**: `e2e/auth/login.test.js:88`
- **Priority**: High
- **Description**: Verify error message for empty username field
- **Expected Result**: Display "Username or email is required"

#### TC-AUTH-005: Login Validation - Empty Password
- **Category**: Authentication
- **Test File**: `e2e/auth/login.test.js:102`
- **Priority**: High
- **Description**: Verify error message for empty password field
- **Expected Result**: Display "Password is required"

#### TC-AUTH-006: Login Validation - Invalid Credentials
- **Category**: Authentication
- **API**: POST `/api/v1/auth/login`
- **Test File**: `e2e/auth/login.test.js:116`
- **Priority**: High
- **Description**: Verify error handling for incorrect username/password
- **Expected Result**: Remain on login screen, display error

#### TC-AUTH-007: Login Validation - Short Username
- **Category**: Authentication
- **Test File**: `e2e/auth/login.test.js:137`
- **Priority**: Medium
- **Description**: Verify validation for username less than 3 characters
- **Expected Result**: Display "Username must be at least 3 characters"

#### TC-AUTH-008: Login Validation - Short Password
- **Category**: Authentication
- **Test File**: `e2e/auth/login.test.js:156`
- **Priority**: Medium
- **Description**: Verify validation for password less than 6 characters
- **Expected Result**: Display "Password must be at least 6 characters"

#### TC-AUTH-009: Login UI - Password Toggle
- **Category**: Authentication
- **Test File**: `e2e/auth/login.test.js:177`
- **Priority**: Low
- **Description**: Verify password visibility toggle functionality

#### TC-AUTH-010: Login UI - Navigate to Register
- **Category**: Authentication
- **Test File**: `e2e/auth/login.test.js:196`
- **Priority**: Medium
- **Description**: Verify navigation to register screen from login
- **Expected Result**: Navigate to register screen

#### TC-AUTH-011: Login UI - Navigate to Forgot Password
- **Category**: Authentication
- **Test File**: `e2e/auth/login.test.js:207`
- **Priority**: Medium
- **Description**: Verify navigation to forgot password screen
- **Expected Result**: Navigate to forgot password screen

#### TC-AUTH-012: Register as Customer
- **Category**: Authentication
- **API**: POST `/api/v1/auth/register`
- **Test File**: `e2e/auth/register.test.js:87`
- **Priority**: High
- **Description**: Verify successful customer registration
- **Expected Result**: Registration successful, navigate to login screen

#### TC-AUTH-013: Register as Seller
- **Category**: Authentication
- **API**: POST `/api/v1/auth/register`
- **Test File**: `e2e/auth/register.test.js:106`
- **Priority**: High
- **Description**: Verify successful seller registration
- **Expected Result**: Registration successful, verification email sent

#### TC-AUTH-014: Register as Dual Role
- **Category**: Authentication
- **API**: POST `/api/v1/auth/register`
- **Test File**: `e2e/auth/register.test.js:124`
- **Priority**: Medium
- **Description**: Verify dual role registration (customer + seller)

#### TC-AUTH-015: Register with Special Characters in Name
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:148`
- **Priority**: Medium
- **Description**: Verify registration accepts valid special characters (O'Brien, Smith-Jones)

#### TC-AUTH-016: Register Validation - Empty Fields
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:167-219`
- **Priority**: High
- **Description**: Verify all required field validations (firstName, lastName, username, email, password, confirmPassword)
- **Expected Result**: Display appropriate error messages for empty fields

#### TC-AUTH-017: Register Validation - Field Format
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:227-323`
- **Priority**: High
- **Description**: Verify field format validations (name length, username format, email format, password strength)

#### TC-AUTH-018: Register Validation - Password Mismatch
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:315`
- **Priority**: High
- **Description**: Verify error when password and confirm password don't match
- **Expected Result**: Display "Passwords do not match"

#### TC-AUTH-019: Register Validation - Duplicate Username
- **Category**: Authentication
- **API**: POST `/api/v1/auth/register`
- **Test File**: `e2e/auth/register.test.js:327`
- **Priority**: High
- **Description**: Verify error when username already exists
- **Expected Result**: Display "Username already exists"

#### TC-AUTH-020: Register Validation - Duplicate Email
- **Category**: Authentication
- **API**: POST `/api/v1/auth/register`
- **Test File**: `e2e/auth/register.test.js:341`
- **Priority**: High
- **Description**: Verify error when email already exists
- **Expected Result**: Display "Email already exists"

#### TC-AUTH-021: Register UI - Password Toggle
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:357`
- **Priority**: Low
- **Description**: Verify password visibility toggle

#### TC-AUTH-022: Register UI - Navigate Back to Login
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:373`
- **Priority**: Medium
- **Description**: Verify navigation back to login screen

#### TC-AUTH-023: Register UI - Role Selection
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:395`
- **Priority**: Medium
- **Description**: Verify switching between customer and seller roles

#### TC-AUTH-024: Register Edge Case - Network Error
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:413`
- **Priority**: High
- **Description**: Verify error handling when network is unavailable
- **Expected Result**: Display network error message

#### TC-AUTH-025: Register Edge Case - Whitespace Trimming
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:430`
- **Priority**: Medium
- **Description**: Verify whitespace is trimmed from username and email

#### TC-AUTH-026: Register Edge Case - Rapid Submission
- **Category**: Authentication
- **Test File**: `e2e/auth/register.test.js:445`
- **Priority**: Medium
- **Description**: Verify form prevents duplicate submission on rapid clicks

#### TC-AUTH-027: Post-Registration Login
- **Category**: Authentication
- **API**: POST `/api/v1/auth/register`, POST `/api/v1/auth/login`
- **Test File**: `e2e/auth/register.test.js:461`
- **Priority**: High
- **Description**: Verify user can login after successful registration

#### TC-AUTH-028: Logout from Profile
- **Category**: Authentication
- **API**: POST `/api/v1/auth/logout`
- **Test File**: `e2e/auth/logout.test.js:51`
- **Priority**: High
- **Description**: Verify successful logout from profile screen
- **Expected Result**: Navigate back to login screen, session cleared

#### TC-AUTH-029: Logout - Session Data Cleared
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:80`
- **Priority**: High
- **Description**: Verify session data is cleared after logout
- **Expected Result**: Cannot access protected screens

#### TC-AUTH-030: Logout - Customer User
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:104`
- **Priority**: Medium
- **Description**: Verify customer logout flow

#### TC-AUTH-031: Logout - Seller User
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:114`
- **Priority**: Medium
- **Description**: Verify seller logout flow

#### TC-AUTH-032: Logout - Confirmation Dialog
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:126`
- **Priority**: Medium
- **Description**: Verify logout confirmation dialog appears

#### TC-AUTH-033: Logout - Cancel Action
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:141`
- **Priority**: Medium
- **Description**: Verify user can cancel logout
- **Expected Result**: Remain on profile screen

#### TC-AUTH-034: Logout - Offline Mode
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:161`
- **Priority**: High
- **Description**: Verify logout works when server is unreachable
- **Expected Result**: Local logout still succeeds

#### TC-AUTH-035: Logout - Protected Screen Access
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:182`
- **Priority**: High
- **Description**: Verify cannot access protected screens after logout

#### TC-AUTH-036: Logout - Rapid Clicks
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:198`
- **Priority**: Low
- **Description**: Verify handling of multiple rapid logout attempts

#### TC-AUTH-037: Post-Logout Re-Login
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:219`
- **Priority**: High
- **Description**: Verify user can login again after logout

#### TC-AUTH-038: Post-Logout Data Refresh
- **Category**: Authentication
- **Test File**: `e2e/auth/logout.test.js:248`
- **Priority**: Medium
- **Description**: Verify cached data is cleared and refreshed after logout

#### TC-AUTH-039: Forgot Password - Send Reset Email
- **Category**: Authentication
- **API**: POST `/api/v1/auth/forgot-password`
- **Test File**: `e2e/auth/resetPassword.test.js:28`
- **Priority**: High
- **Description**: Verify password reset email is sent successfully
- **Expected Result**: Success message, navigate back to login

#### TC-AUTH-040: Forgot Password - Valid Email Formats
- **Category**: Authentication
- **Test File**: `e2e/auth/resetPassword.test.js:57`
- **Priority**: Medium
- **Description**: Verify various valid email formats are accepted

#### TC-AUTH-041: Forgot Password - Empty Email
- **Category**: Authentication
- **Test File**: `e2e/auth/resetPassword.test.js:93`
- **Priority**: High
- **Description**: Verify validation for empty email field
- **Expected Result**: Display "Email is required"

#### TC-AUTH-042: Forgot Password - Invalid Email Format
- **Category**: Authentication
- **Test File**: `e2e/auth/resetPassword.test.js:102`
- **Priority**: High
- **Description**: Verify validation for invalid email format
- **Expected Result**: Display "Invalid email address"

#### TC-AUTH-043: Forgot Password - Non-Existent Email
- **Category**: Authentication
- **API**: POST `/api/v1/auth/forgot-password`
- **Test File**: `e2e/auth/resetPassword.test.js:112`
- **Priority**: Medium
- **Description**: Verify error for email not in system
- **Expected Result**: Display "Email not found"

#### TC-AUTH-044: Forgot Password - Navigate Back
- **Category**: Authentication
- **Test File**: `e2e/auth/resetPassword.test.js:127`
- **Priority**: Low
- **Description**: Verify navigation back to login screen

#### TC-AUTH-045: Reset Password with Valid Token
- **Category**: Authentication
- **API**: POST `/api/v1/auth/reset-password`
- **Test File**: `e2e/auth/resetPassword.test.js:159`
- **Priority**: High
- **Description**: Verify password reset with valid token
- **Expected Result**: Password reset successful, can login with new password

#### TC-AUTH-046: Reset Password - Invalid Token
- **Category**: Authentication
- **API**: POST `/api/v1/auth/reset-password`
- **Test File**: `e2e/auth/resetPassword.test.js:228`
- **Priority**: High
- **Description**: Verify error for expired/invalid reset token
- **Expected Result**: Display "Invalid Reset Link"

#### TC-AUTH-047: Reset Password - Missing Token
- **Category**: Authentication
- **Test File**: `e2e/auth/resetPassword.test.js:241`
- **Priority**: Medium
- **Description**: Verify error when token is missing

#### TC-AUTH-048: Reset Password Validation - Empty Password
- **Category**: Authentication
- **Test File**: `e2e/auth/resetPassword.test.js:265`
- **Priority**: High
- **Description**: Verify validation for empty password field

#### TC-AUTH-049: Reset Password Validation - Password Mismatch
- **Category**: Authentication
- **Test File**: `e2e/auth/resetPassword.test.js:272`
- **Priority**: High
- **Description**: Verify validation when passwords don't match

#### TC-AUTH-050: Reset Password Validation - Weak Password
- **Category**: Authentication
- **Test File**: `e2e/auth/resetPassword.test.js:288`
- **Priority**: High
- **Description**: Verify validation for password strength

#### TC-AUTH-051: Reset Password - Token Reuse Prevention
- **Category**: Authentication
- **Test File**: `e2e/auth/resetPassword.test.js:357`
- **Priority**: High
- **Description**: Verify reset token can only be used once

#### TC-AUTH-052: Change Password - Success
- **Category**: Authentication
- **API**: POST `/api/v1/users/me/change-password`
- **Test File**: `e2e/auth/changePassword.test.js:54`
- **Priority**: High
- **Description**: Verify user can change password while logged in
- **Expected Result**: Password changed, can login with new password

#### TC-AUTH-053: Change Password - Empty Current Password
- **Category**: Authentication
- **Test File**: `e2e/auth/changePassword.test.js:129`
- **Priority**: High
- **Description**: Verify validation for empty current password
- **Expected Result**: Display "Current password is required"

#### TC-AUTH-054: Change Password - Empty New Password
- **Category**: Authentication
- **Test File**: `e2e/auth/changePassword.test.js:148`
- **Priority**: High
- **Description**: Verify validation for empty new password

#### TC-AUTH-055: Change Password - Password Mismatch
- **Category**: Authentication
- **Test File**: `e2e/auth/changePassword.test.js:168`
- **Priority**: High
- **Description**: Verify validation when new passwords don't match

#### TC-AUTH-056: Change Password - Incorrect Current Password
- **Category**: Authentication
- **API**: POST `/api/v1/users/me/change-password`
- **Test File**: `e2e/auth/changePassword.test.js:190`
- **Priority**: High
- **Description**: Verify error when current password is incorrect
- **Expected Result**: Display "Incorrect current password"

#### TC-AUTH-057: Change Password - Weak New Password
- **Category**: Authentication
- **Test File**: `e2e/auth/changePassword.test.js:212`
- **Priority**: High
- **Description**: Verify validation for weak new password

#### TC-AUTH-058: Change Password UI - Toggle Visibility
- **Category**: Authentication
- **Test File**: `e2e/auth/changePassword.test.js:272-302`
- **Priority**: Low
- **Description**: Verify password visibility toggle for current and new password

#### TC-AUTH-059: Change Password - Same Password
- **Category**: Authentication
- **Test File**: `e2e/auth/changePassword.test.js:355`
- **Priority**: Medium
- **Description**: Verify handling when new password same as current

#### TC-AUTH-060: Token Refresh
- **Category**: Authentication
- **API**: POST `/api/v1/auth/refresh`
- **Priority**: High
- **Description**: Verify access token refresh with valid refresh token

#### TC-AUTH-061: Email Verification
- **Category**: Authentication
- **API**: POST `/api/v1/auth/verify-email`
- **Priority**: High
- **Description**: Verify email verification with token

#### TC-AUTH-062: Resend Verification Email
- **Category**: Authentication
- **API**: POST `/api/v1/auth/resend-verification`
- **Priority**: Medium
- **Description**: Verify resend verification email functionality

#### TC-AUTH-063: Switch Role - Customer to Seller
- **Category**: Authentication
- **API**: POST `/api/v1/auth/switch-role`
- **Priority**: Medium
- **Description**: Verify user can switch from customer to seller role

#### TC-AUTH-064: Switch Role - Seller to Customer
- **Category**: Authentication
- **API**: POST `/api/v1/auth/switch-role`
- **Priority**: Medium
- **Description**: Verify user can switch from seller to customer role

---

## User Management

### API Endpoints
- GET `/api/v1/users/` - Get all users
- GET `/api/v1/users/{user_id}` - Get user by ID
- GET `/api/v1/users/me/profile` - Get current user profile
- PUT `/api/v1/users/me/profile` - Update user profile
- DELETE `/api/v1/users/me/account` - Deactivate account
- GET `/api/v1/users/me/addresses` - Get user addresses
- POST `/api/v1/users/me/addresses` - Add new address
- GET `/api/v1/users/me/addresses/{address_id}` - Get specific address
- PUT `/api/v1/users/me/addresses/{address_id}` - Update address
- POST `/api/v1/users/me/addresses/{address_id}/set-default` - Set default address
- DELETE `/api/v1/users/me/addresses/{address_id}` - Delete address

### Screens
- ProfileScreen
- EditProfileScreen
- AddressManagementScreen
- AddAddressScreen
- EditAddressScreen

### Test Cases

#### TC-USER-001: View User Profile
- **Category**: User Management
- **API**: GET `/api/v1/users/me/profile`
- **Priority**: High
- **Description**: Verify user can view their profile information

#### TC-USER-002: Update User Profile
- **Category**: User Management
- **API**: PUT `/api/v1/users/me/profile`
- **Priority**: High
- **Description**: Verify user can update profile details (name, phone, etc.)

#### TC-USER-003: Deactivate Account
- **Category**: User Management
- **API**: DELETE `/api/v1/users/me/account`
- **Priority**: High
- **Description**: Verify user can deactivate their account

#### TC-USER-004: View Address List
- **Category**: User Management
- **API**: GET `/api/v1/users/me/addresses`
- **Priority**: High
- **Description**: Verify user can view all saved addresses

#### TC-USER-005: Add New Address
- **Category**: User Management
- **API**: POST `/api/v1/users/me/addresses`
- **Priority**: High
- **Description**: Verify user can add new shipping address

#### TC-USER-006: Add Address - Validation
- **Category**: User Management
- **Priority**: High
- **Description**: Verify all required address fields are validated

#### TC-USER-007: Add Address - Maximum Limit
- **Category**: User Management
- **API**: POST `/api/v1/users/me/addresses`
- **Priority**: Medium
- **Description**: Verify user cannot add more than 5 addresses

#### TC-USER-008: Update Address
- **Category**: User Management
- **API**: PUT `/api/v1/users/me/addresses/{address_id}`
- **Priority**: High
- **Description**: Verify user can update existing address

#### TC-USER-009: Set Default Address
- **Category**: User Management
- **API**: POST `/api/v1/users/me/addresses/{address_id}/set-default`
- **Priority**: High
- **Description**: Verify user can set an address as default

#### TC-USER-010: Delete Address
- **Category**: User Management
- **API**: DELETE `/api/v1/users/me/addresses/{address_id}`
- **Priority**: High
- **Description**: Verify user can delete an address

#### TC-USER-011: Delete Default Address
- **Category**: User Management
- **API**: DELETE `/api/v1/users/me/addresses/{address_id}`
- **Priority**: Medium
- **Description**: Verify default address is reassigned when deleted

---

## Product

### API Endpoints
- GET `/api/v1/products/` - Get all products (with filters)
- GET `/api/v1/products/{product_id}` - Get product details
- POST `/api/v1/products/` - Create product (seller only)
- PUT `/api/v1/products/{product_id}` - Update product (seller only)
- DELETE `/api/v1/products/{product_id}` - Delete product (seller only)
- GET `/api/v1/products/featured` - Get featured products
- GET `/api/v1/products/trending` - Get trending products
- GET `/api/v1/products/{product_id}/related` - Get related products
- GET `/api/v1/products/{product_id}/similar` - Get similar products
- GET `/api/v1/products/search/advanced` - Advanced search
- GET `/api/v1/products/search/suggestions` - Search suggestions
- GET `/api/v1/products/categories` - Get all categories
- POST `/api/v1/products/categories` - Create category
- GET `/api/v1/products/categories/{category_id}/products` - Get products by category
- GET `/api/v1/products/home/featured` - Get home featured products
- POST `/api/v1/products/{product_id}/view` - Track product view

### Screens
- HomeScreen
- ProductListScreen
- ProductDetailScreen
- SearchScreen
- CategoryScreen
- CreateProductScreen (Seller)
- EditProductScreen (Seller)

### Test Cases

#### TC-PRODUCT-001: View Product List
- **Category**: Product
- **API**: GET `/api/v1/products/`
- **Priority**: High
- **Description**: Verify user can view list of all products

#### TC-PRODUCT-002: View Product Details
- **Category**: Product
- **API**: GET `/api/v1/products/{product_id}`
- **Priority**: High
- **Description**: Verify user can view detailed product information

#### TC-PRODUCT-003: View Featured Products
- **Category**: Product
- **API**: GET `/api/v1/products/featured`
- **Priority**: High
- **Description**: Verify featured products are displayed

#### TC-PRODUCT-004: View Trending Products
- **Category**: Product
- **API**: GET `/api/v1/products/trending`
- **Priority**: Medium
- **Description**: Verify trending products based on recent activity

#### TC-PRODUCT-005: View Related Products
- **Category**: Product
- **API**: GET `/api/v1/products/{product_id}/related`
- **Priority**: Medium
- **Description**: Verify related products are shown based on category and tags

#### TC-PRODUCT-006: View Similar Products
- **Category**: Product
- **API**: GET `/api/v1/products/{product_id}/similar`
- **Priority**: Medium
- **Description**: Verify similar products based on attributes

#### TC-PRODUCT-007: Search Products - Basic
- **Category**: Product
- **API**: GET `/api/v1/products/?search={query}`
- **Priority**: High
- **Description**: Verify basic text search functionality

#### TC-PRODUCT-008: Search Products - Advanced
- **Category**: Product
- **API**: GET `/api/v1/products/search/advanced`
- **Priority**: High
- **Description**: Verify advanced search with multiple filters

#### TC-PRODUCT-009: Search Suggestions
- **Category**: Product
- **API**: GET `/api/v1/products/search/suggestions`
- **Priority**: Medium
- **Description**: Verify autocomplete search suggestions

#### TC-PRODUCT-010: Filter by Category
- **Category**: Product
- **API**: GET `/api/v1/products/?category_id={id}`
- **Priority**: High
- **Description**: Verify products can be filtered by category

#### TC-PRODUCT-011: Filter by Price Range
- **Category**: Product
- **API**: GET `/api/v1/products/?min_price={min}&max_price={max}`
- **Priority**: High
- **Description**: Verify products can be filtered by price range

#### TC-PRODUCT-012: Filter by Material
- **Category**: Product
- **API**: GET `/api/v1/products/search/advanced?material={material}`
- **Priority**: Medium
- **Description**: Verify products can be filtered by material

#### TC-PRODUCT-013: Filter by Color
- **Category**: Product
- **API**: GET `/api/v1/products/search/advanced?color={color}`
- **Priority**: Medium
- **Description**: Verify products can be filtered by color

#### TC-PRODUCT-014: Sort by Price
- **Category**: Product
- **API**: GET `/api/v1/products/?sort_by=price&sort_order=asc`
- **Priority**: High
- **Description**: Verify products can be sorted by price (low to high, high to low)

#### TC-PRODUCT-015: Sort by Date
- **Category**: Product
- **API**: GET `/api/v1/products/?sort_by=created_at&sort_order=desc`
- **Priority**: Medium
- **Description**: Verify products can be sorted by date (newest/oldest)

#### TC-PRODUCT-016: Sort by Rating
- **Category**: Product
- **API**: GET `/api/v1/products/?sort_by=rating`
- **Priority**: Medium
- **Description**: Verify products can be sorted by rating

#### TC-PRODUCT-017: View Categories List
- **Category**: Product
- **API**: GET `/api/v1/products/categories`
- **Priority**: High
- **Description**: Verify all product categories are displayed

#### TC-PRODUCT-018: View Category Tree
- **Category**: Product
- **API**: GET `/api/v1/products/categories/tree`
- **Priority**: Medium
- **Description**: Verify hierarchical category structure

#### TC-PRODUCT-019: View Products by Category
- **Category**: Product
- **API**: GET `/api/v1/products/categories/{category_id}/products`
- **Priority**: High
- **Description**: Verify products displayed for specific category

#### TC-PRODUCT-020: Home Featured Products
- **Category**: Product
- **API**: GET `/api/v1/products/home/featured`
- **Priority**: High
- **Description**: Verify home screen shows featured products

#### TC-PRODUCT-021: Product Pagination
- **Category**: Product
- **API**: GET `/api/v1/products/catalog/paginated`
- **Priority**: High
- **Description**: Verify infinite scroll/pagination works correctly

#### TC-PRODUCT-022: Product Image Gallery
- **Category**: Product
- **Priority**: High
- **Description**: Verify user can view product images in gallery

#### TC-PRODUCT-023: Product Out of Stock
- **Category**: Product
- **Priority**: High
- **Description**: Verify out of stock products are handled correctly

#### TC-PRODUCT-024: Create Product (Seller)
- **Category**: Product - Seller
- **API**: POST `/api/v1/products/`
- **Priority**: High
- **Description**: Verify seller can create new product

#### TC-PRODUCT-025: Create Product - Validation
- **Category**: Product - Seller
- **Priority**: High
- **Description**: Verify all required fields validated when creating product

#### TC-PRODUCT-026: Update Product (Seller)
- **Category**: Product - Seller
- **API**: PUT `/api/v1/products/{product_id}`
- **Priority**: High
- **Description**: Verify seller can update their product

#### TC-PRODUCT-027: Delete Product (Seller)
- **Category**: Product - Seller
- **API**: DELETE `/api/v1/products/{product_id}`
- **Priority**: High
- **Description**: Verify seller can delete (soft delete) their product

#### TC-PRODUCT-028: Create Product - Non-Seller
- **Category**: Product - Security
- **API**: POST `/api/v1/products/`
- **Priority**: High
- **Description**: Verify non-seller users cannot create products

#### TC-PRODUCT-029: Update Other's Product
- **Category**: Product - Security
- **API**: PUT `/api/v1/products/{product_id}`
- **Priority**: High
- **Description**: Verify seller cannot update another seller's product

#### TC-PRODUCT-030: Bulk Update Featured Status
- **Category**: Product - Seller
- **API**: POST `/api/v1/products/bulk/update-featured`
- **Priority**: Medium
- **Description**: Verify seller can bulk update featured status

---

## Cart

### API Endpoints
- GET `/api/v1/cart/` - Get user's cart
- POST `/api/v1/cart/add` - Add item to cart
- PUT `/api/v1/cart/items/{item_id}` - Update cart item quantity
- DELETE `/api/v1/cart/items/{item_id}` - Remove item from cart
- DELETE `/api/v1/cart/clear` - Clear entire cart
- GET `/api/v1/cart/count` - Get cart item count

### Screens
- CartScreen
- CheckoutScreen

### Test Cases

#### TC-CART-001: View Cart
- **Category**: Cart
- **API**: GET `/api/v1/cart/`
- **Priority**: High
- **Description**: Verify user can view their cart

#### TC-CART-002: View Empty Cart
- **Category**: Cart
- **API**: GET `/api/v1/cart/`
- **Priority**: High
- **Description**: Verify empty cart displays appropriate message

#### TC-CART-003: Add Product to Cart
- **Category**: Cart
- **API**: POST `/api/v1/cart/add`
- **Priority**: High
- **Description**: Verify user can add product to cart

#### TC-CART-004: Add Product - Quantity Selection
- **Category**: Cart
- **Priority**: High
- **Description**: Verify user can select quantity when adding to cart

#### TC-CART-005: Add Product - Stock Validation
- **Category**: Cart
- **API**: POST `/api/v1/cart/add`
- **Priority**: High
- **Description**: Verify cannot add more than available stock
- **Expected Result**: Display "Only X items available"

#### TC-CART-006: Add Duplicate Product
- **Category**: Cart
- **API**: POST `/api/v1/cart/add`
- **Priority**: High
- **Description**: Verify adding same product updates quantity

#### TC-CART-007: Update Cart Item Quantity
- **Category**: Cart
- **API**: PUT `/api/v1/cart/items/{item_id}`
- **Priority**: High
- **Description**: Verify user can update item quantity in cart

#### TC-CART-008: Update Quantity - Stock Validation
- **Category**: Cart
- **API**: PUT `/api/v1/cart/items/{item_id}`
- **Priority**: High
- **Description**: Verify cannot update quantity beyond stock

#### TC-CART-009: Remove Item from Cart
- **Category**: Cart
- **API**: DELETE `/api/v1/cart/items/{item_id}`
- **Priority**: High
- **Description**: Verify user can remove item from cart

#### TC-CART-010: Clear Cart
- **Category**: Cart
- **API**: DELETE `/api/v1/cart/clear`
- **Priority**: High
- **Description**: Verify user can clear entire cart

#### TC-CART-011: View Cart Count Badge
- **Category**: Cart
- **API**: GET `/api/v1/cart/count`
- **Priority**: Medium
- **Description**: Verify cart icon shows correct item count

#### TC-CART-012: Cart Summary - Subtotal
- **Category**: Cart
- **Priority**: High
- **Description**: Verify cart subtotal is calculated correctly

#### TC-CART-013: Cart Summary - Tax Calculation
- **Category**: Cart
- **Priority**: High
- **Description**: Verify tax is calculated correctly (8%)

#### TC-CART-014: Cart Summary - Shipping Cost
- **Category**: Cart
- **Priority**: High
- **Description**: Verify shipping cost calculation (free over $100)

#### TC-CART-015: Cart Summary - Total
- **Category**: Cart
- **Priority**: High
- **Description**: Verify total amount is correct (subtotal + tax + shipping)

#### TC-CART-016: Cart - Product Unavailable
- **Category**: Cart
- **Priority**: High
- **Description**: Verify handling when product in cart becomes unavailable

#### TC-CART-017: Cart - Price Change
- **Category**: Cart
- **Priority**: Medium
- **Description**: Verify cart shows updated price if product price changes

#### TC-CART-018: Cart Persistence
- **Category**: Cart
- **Priority**: High
- **Description**: Verify cart persists after logout/login

---

## Orders

### API Endpoints
- GET `/api/v1/orders/` - Get user's orders
- GET `/api/v1/orders/{order_id}` - Get order details
- POST `/api/v1/orders/` - Create order
- POST `/api/v1/orders/checkout` - Checkout from cart
- PUT `/api/v1/orders/{order_id}` - Update order status (seller only)

### Screens
- OrdersListScreen
- OrderDetailScreen
- CheckoutScreen
- OrderConfirmationScreen

### Test Cases

#### TC-ORDER-001: View Orders List (Customer)
- **Category**: Orders
- **API**: GET `/api/v1/orders/`
- **Priority**: High
- **Description**: Verify customer can view their order history

#### TC-ORDER-002: View Orders List (Seller)
- **Category**: Orders
- **API**: GET `/api/v1/orders/`
- **Priority**: High
- **Description**: Verify seller can view orders for their products

#### TC-ORDER-003: View Order Details
- **Category**: Orders
- **API**: GET `/api/v1/orders/{order_id}`
- **Priority**: High
- **Description**: Verify user can view detailed order information

#### TC-ORDER-004: Checkout from Cart
- **Category**: Orders
- **API**: POST `/api/v1/orders/checkout`
- **Priority**: High
- **Description**: Verify user can checkout and create order from cart

#### TC-ORDER-005: Checkout - Address Selection
- **Category**: Orders
- **Priority**: High
- **Description**: Verify user can select shipping address during checkout

#### TC-ORDER-006: Checkout - Empty Cart
- **Category**: Orders
- **API**: POST `/api/v1/orders/checkout`
- **Priority**: High
- **Description**: Verify cannot checkout with empty cart
- **Expected Result**: Display "Cart is empty"

#### TC-ORDER-007: Checkout - Stock Validation
- **Category**: Orders
- **API**: POST `/api/v1/orders/checkout`
- **Priority**: High
- **Description**: Verify stock is checked before order creation
- **Expected Result**: Display "Insufficient stock for product X"

#### TC-ORDER-008: Checkout - Multi-Seller Validation
- **Category**: Orders
- **API**: POST `/api/v1/orders/checkout`
- **Priority**: High
- **Description**: Verify cart with items from multiple sellers handled correctly
- **Expected Result**: Display "Cart contains items from multiple sellers"

#### TC-ORDER-009: Order Confirmation
- **Category**: Orders
- **Priority**: High
- **Description**: Verify order confirmation screen shows correct details

#### TC-ORDER-010: Order - Stock Deduction
- **Category**: Orders - Business Logic
- **Priority**: High
- **Description**: Verify product stock is reduced after order creation

#### TC-ORDER-011: Order - Cart Cleared
- **Category**: Orders - Business Logic
- **Priority**: High
- **Description**: Verify cart is cleared after successful checkout

#### TC-ORDER-012: Update Order Status (Seller)
- **Category**: Orders - Seller
- **API**: PUT `/api/v1/orders/{order_id}`
- **Priority**: High
- **Description**: Verify seller can update order status (processing, shipped, delivered)

#### TC-ORDER-013: Update Order - Authorization
- **Category**: Orders - Security
- **API**: PUT `/api/v1/orders/{order_id}`
- **Priority**: High
- **Description**: Verify only order's seller can update order status

#### TC-ORDER-014: View Order - Authorization
- **Category**: Orders - Security
- **API**: GET `/api/v1/orders/{order_id}`
- **Priority**: High
- **Description**: Verify user can only view their own orders

#### TC-ORDER-015: Order Number Generation
- **Category**: Orders - Business Logic
- **Priority**: Medium
- **Description**: Verify unique order numbers are generated (ORD-XXXXXXXX format)

---

## Reviews

### API Endpoints
- POST `/api/v1/reviews/` - Create review
- GET `/api/v1/reviews/product/{product_id}` - Get product reviews
- PUT `/api/v1/reviews/{review_id}` - Update review
- POST `/api/v1/reviews/{review_id}/helpful` - Mark review helpful

### Screens
- ProductDetailScreen (with reviews)
- ReviewListScreen
- WriteReviewScreen
- EditReviewScreen

### Test Cases

#### TC-REVIEW-001: View Product Reviews
- **Category**: Reviews
- **API**: GET `/api/v1/reviews/product/{product_id}`
- **Priority**: High
- **Description**: Verify user can view reviews for a product

#### TC-REVIEW-002: Write Review
- **Category**: Reviews
- **API**: POST `/api/v1/reviews/`
- **Priority**: High
- **Description**: Verify customer can write review after purchase

#### TC-REVIEW-003: Write Review - Rating Selection
- **Category**: Reviews
- **Priority**: High
- **Description**: Verify user can select rating (1-5 stars)

#### TC-REVIEW-004: Write Review - Validation
- **Category**: Reviews
- **Priority**: High
- **Description**: Verify review content validation (rating required, text optional)

#### TC-REVIEW-005: Write Review - Without Purchase
- **Category**: Reviews - Security
- **API**: POST `/api/v1/reviews/`
- **Priority**: High
- **Description**: Verify user cannot review product without purchase
- **Expected Result**: Display "Can only review your own orders"

#### TC-REVIEW-006: Write Review - Duplicate Prevention
- **Category**: Reviews - Business Logic
- **API**: POST `/api/v1/reviews/`
- **Priority**: High
- **Description**: Verify user cannot review same product/order twice
- **Expected Result**: Display "Review already exists for this product and order"

#### TC-REVIEW-007: Update Review
- **Category**: Reviews
- **API**: PUT `/api/v1/reviews/{review_id}`
- **Priority**: Medium
- **Description**: Verify user can edit their own review

#### TC-REVIEW-008: Update Review - Authorization
- **Category**: Reviews - Security
- **API**: PUT `/api/v1/reviews/{review_id}`
- **Priority**: High
- **Description**: Verify user can only edit their own reviews

#### TC-REVIEW-009: Seller Response to Review
- **Category**: Reviews
- **API**: PUT `/api/v1/reviews/{review_id}`
- **Priority**: Medium
- **Description**: Verify seller can respond to review of their product

#### TC-REVIEW-010: Mark Review Helpful
- **Category**: Reviews
- **API**: POST `/api/v1/reviews/{review_id}/helpful`
- **Priority**: Low
- **Description**: Verify user can mark review as helpful

#### TC-REVIEW-011: Review Pagination
- **Category**: Reviews
- **Priority**: Medium
- **Description**: Verify review list pagination works correctly

#### TC-REVIEW-012: Review Sorting
- **Category**: Reviews
- **Priority**: Medium
- **Description**: Verify reviews can be sorted (newest, helpful, rating)

#### TC-REVIEW-013: Verified Purchase Badge
- **Category**: Reviews
- **Priority**: Low
- **Description**: Verify "Verified Purchase" badge shows for actual purchases

---

## Seller Profile

### API Endpoints
- GET `/api/v1/seller-profile/profile` - Get seller profile
- PUT `/api/v1/seller-profile/profile` - Update seller profile
- GET `/api/v1/seller-profile/store` - Get store information
- POST `/api/v1/seller-profile/themes` - Create store theme
- PUT `/api/v1/seller-profile/themes/{theme_id}` - Update theme
- POST `/api/v1/seller-profile/themes/{theme_id}/activate` - Activate theme
- DELETE `/api/v1/seller-profile/themes/{theme_id}` - Delete theme
- GET `/api/v1/seller-profile/public/{seller_id}` - Get public store
- GET `/api/v1/seller-profile/analytics` - Get store analytics
- GET `/api/v1/seller-profile/stats` - Get store statistics
- POST `/api/v1/seller-profile/upload-logo` - Upload store logo
- POST `/api/v1/seller-profile/upload-banner` - Upload store banner
- POST `/api/v1/seller-profile/verify` - Request business verification

### Screens
- SellerDashboardScreen
- SellerProfileScreen
- StoreCustomizationScreen
- StoreThemeScreen
- StoreAnalyticsScreen

### Test Cases

#### TC-SELLER-001: View Seller Profile
- **Category**: Seller Profile
- **API**: GET `/api/v1/seller-profile/profile`
- **Priority**: High
- **Description**: Verify seller can view their profile

#### TC-SELLER-002: Create Default Profile
- **Category**: Seller Profile
- **API**: GET `/api/v1/seller-profile/profile`
- **Priority**: High
- **Description**: Verify default profile is created for new seller

#### TC-SELLER-003: Update Seller Profile
- **Category**: Seller Profile
- **API**: PUT `/api/v1/seller-profile/profile`
- **Priority**: High
- **Description**: Verify seller can update profile information

#### TC-SELLER-004: Update Store Name
- **Category**: Seller Profile
- **Priority**: High
- **Description**: Verify seller can update store name

#### TC-SELLER-005: Update Store Description
- **Category**: Seller Profile
- **Priority**: High
- **Description**: Verify seller can update store description

#### TC-SELLER-006: Upload Store Logo
- **Category**: Seller Profile
- **API**: POST `/api/v1/seller-profile/upload-logo`
- **Priority**: High
- **Description**: Verify seller can upload store logo

#### TC-SELLER-007: Upload Store Banner
- **Category**: Seller Profile
- **API**: POST `/api/v1/seller-profile/upload-banner`
- **Priority**: High
- **Description**: Verify seller can upload store banner

#### TC-SELLER-008: Update Contact Information
- **Category**: Seller Profile
- **Priority**: High
- **Description**: Verify seller can update business contact info

#### TC-SELLER-009: Update Business Hours
- **Category**: Seller Profile
- **Priority**: Medium
- **Description**: Verify seller can set business hours

#### TC-SELLER-010: Update Shipping Policy
- **Category**: Seller Profile
- **Priority**: High
- **Description**: Verify seller can set shipping policy

#### TC-SELLER-011: Update Return Policy
- **Category**: Seller Profile
- **Priority**: High
- **Description**: Verify seller can set return policy

#### TC-SELLER-012: View Store Information
- **Category**: Seller Profile
- **API**: GET `/api/v1/seller-profile/store`
- **Priority**: High
- **Description**: Verify seller can view complete store information

#### TC-SELLER-013: Create Store Theme
- **Category**: Seller Profile
- **API**: POST `/api/v1/seller-profile/themes`
- **Priority**: Medium
- **Description**: Verify seller can create custom store theme

#### TC-SELLER-014: Update Store Theme
- **Category**: Seller Profile
- **API**: PUT `/api/v1/seller-profile/themes/{theme_id}`
- **Priority**: Medium
- **Description**: Verify seller can update theme settings

#### TC-SELLER-015: Activate Theme
- **Category**: Seller Profile
- **API**: POST `/api/v1/seller-profile/themes/{theme_id}/activate`
- **Priority**: Medium
- **Description**: Verify seller can activate a theme

#### TC-SELLER-016: Delete Theme
- **Category**: Seller Profile
- **API**: DELETE `/api/v1/seller-profile/themes/{theme_id}`
- **Priority**: Low
- **Description**: Verify seller can delete non-active theme

#### TC-SELLER-017: Delete Active Theme
- **Category**: Seller Profile
- **API**: DELETE `/api/v1/seller-profile/themes/{theme_id}`
- **Priority**: Medium
- **Description**: Verify cannot delete active theme
- **Expected Result**: Display "Cannot delete active theme"

#### TC-SELLER-018: View Public Store
- **Category**: Seller Profile
- **API**: GET `/api/v1/seller-profile/public/{seller_id}`
- **Priority**: High
- **Description**: Verify customers can view seller's public store

#### TC-SELLER-019: View Store Analytics
- **Category**: Seller Profile
- **API**: GET `/api/v1/seller-profile/analytics`
- **Priority**: High
- **Description**: Verify seller can view store analytics

#### TC-SELLER-020: View Store Statistics
- **Category**: Seller Profile
- **API**: GET `/api/v1/seller-profile/stats`
- **Priority**: Medium
- **Description**: Verify seller can view store statistics

#### TC-SELLER-021: Profile Completion Percentage
- **Category**: Seller Profile
- **Priority**: Low
- **Description**: Verify profile completion percentage is calculated

#### TC-SELLER-022: Request Business Verification
- **Category**: Seller Profile
- **API**: POST `/api/v1/seller-profile/verify`
- **Priority**: Medium
- **Description**: Verify seller can request business verification

#### TC-SELLER-023: Access Seller Features - Non-Seller
- **Category**: Seller Profile - Security
- **Priority**: High
- **Description**: Verify non-seller users cannot access seller features
- **Expected Result**: Display "Only sellers can access..."

---

## Business & Payment

### Additional API Endpoints (Referenced but not fully tested)
- Chat/Messaging endpoints
- Order fulfillment endpoints
- Seller analytics endpoints
- Seller dashboard endpoints

### Test Cases

#### TC-BUSINESS-001: View Sales Dashboard
- **Category**: Business
- **Priority**: High
- **Description**: Verify seller can view sales dashboard with metrics

#### TC-BUSINESS-002: View Order Fulfillment
- **Category**: Business
- **Priority**: High
- **Description**: Verify seller can view orders pending fulfillment

#### TC-BUSINESS-003: View Sales Analytics
- **Category**: Business
- **Priority**: Medium
- **Description**: Verify seller can view sales analytics and reports

#### TC-BUSINESS-004: Chat with Customer
- **Category**: Business
- **Priority**: Medium
- **Description**: Verify chat functionality between seller and customer

#### TC-BUSINESS-005: Product Performance Metrics
- **Category**: Business
- **Priority**: Medium
- **Description**: Verify seller can view product performance metrics

---

## Summary Statistics

### Total Test Cases by Category

| Category | Count | Priority High | Priority Medium | Priority Low |
|----------|-------|---------------|-----------------|--------------|
| Authentication | 64 | 49 | 14 | 1 |
| User Management | 11 | 9 | 2 | 0 |
| Product | 30 | 18 | 12 | 0 |
| Cart | 18 | 15 | 2 | 1 |
| Orders | 15 | 12 | 2 | 1 |
| Reviews | 13 | 7 | 5 | 1 |
| Seller Profile | 23 | 16 | 6 | 1 |
| Business | 5 | 3 | 2 | 0 |
| **TOTAL** | **179** | **129** | **45** | **5** |

### Test Coverage by Screen

| Screen | Test Cases | Implemented |
|--------|-----------|-------------|
| LoginScreen | 12 | ✅ |
| RegisterScreen | 17 | ✅ |
| ForgotPasswordScreen | 6 | ✅ |
| ResetPasswordScreen | 7 | ✅ |
| ChangePasswordScreen | 7 | ✅ |
| LogoutFlow | 10 | ✅ |
| ProfileScreen | 11 | 🔨 |
| ProductListScreen | 20 | 🔨 |
| ProductDetailScreen | 10 | 🔨 |
| CartScreen | 18 | 🔨 |
| CheckoutScreen | 9 | 🔨 |
| OrdersScreen | 15 | 🔨 |
| ReviewsScreen | 13 | 🔨 |
| SellerProfileScreen | 23 | 🔨 |
| SellerDashboardScreen | 5 | 🔨 |

Legend: ✅ Implemented | 🔨 Planned | ❌ Not Implemented

### API Endpoint Coverage

| Module | Total Endpoints | Test Coverage |
|--------|----------------|---------------|
| Auth | 11 | 100% |
| Users | 11 | 50% |
| Products | 25+ | 60% |
| Cart | 6 | 80% |
| Orders | 5 | 80% |
| Reviews | 4 | 75% |
| Seller Profile | 13 | 50% |
| **TOTAL** | **75+** | **70%** |

---

## Test Execution Plan

### Phase 1: Authentication (Current)
- ✅ Login tests (12 cases)
- ✅ Register tests (17 cases)
- ✅ Logout tests (10 cases)
- ✅ Password reset tests (13 cases)
- ✅ Change password tests (7 cases)

### Phase 2: User Management (Next)
- Profile management (11 cases)
- Address management (11 cases)

### Phase 3: Product & Cart
- Product browsing (20 cases)
- Product details (10 cases)
- Cart operations (18 cases)

### Phase 4: Orders & Checkout
- Checkout flow (9 cases)
- Order management (15 cases)

### Phase 5: Reviews & Ratings
- Review creation and management (13 cases)

### Phase 6: Seller Features
- Seller profile (23 cases)
- Product management (seller) (10 cases)
- Order fulfillment (5 cases)

---

## Notes

1. **Test Data Requirements**: Test users with different roles (customer, seller, dual) are required
2. **Network Simulation**: Some tests require network simulation (offline mode)
3. **Real Device Testing**: Recommended for final validation
4. **API Availability**: Backend server must be running and accessible
5. **Test Isolation**: Each test should be independent and clean up after itself
6. **Screenshot Documentation**: Screenshots are captured for all test scenarios

## Related Documentation

- `README_TESTING.md` - Testing framework setup and guidelines
- `DETOX_SETUP.md` - Detox configuration and environment setup
- `PROJECT_SUMMARY.md` - Overall project structure and architecture
- `TEST_REPORT.md` - Test execution results and metrics
