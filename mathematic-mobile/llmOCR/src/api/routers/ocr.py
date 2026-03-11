"""
OCR router — thin HTTP adapter.

All business logic lives in src/application/ocr/use_cases.py.
This module only:
  1. Parses HTTP request data
  2. Invokes the appropriate use case
  3. Formats the HTTP response
"""
import base64
import io
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from loguru import logger
from PIL import Image
from pydantic import BaseModel, Field

from ...application.ocr.use_cases import BatchExtractTextUseCase, ExtractTextUseCase
from ...api.dependencies import get_batch_extract_text_use_case, get_extract_text_use_case
from ...api.exceptions import ModelNotLoadedException

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class OCRRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image data")
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    use_mathematical_model: bool = Field(default=True)


class OCRResponse(BaseModel):
    success: bool
    extracted_text: str
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]
    request_id: Optional[str] = None


class BatchOCRRequest(BaseModel):
    images_base64: List[str] = Field(..., min_length=1, max_length=10)
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    use_mathematical_model: bool = Field(default=True)


class BatchOCRResponse(BaseModel):
    results: List[OCRResponse]
    total_processing_time: float
    successful_count: int
    failed_count: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/extract", response_model=OCRResponse)
async def extract_text_from_image(
    request: Request,
    file: UploadFile = File(...),
    confidence_threshold: float = 0.8,
    use_mathematical_model: bool = True,
    use_case: ExtractTextUseCase = Depends(get_extract_text_use_case),
):
    """Extract mathematical text from an uploaded image file."""
    request_id = getattr(request.state, "request_id", None)
    start_time = time.time()

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_data = await file.read()
    if len(image_data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10 MB limit")

    image = Image.open(io.BytesIO(image_data))

    try:
        result = use_case.execute(
            image,
            confidence_threshold=confidence_threshold,
            use_mathematical_model=use_mathematical_model,
            source_metadata={
                "file_name": file.filename,
                "file_size_bytes": len(image_data),
                "content_type": file.content_type,
                "request_id": request_id,
            },
        )
    except ModelNotLoadedException as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    logger.info(f"OCR completed for {file.filename} in {result.processing_time:.3f}s")
    return OCRResponse(
        success=result.success,
        extracted_text=result.extracted_text,
        confidence=result.confidence,
        processing_time=result.processing_time,
        metadata=result.metadata,
        request_id=request_id,
    )


@router.post("/extract-base64", response_model=OCRResponse)
async def extract_text_from_base64(
    request: Request,
    ocr_request: OCRRequest,
    use_case: ExtractTextUseCase = Depends(get_extract_text_use_case),
):
    """Extract mathematical text from a base64-encoded image."""
    request_id = getattr(request.state, "request_id", None)

    try:
        image_data = base64.b64decode(ocr_request.image_base64)
        image = Image.open(io.BytesIO(image_data))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {exc}")

    try:
        result = use_case.execute(
            image,
            confidence_threshold=ocr_request.confidence_threshold,
            use_mathematical_model=ocr_request.use_mathematical_model,
            source_metadata={"input_type": "base64", "request_id": request_id},
        )
    except ModelNotLoadedException as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    logger.info(f"OCR completed for base64 image in {result.processing_time:.3f}s")
    return OCRResponse(
        success=result.success,
        extracted_text=result.extracted_text,
        confidence=result.confidence,
        processing_time=result.processing_time,
        metadata=result.metadata,
        request_id=request_id,
    )


@router.post("/extract-batch", response_model=BatchOCRResponse)
async def extract_text_batch(
    request: Request,
    batch_request: BatchOCRRequest,
    use_case: BatchExtractTextUseCase = Depends(get_batch_extract_text_use_case),
):
    """Extract mathematical text from multiple base64-encoded images."""
    request_id = getattr(request.state, "request_id", None)
    start_time = time.time()

    images: List[Image.Image] = []
    for idx, img_b64 in enumerate(batch_request.images_base64):
        try:
            img_data = base64.b64decode(img_b64)
            images.append(Image.open(io.BytesIO(img_data)))
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 image at index {idx}: {exc}",
            )

    results = use_case.execute(
        images,
        confidence_threshold=batch_request.confidence_threshold,
        use_mathematical_model=batch_request.use_mathematical_model,
    )

    successful = sum(1 for r in results if r.success)
    responses = [
        OCRResponse(
            success=r.success,
            extracted_text=r.extracted_text,
            confidence=r.confidence,
            processing_time=r.processing_time,
            metadata={**r.metadata, "request_id": request_id},
            request_id=request_id,
        )
        for r in results
    ]

    total_time = time.time() - start_time
    logger.info(
        f"Batch OCR: {successful}/{len(images)} successful in {total_time:.3f}s"
    )
    return BatchOCRResponse(
        results=responses,
        total_processing_time=total_time,
        successful_count=successful,
        failed_count=len(results) - successful,
    )


@router.get("/models")
async def list_ocr_models(request: Request):
    """List OCR models registered in the model registry."""
    registry = request.app.state.model_manager.get_registry()
    models = []
    for name in registry.list_models():
        model = registry.get_model(name)
        if model and hasattr(model, "get_model_info"):
            info = model.get_model_info()
            if info.get("model_type") == "ocr":
                models.append({"name": name, "info": info})
    return {"models": models}
