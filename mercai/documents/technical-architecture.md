# Mercai Technical Architecture

## System Architecture Overview

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Native  │    │    FastAPI      │    │      MySQL      │
│   Mobile App    │◄──►│   Backend API   │◄──►│    Database     │
│                 │    │                 │    │                 │
│ • State Mgmt    │    │ • JWT Auth      │    │ • Relational    │
│ • Navigation    │    │ • WebSocket     │    │ • ACID          │
│ • UI Components │    │ • File Upload   │    │ • Indexing      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │
        │              ┌─────────────────┐
        │              │  Local Storage  │
        └──────────────┤  Image Files    │
                       │                 │
                       └─────────────────┘
```

## Frontend Architecture (React Native)

### Component Structure
```
src/
├── components/
│   ├── common/          # Reusable UI components
│   ├── product/         # Product-specific components
│   ├── seller/          # Seller dashboard components
│   └── chat/            # Chat interface components
├── screens/
│   ├── auth/            # Authentication screens
│   ├── customer/        # Customer-focused screens
│   ├── seller/          # Seller-focused screens
│   └── shared/          # Shared screens
├── navigation/
│   ├── CustomerStack.js # Customer navigation
│   ├── SellerStack.js   # Seller navigation
│   └── RootNavigator.js # Main navigation container
├── store/
│   ├── auth/            # Authentication state
│   ├── products/        # Product catalog state
│   ├── cart/            # Shopping cart state
│   └── chat/            # Chat state management
├── services/
│   ├── api/             # API client configuration
│   ├── auth/            # Authentication services
│   └── websocket/       # WebSocket connection
└── utils/
    ├── constants/       # App constants
    ├── helpers/         # Utility functions
    └── validators/      # Input validation
```

### State Management Strategy
- **Redux Toolkit** for complex state (cart, product catalog)
- **Context API** for simple state (theme, user preferences)
- **AsyncStorage** for persistence (user session, cart backup)
- **React Query** for server state management and caching

### Navigation Architecture
```
RootNavigator
├── AuthStack (not authenticated)
│   ├── LoginScreen
│   ├── RegisterScreen
│   └── ForgotPasswordScreen
└── MainStack (authenticated)
    ├── CustomerStack
    │   ├── HomeScreen
    │   ├── ProductListScreen
    │   ├── ProductDetailScreen
    │   ├── CartScreen
    │   └── CheckoutScreen
    ├── SellerStack
    │   ├── SellerDashboard
    │   ├── ProductManagement
    │   ├── OrderManagement
    │   └── Analytics
    ├── SharedStack
    │   ├── ChatScreen
    │   ├── ProfileScreen
    │   └── SettingsScreen
    └── RoleSwitcher
```

## Backend Architecture (FastAPI)

### API Structure
```
app/
├── api/
│   └── v1/
│       ├── auth.py          # Authentication endpoints
│       ├── products.py      # Product CRUD operations
│       ├── orders.py        # Order management
│       ├── users.py         # User profile management
│       ├── chat.py          # Chat functionality
│       ├── reviews.py       # Review system
│       ├── categories.py    # Category management
│       └── seller.py        # Seller-specific endpoints
├── core/
│   ├── config.py           # Configuration management
│   ├── security.py         # Security utilities
│   ├── database.py         # Database connection
│   └── auth.py             # Authentication logic
├── models/
│   ├── user.py             # User-related models
│   ├── product.py          # Product models
│   ├── order.py            # Order models
│   ├── chat.py             # Chat models
│   └── review.py           # Review models
├── schemas/
│   ├── user.py             # Pydantic schemas for users
│   ├── product.py          # Pydantic schemas for products
│   ├── order.py            # Pydantic schemas for orders
│   └── chat.py             # Pydantic schemas for chat
├── services/
│   ├── auth_service.py     # Authentication business logic
│   ├── product_service.py  # Product business logic
│   ├── order_service.py    # Order processing logic
│   ├── chat_service.py     # Chat functionality
│   └── notification_service.py # Push notifications
├── utils/
│   ├── dependencies.py     # FastAPI dependencies
│   ├── validators.py       # Input validation
│   └── helpers.py          # Utility functions
└── websocket/
    ├── chat_handler.py     # Chat WebSocket handler
    └── notification_handler.py # Real-time notifications
