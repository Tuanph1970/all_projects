# Chat Service - Real-time Messaging Microservice
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from sqlalchemy import text
from shared.database import engine, Base
from shared.config import settings

from app.routers import chat

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Chat Service...")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    yield

    # Shutdown
    logger.info("Shutting down Chat Service...")

app = FastAPI(
    title="Chat Service",
    description="Real-time Messaging for Mercai",
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
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

@app.get("/health")
def health_check():
    """Health check endpoint for container orchestration"""
    from app.services.websocket_manager import manager

    health_status = {
        "status": "healthy",
        "service": "chat-service",
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

    # WebSocket stats
    health_status["websocket"] = {
        "active_connections": len(manager.active_connections),
        "online_users": len(manager.get_online_users())
    }

    return health_status

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "Chat Service",
        "status": "running",
        "endpoints": {
            "chat": "/api/v1/chat",
            "websocket": "/api/v1/chat/ws/{user_id}",
            "health": "/health"
        }
    }
