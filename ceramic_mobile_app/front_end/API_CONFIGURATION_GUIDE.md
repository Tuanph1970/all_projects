# API Configuration Guide

## Overview
This guide explains how to switch between local development and production environments for the Ceramic Marketplace mobile application.

## Quick Start

### Switching Environments

**Location:** `/front_end/src/constants/config.js`

**To switch environments, change just ONE line:**

```javascript
const ENVIRONMENT = 'local'; // Change to 'production' for deployment
```

### Environment Options

- **`'local'`** - For local development (localhost:8000)
- **`'production'`** - For production server (112.213.91.103:8000)

## Configuration Details

### Current Configuration

```javascript
const ENV_CONFIG = {
  local: {
    BASE_URL: 'http://localhost:8000',
    WS_URL: 'ws://localhost:8000',
  },
  production: {
    BASE_URL: 'http://112.213.91.103:8000',
    WS_URL: 'ws://112.213.91.103:8000',
  },
};
```

### Two-Stage Deployment Process

#### Stage 1: Local Testing
1. Open `/front_end/src/constants/config.js`
2. Set `ENVIRONMENT = 'local'`
3. Start your backend server locally on port 8000
4. Run the mobile app: `npm start` or `expo start`
5. Test all features locally

#### Stage 2: Production Deployment
1. Open `/front_end/src/constants/config.js`
2. Change `ENVIRONMENT = 'production'`
3. Build and deploy the app
4. All API calls will now point to `http://112.213.91.103:8000`

## What Was Updated

### 1. Centralized Configuration (`src/constants/config.js`)
- ✅ Single point of configuration for all API endpoints
- ✅ Environment-based URL switching
- ✅ WebSocket URL configuration for chat
- ✅ All API endpoints defined in one place

### 2. Updated Services

All service files now use centralized configuration:

#### Core Services
- ✅ `authService.js` - Authentication endpoints
- ✅ `productService.js` - Product management
- ✅ `cartService.js` - Shopping cart
- ✅ `chatService.js` - WebSocket chat (HTTP + WS)

#### Seller Services
- ✅ `sellerService.js` - Seller dashboard
- ✅ `sellerProfileService.js` - Seller profile management
- ✅ `sellerAnalyticsService.js` - Analytics and reporting
- ✅ `orderFulfillmentService.js` - Order processing

#### API Client
- ✅ `apiClient.js` - Uses centralized BASE_URL
- ✅ Automatic token management
- ✅ Request/response interceptors

## API Endpoints Reference

### Base Configuration
```javascript
API_CONFIG = {
  BASE_URL: currentEnv.BASE_URL,  // 'http://localhost:8000' or 'http://112.213.91.103:8000'
  WS_URL: currentEnv.WS_URL,      // WebSocket URL for chat
  TIMEOUT: 10000,                  // 10 seconds
}
```

### Authentication Endpoints
- `LOGIN: '/api/v1/auth/login'`
- `REGISTER: '/api/v1/auth/register'`
- `REFRESH: '/api/v1/auth/refresh'`
- `ME: '/api/v1/auth/me'`
- `LOGOUT: '/api/v1/auth/logout'`
- `SWITCH_ROLE: '/api/v1/auth/switch-role'`
- `VERIFY_EMAIL: '/api/v1/auth/verify-email'`
- `RESEND_VERIFICATION: '/api/v1/auth/resend-verification'`
- `FORGOT_PASSWORD: '/api/v1/auth/forgot-password'`
- `RESET_PASSWORD: '/api/v1/auth/reset-password'`

### User Endpoints
- `USER_PROFILE: '/api/v1/users/me/profile'`
- `USER_ADDRESSES: '/api/v1/users/me/addresses'`
- `CHANGE_PASSWORD: '/api/v1/users/me/change-password'`

### Product Endpoints
- `PRODUCTS: '/api/v1/products'`
- `CATEGORIES: '/api/v1/products/categories'`

### Order & Cart Endpoints
- `ORDERS: '/api/v1/orders'`
- `CART: '/api/v1/cart'`

### Chat Endpoints
- `CONVERSATIONS: '/api/v1/chat/conversations'`
- `MESSAGES: '/api/v1/chat/messages'`

### Review Endpoints
- `REVIEWS: '/api/v1/reviews'`

### Seller Endpoints
- `SELLER_DASHBOARD: '/api/v1/seller/dashboard'`
- `SELLER_PRODUCTS: '/api/v1/seller/products'`
- `SELLER_ANALYTICS: '/api/v1/seller/analytics'`
- `SELLER_PROFILE: '/api/v1/seller/profile'`
- `SELLER_FULFILLMENT: '/api/v1/seller/fulfillment'`

## Testing Checklist

### Local Testing (Stage 1)
- [ ] Set `ENVIRONMENT = 'local'` in config.js
- [ ] Backend running on localhost:8000
- [ ] Test user authentication (login/register)
- [ ] Test product browsing
- [ ] Test cart operations
- [ ] Test order placement
- [ ] Test chat functionality (WebSocket)
- [ ] Test seller dashboard (if applicable)

### Production Testing (Stage 2)
- [ ] Set `ENVIRONMENT = 'production'` in config.js
- [ ] Verify backend is accessible at 112.213.91.103:8000
- [ ] Test all features listed above
- [ ] Verify WebSocket connection for chat
- [ ] Test on actual device (not just simulator)

## Troubleshooting

### Issue: API calls fail with "Network Error"
**Solution:**
- Check that `ENVIRONMENT` is set correctly
- Verify backend server is running and accessible
- Check firewall/network settings

### Issue: WebSocket chat not connecting
**Solution:**
- Verify `WS_URL` is configured correctly
- Check that WebSocket port is open on server
- Ensure authentication token is valid

### Issue: Mixed content errors (HTTP/HTTPS)
**Solution:**
- Ensure both BASE_URL and WS_URL use the same protocol (http/ws or https/wss)
- Update production config to use HTTPS/WSS if server supports it

## Adding New Environments

To add a new environment (e.g., staging):

```javascript
const ENV_CONFIG = {
  local: {
    BASE_URL: 'http://localhost:8000',
    WS_URL: 'ws://localhost:8000',
  },
  staging: {
    BASE_URL: 'http://staging.example.com:8000',
    WS_URL: 'ws://staging.example.com:8000',
  },
  production: {
    BASE_URL: 'http://112.213.91.103:8000',
    WS_URL: 'ws://112.213.91.103:8000',
  },
};

const ENVIRONMENT = 'staging'; // or 'local' or 'production'
```

## Best Practices

1. **Never commit production URLs accidentally**
   - Always verify `ENVIRONMENT = 'local'` before committing
   - Consider using environment variables for sensitive data

2. **Test locally first**
   - Always test changes locally before deploying to production
   - Use the two-stage process outlined above

3. **Keep endpoints centralized**
   - All new endpoints should be added to `config.js`
   - Services should reference `API_CONFIG.ENDPOINTS.*`

4. **Version control**
   - Consider creating separate branches for production configs
   - Document any environment-specific changes

## Summary

✅ **Optimized Setup Complete**
- Single configuration file for all environments
- One-line change to switch between local and production
- All services updated to use centralized configuration
- WebSocket support for chat functionality
- Clear two-stage deployment process

**Next Steps:**
1. Test locally with `ENVIRONMENT = 'local'`
2. Verify all features work correctly
3. Switch to `ENVIRONMENT = 'production'` for deployment
4. Deploy and test on production server
