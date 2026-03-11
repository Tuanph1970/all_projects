"""
Solution router — thin HTTP adapter.

All business logic lives in src/application/solution/use_cases.py.
"""
import base64
import io
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from PIL import Image
from pydantic import BaseModel, Field

from ...application.solution.use_cases import OCRAndSolveUseCase, SolveProblemUseCase
from ...api.dependencies import get_ocr_and_solve_use_case, get_solve_problem_use_case
from ...api.exceptions import ModelNotLoadedException

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class SolutionRequest(BaseModel):
    problem: str = Field(..., description="Mathematical problem text")
    context: Optional[Dict[str, Any]] = Field(default=None)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SolutionResponse(BaseModel):
    success: bool
    solution: str
    steps: List[str]
    final_answer: str
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]
    request_id: Optional[str] = None


class OCRSolutionRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image")
    ocr_confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    solution_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    use_mathematical_ocr: bool = Field(default=True)


class OCRSolutionResponse(BaseModel):
    success: bool
    extracted_text: str
    ocr_confidence: float
    solution: str
    solution_steps: List[str]
    final_answer: str
    solution_confidence: float
    total_processing_time: float
    metadata: Dict[str, Any]
    request_id: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/solve", response_model=SolutionResponse)
async def solve_problem(
    request: Request,
    solution_request: SolutionRequest,
    use_case: SolveProblemUseCase = Depends(get_solve_problem_use_case),
):
    """Solve a mathematical problem supplied as text."""
    request_id = getattr(request.state, "request_id", None)

    try:
        result = use_case.execute(
            problem=solution_request.problem,
            context=solution_request.context or {},
            confidence_threshold=solution_request.confidence_threshold,
        )
    except ModelNotLoadedException as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    result.metadata.update({"request_id": request_id})
    logger.info(
        f"Problem solved in {result.processing_time:.3f}s "
        f"with confidence {result.confidence:.3f}"
    )
    return SolutionResponse(
        success=result.success,
        solution=result.solution,
        steps=result.steps,
        final_answer=result.final_answer,
        confidence=result.confidence,
        processing_time=result.processing_time,
        metadata=result.metadata,
        request_id=request_id,
    )


@router.post("/ocr-solve", response_model=OCRSolutionResponse)
async def ocr_and_solve(
    request: Request,
    ocr_solution_request: OCRSolutionRequest,
    use_case: OCRAndSolveUseCase = Depends(get_ocr_and_solve_use_case),
):
    """Extract a mathematical problem from an image and solve it."""
    request_id = getattr(request.state, "request_id", None)
    start_time = time.time()

    try:
        image_data = base64.b64decode(ocr_solution_request.image_base64)
        image = Image.open(io.BytesIO(image_data))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {exc}")

    try:
        pipeline = use_case.execute(
            image=image,
            ocr_confidence_threshold=ocr_solution_request.ocr_confidence_threshold,
            solution_confidence_threshold=ocr_solution_request.solution_confidence_threshold,
            use_mathematical_ocr=ocr_solution_request.use_mathematical_ocr,
        )
    except ModelNotLoadedException as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    ocr = pipeline["ocr_result"]
    sol = pipeline["solution_result"]
    total_time = time.time() - start_time

    if sol is None:
        return OCRSolutionResponse(
            success=False,
            extracted_text=ocr.extracted_text,
            ocr_confidence=ocr.confidence,
            solution="OCR failed to extract usable text",
            solution_steps=[],
            final_answer="",
            solution_confidence=0.0,
            total_processing_time=total_time,
            metadata={"error": "OCR extraction failed", "request_id": request_id},
            request_id=request_id,
        )

    combined_metadata = {
        "pipeline": "ocr_and_solve",
        "ocr_processing_time": ocr.processing_time,
        "solution_processing_time": sol.processing_time,
        "request_id": request_id,
        "ocr_metadata": ocr.metadata,
        "solution_metadata": sol.metadata,
    }

    logger.info(f"OCR+Solution pipeline completed in {total_time:.3f}s")
    return OCRSolutionResponse(
        success=sol.success,
        extracted_text=ocr.extracted_text,
        ocr_confidence=ocr.confidence,
        solution=sol.solution,
        solution_steps=sol.steps,
        final_answer=sol.final_answer,
        solution_confidence=sol.confidence,
        total_processing_time=total_time,
        metadata=combined_metadata,
        request_id=request_id,
    )


@router.get("/models")
async def list_solution_models(request: Request):
    """List solution models registered in the model registry."""
    registry = request.app.state.model_manager.get_registry()
    models = []
    for name in registry.list_models():
        model = registry.get_model(name)
        if model and hasattr(model, "get_model_info"):
            info = model.get_model_info()
            if info.get("model_type") == "solution":
                models.append({"name": name, "info": info})
    return {"models": models}
