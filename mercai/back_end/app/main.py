from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import auth, users, products, orders, chat, reviews, cart, seller_dashboard, order_fulfillment, seller_analytics, seller_profile
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mercai API",
    description="Backend API for Mercai mobile application",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

@app.on_event("startup")
async def startup_event():
    """Initialize database tables and test data on application startup"""
    try:
        from app.utils.database_init import create_tables
        create_tables()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization: {e}")
        logger.info("Tables may already exist, continuing...")

    # Initialize test data (ensures customer_a account exists with correct password)
    try:
        from app.utils.init_test_data import initialize_test_data
        initialize_test_data()
    except Exception as e:
        logger.warning(f"Test data initialization: {e}")
        logger.info("Test data may not be needed in production, continuing...")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(cart.router, prefix="/api/v1", tags=["cart"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
app.include_router(seller_dashboard.router, prefix="/api/v1/seller", tags=["seller-dashboard"])
app.include_router(order_fulfillment.router, prefix="/api/v1/seller/fulfillment", tags=["order-fulfillment"])
app.include_router(seller_analytics.router, prefix="/api/v1/seller/analytics", tags=["seller-analytics"])
app.include_router(seller_profile.router, prefix="/api/v1/seller/profile", tags=["seller-profile"])

@app.get("/")
async def root():
    return {"message": "Mercai API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    from app.core.cache import cache
    cache_status = cache.health_check()
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "cache": cache_status
    }

# API v1 root and health endpoints
@app.get("/api/v1")
async def api_v1_root():
    return {"message": "Mercai API v1", "version": "1.0.0", "docs": "/api/docs"}

@app.get("/api/v1/health")
async def api_v1_health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT, "version": "1.0.0"}