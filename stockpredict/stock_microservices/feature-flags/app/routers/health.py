"""
Health Check Endpoints
"""
from fastapi import APIRouter, Request
from datetime import datetime

router = APIRouter()


@router.get("/live")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/ready")
async def readiness(request: Request):
    """Kubernetes readiness probe"""
    try:
        # Check Redis connection
        await request.app.state.flag_store.redis.ping()

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "redis": "connected"
            }
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "redis": f"error: {str(e)}"
            }
        }