```

### API Endpoint Structure
```
/api/v1/
├── auth/
│   ├── POST /register      # User registration
│   ├── POST /login         # User authentication
│   ├── POST /refresh       # Token refresh
│   └── POST /logout        # User logout
├── products/
│   ├── GET /               # List products with pagination
│   ├── GET /{id}           # Get product details
│   ├── POST /              # Create product (seller only)
│   ├── PUT /{id}           # Update product (seller only)
│   ├── DELETE /{id}        # Delete product (seller only)
│   ├── GET /featured       # Featured products
│   ├── GET /search         # Search products
│   └── POST /filter        # Advanced filtering
├── orders/
│   ├── GET /               # List user orders
│   ├── GET /{id}           # Get order details
│   ├── POST /              # Create new order
│   └── PUT /{id}/status    # Update order status
├── cart/
│   ├── GET /               # Get cart contents
│   ├── POST /add           # Add item to cart
│   ├── PUT /update/{id}    # Update cart item
│   └── DELETE /remove/{id} # Remove cart item
├── chat/
│   ├── GET /conversations  # List conversations
│   ├── GET /messages/{id}  # Get conversation messages
│   └── POST /send          # Send message
├── reviews/
│   ├── GET /product/{id}   # Get product reviews
│   ├── POST /product/{id}  # Add product review
│   └── PUT /{id}           # Update review
└── seller/
    ├── GET /dashboard      # Seller dashboard data
    ├── GET /analytics      # Performance analytics
    └── GET /orders         # Seller order management
```

## Database Schema Design

### Core Tables

#### Users Table
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('customer', 'seller', 'dual') DEFAULT 'customer',
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### User Profiles Table
```sql
CREATE TABLE user_profiles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    avatar_url VARCHAR(500),
    store_name VARCHAR(255),
    store_description TEXT,
    location VARCHAR(255),
    response_time_hours INT DEFAULT 24,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Categories Table
```sql
CREATE TABLE categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    parent_id INT,
    description TEXT,
    icon_url VARCHAR(500),
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
);
```

#### Products Table
```sql
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    seller_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category_id INT NOT NULL,
    subcategory_id INT,
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2),
    quantity INT DEFAULT 0,
    sku VARCHAR(100),
    condition_type ENUM('new', 'like_new', 'good', 'fair', 'refurbished') NOT NULL,
    dimensions_length DECIMAL(8,2),
    dimensions_width DECIMAL(8,2),
    dimensions_height DECIMAL(8,2),
    weight DECIMAL(8,2),
    material VARCHAR(255),
    color VARCHAR(100),
    shipping_cost DECIMAL(8,2) DEFAULT 0,
    processing_time_days INT DEFAULT 3,
    return_policy TEXT,
    views_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (subcategory_id) REFERENCES categories(id),
    INDEX idx_seller (seller_id),
    INDEX idx_category (category_id),
    INDEX idx_price (price),
    INDEX idx_active (is_active)
);
```

#### Product Images Table
```sql
CREATE TABLE product_images (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    alt_text VARCHAR(255),
    sort_order INT DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    INDEX idx_product (product_id)
);
```

#### Orders Table
```sql
CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded') DEFAULT 'pending',
    subtotal DECIMAL(10,2) NOT NULL,
    shipping_cost DECIMAL(8,2) DEFAULT 0,
    tax_amount DECIMAL(8,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    shipping_address_id INT NOT NULL,
    tracking_number VARCHAR(255),
    shipped_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id),
    FOREIGN KEY (shipping_address_id) REFERENCES shipping_addresses(id),
    INDEX idx_customer (customer_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
);
```

#### Order Items Table
```sql
CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    seller_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (seller_id) REFERENCES users(id),
    INDEX idx_order (order_id),
    INDEX idx_seller (seller_id)
);
```

#### Cart Items Table
```sql
CREATE TABLE cart_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_product (user_id, product_id),
    INDEX idx_user (user_id)
);
```

#### Reviews Table
```sql
CREATE TABLE reviews (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    user_id INT NOT NULL,
    order_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    content TEXT,
    verified_purchase BOOLEAN DEFAULT TRUE,
    helpful_count INT DEFAULT 0,
    unhelpful_count INT DEFAULT 0,
    seller_response TEXT,
    seller_response_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    UNIQUE KEY unique_user_product_order (user_id, product_id, order_id),
    INDEX idx_product (product_id),
    INDEX idx_rating (rating)
);
```

#### Chat System Tables
```sql
CREATE TABLE conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    seller_id INT NOT NULL,
    product_id INT,
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL,
    UNIQUE KEY unique_customer_seller_product (customer_id, seller_id, product_id),
    INDEX idx_customer (customer_id),
    INDEX idx_seller (seller_id)
);

CREATE TABLE messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    sender_id INT NOT NULL,
    message_type ENUM('text', 'image', 'product_reference') DEFAULT 'text',
    content TEXT NOT NULL,
    image_url VARCHAR(500),
    product_reference_id INT,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_reference_id) REFERENCES products(id) ON DELETE SET NULL,
    INDEX idx_conversation (conversation_id),
    INDEX idx_created (created_at)
);
```

#### Shipping Addresses Table
```sql
CREATE TABLE shipping_addresses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id)
);
```

## API Architecture Details

### Authentication Flow
```
1. User Registration/Login → JWT Token Generation
2. Token Storage in AsyncStorage
3. Automatic Token Refresh (before expiration)
4. Token Validation Middleware on Protected Routes
5. Role-based Route Protection
```

