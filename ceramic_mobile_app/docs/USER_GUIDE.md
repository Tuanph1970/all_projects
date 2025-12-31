# Ceramic Marketplace Mobile App - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [User Registration & Login](#user-registration--login)
3. [Customer Mode Features](#customer-mode-features)
4. [Seller Mode Features](#seller-mode-features)
5. [Switching Between Modes](#switching-between-modes)
6. [Language Settings](#language-settings)
7. [Testing Scenarios](#testing-scenarios)

---

## Getting Started

### Installation
1. Download the Ceramic Marketplace app from your app store
2. Open the app - you'll see the welcome screen
3. Choose to either Login or Register

### First Time Setup
- Allow notifications when prompted (for order updates and messages)
- Select your preferred language (English or Vietnamese)
- Choose your user type during registration

---

## User Registration & Login

### Registration Process

#### Step 1: Choose User Type
- **Customer**: Can only buy products
- **Seller**: Can only sell products
- **Dual**: Can both buy and sell (switch between modes)

#### Step 2: Fill Registration Form
1. Enter your username (unique identifier)
2. Enter your email address
3. Create a strong password (minimum 8 characters)
4. Confirm your password
5. Accept terms and conditions
6. Tap "Register"

#### Step 3: Email Verification
1. Check your email for verification link
2. Click the link to verify your account
3. Return to the app and login

### Login Process
1. Enter username or email
2. Enter password
3. Tap "Login"
4. Optional: Enable "Remember Me" for easier future access

### Forgot Password
1. Tap "Forgot Password?" on login screen
2. Enter your registered email
3. Check email for reset link
4. Create new password
5. Login with new password

---

## Customer Mode Features

### 1. Home Screen Navigation
- **Search Bar**: Tap to search for products
- **Categories**: Swipe horizontally to browse categories
- **Featured Products**: Scroll down to see recommendations
- **Bottom Navigation**:
  - Home: Main marketplace
  - Categories: Browse by category
  - Cart: View shopping cart
  - Orders: Track your orders
  - Profile: Account settings

### 2. Browsing Products

#### Search Products
1. Tap search bar
2. Type product name or keywords
3. Use filters:
   - Price range (drag sliders)
   - Category (select from list)
   - Condition (New/Used/Refurbished)
   - Rating (1-5 stars)
4. Tap "Apply Filters"

#### View Product Details
1. Tap any product card
2. Swipe images to see all photos
3. Read product information:
   - Price
   - Description
   - Specifications (size, weight, material)
   - Seller information
   - Customer reviews
4. Check availability status

### 3. Shopping Cart

#### Add to Cart
1. On product page, tap "Add to Cart"
2. Select quantity (if available)
3. View cart badge update on bottom navigation

#### Manage Cart
1. Go to Cart tab
2. Adjust quantities with +/- buttons
3. Remove items with swipe gesture or delete icon
4. View subtotal at bottom

### 4. Checkout Process
1. From cart, tap "Proceed to Checkout"
2. Enter/select shipping address:
   - Full name
   - Phone number
   - Street address
   - City, State, Zip code
3. Review order summary
4. Select payment method
5. Tap "Place Order"
6. Receive order confirmation

### 5. Order Tracking
1. Go to Orders tab
2. View order list with statuses:
   - Pending (yellow)
   - Processing (blue)
   - Shipped (orange)
   - Delivered (green)
3. Tap order to see details:
   - Order number
   - Items ordered
   - Tracking information
   - Estimated delivery

### 6. Chat with Sellers
1. On product page, tap "Chat with Seller"
2. Type message in text field
3. Optional: Attach images with camera icon
4. Send message with send button
5. View read receipts (double checkmarks)

### 7. Product Reviews
1. Go to Orders → Completed orders
2. Tap "Write Review" on delivered items
3. Rate 1-5 stars
4. Write review text
5. Optional: Add photos
6. Submit review

### 8. Favorites
1. On product page, tap heart icon
2. View saved items in Profile → Favorites
3. Remove by tapping heart again

---

## Seller Mode Features

### 1. Seller Dashboard
Access from home screen in seller mode:
- **Today's Sales**: Revenue for current day
- **Pending Orders**: Orders awaiting processing
- **Low Stock Alert**: Products running out
- **Performance Metrics**: Sales trends

### 2. Product Management

#### Add New Product
1. Tap "+" button on products screen
2. Fill product details:
   - Product name
   - Description
   - Category (Common/Art)
   - Price
   - Quantity in stock
   - Specifications:
     - Dimensions (L×W×H)
     - Weight
     - Material type
     - Color options
   - Condition (New/Used/Refurbished)
3. Add photos:
   - Tap camera icon
   - Take photo or select from gallery
   - Add up to 5 images
   - First image becomes main photo
4. Tap "Publish Product"

#### Edit Product
1. Go to Products tab
2. Find product and tap edit icon
3. Modify any field
4. Save changes

#### Manage Inventory
1. View stock levels on products list
2. Tap product to update quantity
3. Set product as "Out of Stock" when needed
4. Activate/Deactivate products with toggle

### 3. Order Management

#### Process Orders
1. Go to Orders tab
2. View new orders in "Pending" section
3. Tap order to see details:
   - Customer information
   - Items ordered
   - Shipping address
4. Update order status:
   - Mark as "Processing"
   - Print shipping label
   - Mark as "Shipped" with tracking
   - Confirm "Delivered"

#### Handle Refunds
1. Find order in Orders list
2. Tap "Process Refund"
3. Select reason
4. Enter refund amount
5. Confirm refund

### 4. Analytics & Reports
1. Go to Analytics tab
2. View charts:
   - Sales over time (daily/weekly/monthly)
   - Top selling products
   - Revenue by category
   - Customer demographics
3. Export reports with export icon

### 5. Customer Communication
1. Go to Messages tab
2. View customer inquiries
3. Respond to messages
4. Send product updates
5. Share additional photos if requested

---

## Switching Between Modes

For Dual accounts only:
1. Go to Profile tab
2. Tap "Switch to Seller/Customer Mode"
3. Interface updates immediately
4. Bottom navigation changes based on mode

---

## Language Settings

1. Go to Profile → Settings
2. Tap "Language"
3. Select:
   - English
   - Tiếng Việt (Vietnamese)
4. App updates immediately

---

## Testing Scenarios

### Basic Customer Flow Test
1. **Registration & Login**
   - Register new customer account
   - Verify email
   - Login successfully

2. **Product Discovery**
   - Search for "ceramic bowl"
   - Apply price filter ($10-50)
   - View product details
   - Check all product images

3. **Purchase Flow**
   - Add 2 items to cart
   - Modify quantity in cart
   - Complete checkout
   - View order in Orders tab

4. **Communication**
   - Chat with seller about product
   - Send image in chat
   - Check message read status

### Basic Seller Flow Test
1. **Setup**
   - Login as seller
   - View dashboard metrics

2. **Product Listing**
   - Add new ceramic vase
   - Upload 3 product images
   - Set price and inventory
   - Publish product

3. **Order Processing**
   - View pending order
   - Update to processing
   - Mark as shipped
   - Add tracking number

4. **Analytics**
   - Check daily sales
   - View top products
   - Review revenue chart

### Advanced Testing
1. **Dual Mode**
   - Login as dual user
   - Buy product in customer mode
   - Switch to seller mode
   - List new product

2. **Error Handling**
   - Try login with wrong password
   - Search with no results
   - Add out-of-stock item to cart
   - Submit order with invalid address

3. **Performance**
   - Load product list with 50+ items
   - Upload 5 high-resolution images
   - Search with complex filters
   - Switch between tabs rapidly

### Network Scenarios
1. **Offline Mode**
   - Browse cached products
   - View cart offline
   - Try to checkout (should fail gracefully)

2. **Poor Connection**
   - Load images on slow network
   - Submit order with intermittent connection
   - Test chat message delivery

---

## Troubleshooting

### Common Issues

**Can't Login**
- Check username/email spelling
- Verify password is correct
- Ensure account is verified
- Try password reset

**Products Not Loading**
- Check internet connection
- Pull down to refresh
- Clear app cache in settings
- Update to latest version

**Order Issues**
- Verify shipping address
- Check payment method
- Contact seller through chat
- Report issue in Profile → Support

**App Crashes**
- Force close and restart app
- Check for app updates
- Clear app data (Profile → Settings)
- Reinstall if necessary

---

## Tips for Effective Testing

1. **Test Different User Journeys**
   - New user experience
   - Returning customer
   - Power seller scenarios

2. **Validate Data**
   - Check calculations (prices, totals)
   - Verify status updates
   - Confirm notifications work

3. **Test Edge Cases**
   - Maximum character limits
   - Minimum/maximum quantities
   - Special characters in text fields

4. **Check Responsiveness**
   - Portrait and landscape modes
   - Different device sizes
   - Various network conditions

5. **Verify Integrations**
   - Email notifications
   - Payment processing
   - Real-time chat updates

---

## Contact Support

For issues during testing:
- In-app: Profile → Help & Support
- Email: support@ceramicmarketplace.com
- Report bugs with screenshots when possible