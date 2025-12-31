# Order Service - Cart & Orders Microservice
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from sqlalchemy import text
from shared.database import engine, Base
from shared.config import settings

from app.routers import orders, cart

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Order Service...")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    yield

    # Shutdown
    logger.info("Shutting down Order Service...")

app = FastAPI(
    title="Order Service",
    description="Cart and Order Management for Ceramic Marketplace",
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
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(cart.router, prefix="/api/v1/cart", tags=["cart"])

@app.get("/health")
def health_check():
    """Health check endpoint for container orchestration"""
    health_status = {
        "status": "healthy",
        "service": "order-service",
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

    return health_status

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "Order Service",
        "status": "running",
        "endpoints": {
            "orders": "/api/v1/orders",
            "cart": "/api/v1/cart",
            "health": "/health"
        }
    }