### API Design Patterns
- **RESTful Design**: Standard HTTP methods and status codes
- **Resource-Based URLs**: /api/v1/products/{id}/reviews
- **Pagination**: Cursor-based for performance
- **Rate Limiting**: Per-user and per-endpoint limits
- **Error Handling**: Consistent error response format
- **Caching**: Redis for frequently accessed data

### WebSocket Architecture
```
WebSocket Connections:
├── /ws/chat/{user_id}          # Chat messages
├── /ws/notifications/{user_id}  # Real-time notifications
└── /ws/cart/{user_id}          # Cart updates

Message Types:
├── chat_message    # Direct messages between users
├── order_update    # Order status changes
├── stock_update    # Product stock changes
└── system_alert    # System notifications
```

## Security Architecture

### Authentication & Authorization
- **JWT Tokens**: Access and refresh token strategy
- **Password Security**: bcrypt hashing with salt
- **Role-Based Access**: Customer/Seller/Dual permissions
- **API Rate Limiting**: Prevent abuse and DDoS
- **Input Validation**: Pydantic schemas for all inputs

### Data Protection
- **Encryption**: AES-256 for sensitive data
- **SSL/TLS**: All communications encrypted
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Input sanitization
- **CSRF Protection**: Token-based CSRF prevention

### Security Monitoring
- **Audit Logging**: All sensitive operations logged
- **Failed Login Tracking**: Brute force protection
- **Suspicious Activity Detection**: Anomaly detection
- **Data Breach Prevention**: Access logging and monitoring

## Performance Architecture

### Database Optimization
```sql
-- Key Indexes for Performance
CREATE INDEX idx_products_search ON products(title, description);
CREATE INDEX idx_products_price_category ON products(category_id, price);
CREATE INDEX idx_orders_customer_date ON orders(customer_id, created_at);
CREATE INDEX idx_messages_conversation_date ON messages(conversation_id, created_at);
```

### Caching Strategy
- **Application Cache**: Redis for session data and frequent queries
- **Database Cache**: Query result caching for product listings
- **Image Cache**: CDN for product images and user avatars
- **Mobile Cache**: AsyncStorage for offline capability

### Performance Targets
- **API Response**: <200ms average
- **Database Queries**: <50ms for simple queries
- **Image Loading**: <2 seconds for high-resolution images
- **App Startup**: <3 seconds cold start
- **Search Results**: <1 second response time

## File Storage Architecture

### Image Management
```
Local Storage Structure:
uploads/
├── products/
│   ├── {product_id}/
│   │   ├── original/     # Original uploaded images
│   │   ├── medium/       # 800x600 optimized
│   │   └── thumbnail/    # 200x200 thumbnails
├── users/
│   └── avatars/          # User profile images
└── chat/
    └── attachments/      # Chat image attachments
```

### File Processing Pipeline
1. **Upload Validation**: File type, size, and content validation
2. **Image Processing**: Multiple size generation (original, medium, thumbnail)
3. **Storage**: Local filesystem with organized directory structure
4. **Serving**: FastAPI static file serving with caching headers
5. **Cleanup**: Orphaned file detection and removal

## Real-time Communication

### WebSocket Implementation
- **Connection Management**: Per-user connection tracking
- **Message Routing**: Efficient message delivery to target users
- **Presence System**: Online/offline status tracking
- **Typing Indicators**: Real-time typing notifications
- **Connection Recovery**: Automatic reconnection with message queue

### Push Notifications
- **Local Notifications**: React Native local notification system
- **Message Notifications**: New chat messages
- **Order Notifications**: Status updates for buyers and sellers
- **Marketing Notifications**: Promotional messages (opt-in)

## Scalability Considerations

### Horizontal Scaling Strategy
- **Database Sharding**: User-based sharding strategy
- **Load Balancing**: Multiple FastAPI instances
- **CDN Integration**: Image and static asset delivery
- **Microservices**: Future migration path for high-load components

### Performance Monitoring
- **Application Metrics**: Response times, error rates, throughput
- **Database Metrics**: Query performance, connection pool usage
- **Infrastructure Metrics**: CPU, memory, disk usage
- **User Experience Metrics**: App performance, crash rates

## Development & Deployment

### Environment Configuration
- **Development**: Local MySQL, local file storage
- **Staging**: Cloud database, cloud storage simulation
- **Production**: Optimized cloud infrastructure

### CI/CD Pipeline
```
Code Commit → Automated Testing → Build → Deploy
├── Unit Tests (80% coverage)
├── Integration Tests
├── Security Scans
├── Performance Tests
└── Deployment to Environment
```

### Monitoring & Logging
- **Application Logs**: Structured logging with correlation IDs
- **Error Tracking**: Sentry for error monitoring and alerting
- **Performance Monitoring**: APM for response time tracking
- **Business Metrics**: Custom dashboards for KPI tracking

---

**Architecture Status**: Design Complete  
**Next Steps**: Development environment setup and team alignment