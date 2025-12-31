"""
Feature Flag API Endpoints
"""
import time
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel

from app.models.flag import (
    FeatureFlag, FlagUpdate, FlagEvaluation, EvaluationContext,
    CutoverStatus
)
from app.config import CUTOVER_PHASES

router = APIRouter()


class EvaluateRequest(BaseModel):
    """Request to evaluate a flag"""
    user_id: Optional[str] = None
    user_groups: List[str] = []
    request_id: Optional[str] = None


@router.get("/", response_model=dict)
async def list_flags(request: Request):
    """List all feature flags"""
    flags = await request.app.state.flag_store.get_all_flags()
    return {
        "flags": {name: flag.model_dump() for name, flag in flags.items()},
        "count": len(flags),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/{flag_name}", response_model=FeatureFlag)
async def get_flag(flag_name: str, request: Request):
    """Get a specific feature flag"""
    flag = await request.app.state.flag_store.get_flag(flag_name)
    if not flag:
        raise HTTPException(status_code=404, detail=f"Flag '{flag_name}' not found")
    return flag


@router.post("/{flag_name}/evaluate", response_model=FlagEvaluation)
async def evaluate_flag(
    flag_name: str,
    eval_request: EvaluateRequest,
    request: Request
):
    """Evaluate a feature flag for routing decision"""
    start_time = time.time()

    context = EvaluationContext(
        user_id=eval_request.user_id,
        user_groups=eval_request.user_groups,
        request_id=eval_request.request_id
    )

    result = await request.app.state.flag_store.evaluate_flag(flag_name, context)

    # Record metrics
    evaluation_time = time.time() - start_time
    request.app.state.metrics.record_evaluation(
        flag_name=flag_name,
        use_microservice=result.use_microservice,
        evaluation_time=evaluation_time
    )

    return result


@router.post("/evaluate-all")
async def evaluate_all_flags(
    eval_request: EvaluateRequest,
    request: Request
):
    """Evaluate all feature flags for a request"""
    flags = await request.app.state.flag_store.get_all_flags()
    context = EvaluationContext(
        user_id=eval_request.user_id,
        user_groups=eval_request.user_groups,
        request_id=eval_request.request_id
    )

    results = {}
    for flag_name in flags.keys():
        result = await request.app.state.flag_store.evaluate_flag(flag_name, context)
        results[flag_name] = result.model_dump()

    return {
        "evaluations": results,
        "context": context.model_dump(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/status/current", response_model=CutoverStatus)
async def get_cutover_status(request: Request):
    """Get current cutover status"""
    current_phase = await request.app.state.flag_store.get_current_phase()
    current_phase = current_phase or "shadow"

    flags = await request.app.state.flag_store.get_all_flags()
    phase_info = CUTOVER_PHASES.get(current_phase, CUTOVER_PHASES["shadow"])

    return CutoverStatus(
        current_phase=current_phase,
        phase_info=phase_info,
        flags=flags,
        health_status="healthy",
        last_updated=datetime.utcnow()
    )


@router.get("/phases/list")
async def list_phases():
    """List all available cutover phases"""
    return {
        "phases": CUTOVER_PHASES,
        "count": len(CUTOVER_PHASES)
    }


@router.get("/metrics/evaluations")
async def get_evaluation_metrics(request: Request):
    """Get flag evaluation statistics"""
    stats = request.app.state.metrics.get_evaluation_stats()
    return {
        "statistics": stats,
        "timestamp": datetime.utcnow().isoformat()
    }
