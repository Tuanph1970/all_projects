"""
Auth Service - Handles authentication, user management, and authorization
"""
import sys
sys.path.insert(0, '/app')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config import settings
from shared.database import init_db
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Auth Service",
    description="Authentication and user management service for Mercai",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_db()
        logger.info("Auth Service: Database initialized successfully")
    except Exception as e:
        logger.warning(f"Auth Service: Database initialization: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.routers import auth, users

app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

@app.get("/")
async def root():
    return {"service": "Auth Service", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    from shared.cache import cache
    cache_status = cache.health_check()
    return {
        "status": "healthy",
        "service": "auth-service",
        "environment": settings.ENVIRONMENT,
        "cache": cache_status
    }
