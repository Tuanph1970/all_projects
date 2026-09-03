// ============================================
// ENVIRONMENT CONFIGURATION
// ============================================
// Change this single line to switch between environments:
// - 'local': Local development (localhost)
// - 'testing': E2E testing (direct API access)
// - 'production': Production server
// ============================================
// const ENVIRONMENT = 'testing'; // Use 'testing' for E2E tests
const ENVIRONMENT = 'production'; // Use 'production' for release
// ============================================

// Microservices Architecture:
// - All API requests go through Traefik API Gateway on port 80
// - Traefik routes requests to appropriate microservices:
//   /api/v1/auth/*     -> auth-service
//   /api/v1/products/* -> product-service
//   /api/v1/orders/*   -> order-service
//   /api/v1/cart/*     -> order-service
//   /api/v1/chat/*     -> chat-service
//   /api/v1/seller/*   -> seller-service

const ENV_CONFIG = {
  local: {
    // 10.0.2.2 is Android emulator's alias for host machine localhost
    BASE_URL: 'http://10.0.2.2',
    WS_URL: 'ws://10.0.2.2',
  },
  testing: {
    // E2E testing via Traefik gateway (10.0.2.2 is Android emulator's alias for host)
    // Auto-detect: tries each URL in order, uses first one that works
    BASE_URLS: [
      'http://10.0.2.2:8002',      // Office: direct Traefik port
      'http://10.0.2.2/mercai',   // Home: nginx proxy with /mercai path
      'http://10.0.2.2:80',        // Fallback: standard HTTP port
    ],
    BASE_URL: 'http://10.0.2.2:8002', // Default (will be auto-detected)
    WS_URL: 'ws://10.0.2.2:8002',
  },
  production: {
    // Cloudflare Tunnel -> Traefik gateway (:8002). Traefik serves /api/v1/*
    // at the root of this hostname, so there is no path prefix: the old
    // '/mercai-app' prefix was never served by any nginx config and 404'd.
    BASE_URL: 'https://mercai.tuan1970.com',
    WS_URL: 'wss://mercai.tuan1970.com',
  },
};

// Get current environment configuration
const currentEnv = ENV_CONFIG[ENVIRONMENT];

export const API_CONFIG = {
  // Base URL for API requests
  BASE_URL: currentEnv.BASE_URL,
  BASE_URLS: currentEnv.BASE_URLS || null, // Array for auto-detection (testing env only)
  WS_URL: currentEnv.WS_URL,

  TIMEOUT: 10000, // 10 seconds
  // An intel call may make an outbound fetch to a third-party site, so it can
  // legitimately take longer than a CRUD call against our own database.
  INTEL_TIMEOUT: 30000, // 30 seconds
  
  ENDPOINTS: {
    // Auth endpoints
    LOGIN: '/api/v1/auth/login',
    REGISTER: '/api/v1/auth/register',
    REFRESH: '/api/v1/auth/refresh',
    ME: '/api/v1/auth/me',
    LOGOUT: '/api/v1/auth/logout',
    SWITCH_ROLE: '/api/v1/auth/switch-role',
    VERIFY_EMAIL: '/api/v1/auth/verify-email',
    RESEND_VERIFICATION: '/api/v1/auth/resend-verification',
    FORGOT_PASSWORD: '/api/v1/auth/forgot-password',
    RESET_PASSWORD: '/api/v1/auth/reset-password',
    
    // User endpoints
    USER_PROFILE: '/api/v1/users/me/profile',
    USER_ADDRESSES: '/api/v1/users/me/addresses',
    CHANGE_PASSWORD: '/api/v1/users/me/change-password',
    
    // Product endpoints
    PRODUCTS: '/api/v1/products',
    CATEGORIES: '/api/v1/products/categories',
    
    // Order endpoints
    ORDERS: '/api/v1/orders',
    CART: '/api/v1/cart',
    
    // Chat endpoints
    CHAT_ROOMS: '/api/v1/chat/rooms',
    CHAT_MESSAGES: '/api/v1/chat/rooms', // Use: ${CHAT_MESSAGES}/${roomId}/messages
    
    // Review endpoints
    REVIEWS: '/api/v1/reviews',

    // Seller endpoints (routes to seller-service via Traefik)
    SELLER: '/api/v1/seller', // Base seller path for upload-image, bulk-operations
    SELLER_DASHBOARD: '/api/v1/seller/dashboard',
    SELLER_PRODUCTS: '/api/v1/seller/products',
    SELLER_ANALYTICS: '/api/v1/seller',
    SELLER_PROFILE: '/api/v1/seller/profile',
    SELLER_CATEGORIES: '/api/v1/seller/categories',

    // Intel endpoints (routes to intel-service via Traefik).
    // Price intelligence lands here in phase 1; see
    // docs/ai-features/05-price-intelligence.md section 10.
    INTEL: '/api/v1/intel',

    // Order fulfillment endpoints (seller order management)
    SELLER_FULFILLMENT: '/api/v1/seller/fulfillment/orders',  // For GET orders
    ORDER_FULFILLMENT: '/api/v1/order-fulfillment/orders',    // For status updates
  },
};

// Export BASE_URL for backward compatibility
export const API_BASE_URL = API_CONFIG.BASE_URL;

export const APP_CONFIG = {
  APP_NAME: 'Mercai',
  VERSION: '1.0.0',
  
  // Feature flags
  FEATURES: {
    CHAT_ENABLED: true,
    PUSH_NOTIFICATIONS: true,
    OFFLINE_MODE: false,
  },
  
  // UI Configuration
  UI: {
    SPLASH_DURATION: 2000,
    TOAST_DURATION: 3000,
    LOADING_TIMEOUT: 30000,
  },
  
  // Pagination
  PAGINATION: {
    DEFAULT_PAGE_SIZE: 20,
    MAX_PAGE_SIZE: 100,
  },
  
  // File uploads
  UPLOAD: {
    MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
    MAX_IMAGES_PER_PRODUCT: 6,
    ALLOWED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/webp'],
  },
};