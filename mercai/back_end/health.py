"""
Health check endpoint for monitoring
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict
import datetime

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict:
    """
    Health check endpoint for monitoring service status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "service": "Mercai API",
        "version": "1.0.0"
    }


@router.get("/health/db")
async def database_health_check(db: Session = Depends(get_db)) -> Dict:
    """
    Check database connectivity
    """
    try:
        # Execute a simple query
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }