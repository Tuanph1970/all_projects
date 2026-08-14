# Product Service - Catalog & Search Microservice
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from sqlalchemy import text
from shared.database import engine, Base
from shared.config import settings
from shared.cache import cache

from app.routers import products, reviews

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Product Service...")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    # Initialize cache
    if cache.client:
        logger.info("Redis cache connection established")
    else:
        logger.warning("Redis cache not available - running without cache")

    yield

    # Shutdown
    logger.info("Shutting down Product Service...")

app = FastAPI(
    title="Product Service",
    description="Catalog, Search, and Review Management for Mercai",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])

@app.get("/health")
def health_check():
    """Health check endpoint for container orchestration"""
    health_status = {
        "status": "healthy",
        "service": "product-service",
        "version": "1.0.0"
    }

    # Check database connection
    try:
        from shared.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check cache connection
    try:
        if cache.client and cache.client.ping():
            health_status["cache"] = "connected"
        else:
            health_status["cache"] = "not available"
    except Exception as e:
        health_status["cache"] = f"error: {str(e)}"

    return health_status

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "Product Service",
        "status": "running",
        "endpoints": {
            "products": "/api/v1/products",
            "reviews": "/api/v1/reviews",
            "health": "/health"
        }
    }
