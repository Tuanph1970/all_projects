"""
Admin API Endpoints for Feature Flags
Protected endpoints for managing flags and cutover phases
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Header, Query
from pydantic import BaseModel

from app.config import settings, CUTOVER_PHASES
from app.models.flag import (
    FeatureFlag, FlagUpdate, BulkUpdateRequest, BulkUpdateResponse,
    AuditLogEntry
)

router = APIRouter()


def verify_admin_key(api_key: str = Header(..., alias="X-Admin-Key")):
    """Verify admin API key"""
    if api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    return api_key


class CreateFlagRequest(BaseModel):
    """Request to create a new flag"""
    name: str
    enabled: bool = True
    percentage: int = 0
    description: str = ""
    service: Optional[str] = None
    django_path: Optional[str] = None
    microservice_path: Optional[str] = None


@router.post("/flags", response_model=FeatureFlag)
async def create_flag(
    flag_request: CreateFlagRequest,
    request: Request,
    api_key: str = Header(..., alias="X-Admin-Key")
):
    """Create a new feature flag"""
    verify_admin_key(api_key)

    # Check if flag exists
    existing = await request.app.state.flag_store.get_flag(flag_request.name)
    if existing:
        raise HTTPException(status_code=409, detail="Flag already exists")

    flag = FeatureFlag(**flag_request.model_dump())
    await request.app.state.flag_store.set_flag(flag)

    return flag


@router.put("/flags/{flag_name}", response_model=FeatureFlag)
async def update_flag(
    flag_name: str,
    update: FlagUpdate,
    request: Request,
    api_key: str = Header(..., alias="X-Admin-Key")
):
    """Update a feature flag"""
    verify_admin_key(api_key)

    flag = await request.app.state.flag_store.update_flag(
        flag_name,
        update,
        actor=f"admin:{api_key[:8]}..."
    )

    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    # Update metrics
    request.app.state.metrics.update_flag_percentage(flag_name, flag.percentage)

    return flag


@router.delete("/flags/{flag_name}")
async def delete_flag(
    flag_name: str,
    request: Request,
    api_key: str = Header(..., alias="X-Admin-Key")
):
    """Delete a feature flag"""
    verify_admin_key(api_key)

    deleted = await request.app.state.flag_store.delete_flag(
        flag_name,
        actor=f"admin:{api_key[:8]}..."
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Flag not found")

    return {"deleted": flag_name, "timestamp": datetime.utcnow().isoformat()}


@router.post("/phases/apply", response_model=BulkUpdateResponse)
async def apply_phase(
    phase_request: BulkUpdateRequest,
    request: Request,
    api_key: str = Header(..., alias="X-Admin-Key")
):
    """Apply a cutover phase to all flags"""
    verify_admin_key(api_key)

    if phase_request.phase not in CUTOVER_PHASES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown phase: {phase_request.phase}"
        )

    # Get current phase for metrics
    current_phase = await request.app.state.flag_store.get_current_phase()

    try:
        changes = await request.app.state.flag_store.apply_phase(
            phase_request.phase,
            actor=f"admin:{api_key[:8]}...",
            dry_run=phase_request.dry_run
        )

        # Update metrics
        if not phase_request.dry_run:
            request.app.state.metrics.update_current_phase(phase_request.phase)
            if current_phase:
                request.app.state.metrics.record_phase_transition(
                    current_phase,
                    phase_request.phase
                )

            # Update flag percentages in metrics
            for change in changes:
                request.app.state.metrics.update_flag_percentage(
                    change["flag"],
                    change["new_percentage"]
                )

        return BulkUpdateResponse(
            success=True,
            phase=phase_request.phase,
            changes=changes,
            dry_run=phase_request.dry_run,
            applied_at=datetime.utcnow() if not phase_request.dry_run else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flags/{flag_name}/percentage")
async def set_flag_percentage(
    flag_name: str,
    percentage: int = Query(..., ge=0, le=100),
    request: Request = None,
    api_key: str = Header(..., alias="X-Admin-Key")
):
    """Quickly set a flag's traffic percentage"""
    verify_admin_key(api_key)

    flag = await request.app.state.flag_store.update_flag(
        flag_name,
        FlagUpdate(percentage=percentage),
        actor=f"admin:{api_key[:8]}..."
    )

    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    request.app.state.metrics.update_flag_percentage(flag_name, percentage)

    return {
        "flag": flag_name,
        "percentage": percentage,
        "updated_at": datetime.utcnow().isoformat()
    }


@router.post("/rollback")
async def emergency_rollback(
    request: Request,
    reason: str = Query(..., description="Reason for rollback"),
    api_key: str = Header(..., alias="X-Admin-Key")
):
    """Emergency rollback to 100% Django"""
    verify_admin_key(api_key)

    current_phase = await request.app.state.flag_store.get_current_phase()

    changes = await request.app.state.flag_store.apply_phase(
        "rollback",
        actor=f"admin:{api_key[:8]}... (EMERGENCY)",
        dry_run=False
    )

    # Update metrics
    request.app.state.metrics.update_current_phase("rollback")
    if current_phase:
        request.app.state.metrics.record_phase_transition(current_phase, "rollback")

    for change in changes:
        request.app.state.metrics.update_flag_percentage(change["flag"], 0)

    return {
        "status": "rolled_back",
        "previous_phase": current_phase,
        "reason": reason,
        "changes": changes,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/audit-log")
async def get_audit_log(
    request: Request,
    limit: int = Query(100, le=1000),
    api_key: str = Header(..., alias="X-Admin-Key")
):
    """Get audit log entries"""
    verify_admin_key(api_key)

    entries = await request.app.state.flag_store.get_audit_log(limit)
    return {
        "entries": [e.model_dump() for e in entries],
        "count": len(entries)
    }


@router.get("/prometheus")
async def prometheus_metrics(request: Request):
    """Prometheus metrics endpoint"""
    metrics = request.app.state.metrics.get_prometheus_metrics()
    from fastapi.responses import Response
    return Response(content=metrics, media_type="text/plain")
