"""
OCR router for mathematical text recognition endpoints.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import io
import time
from PIL import Image
from loguru import logger

from ...models.base import get_model_registry, OCRResult
from ...models.ocr_model import OCRModel, MathematicalOCRModel
from ...config.settings import get_settings, Settings

router = APIRouter()


class OCRRequest(BaseModel):
    """Request model for OCR processing."""
    image_base64: Optional[str] = Field(None, description="Base64 encoded image data")
    confidence_threshold: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="Minimum confidence threshold")
    use_mathematical_model: Optional[bool] = Field(True, description="Use mathematical OCR model")


class OCRResponse(BaseModel):
    """Response model for OCR processing."""
    success: bool
    extracted_text: str
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]
    request_id: Optional[str] = None


class BatchOCRRequest(BaseModel):
    """Request model for batch OCR processing."""
    images_base64: List[str] = Field(..., min_items=1, max_items=10, description="List of base64 encoded images")
    confidence_threshold: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="Minimum confidence threshold")
    use_mathematical_model: Optional[bool] = Field(True, description="Use mathematical OCR model")


class BatchOCRResponse(BaseModel):
    """Response model for batch OCR processing."""
    results: List[OCRResponse]
    total_processing_time: float
    successful_count: int
    failed_count: int


@router.post("/extract", response_model=OCRResponse)
async def extract_text_from_image(
    request: Request,
    file: UploadFile = File(...),
    confidence_threshold: float = 0.8,
    use_mathematical_model: bool = True,
    settings: Settings = Depends(get_settings)
):
    """
    Extract mathematical text from an uploaded image using OCR.
    
    Args:
        file: The uploaded image file
        confidence_threshold: Minimum confidence threshold for results
        use_mathematical_model: Whether to use the mathematical OCR model
    
    Returns:
        OCR result with extracted text and metadata
    """
    request_id = getattr(request.state, 'request_id', None)
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if hasattr(file, 'size') and file.size > max_size:
        raise HTTPException(status_code=400, detail="File size too large (max 10MB)")
    
    try:
        start_time = time.time()
        
        # Read image file
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Get appropriate OCR model
        model_registry = get_model_registry()
        if use_mathematical_model:
            # Try to get mathematical OCR model
            model_name = "mathematical_ocr"
            if model_name not in model_registry.list_models():
                # Fall back to regular OCR model
                model_name = "default_ocr"
        else:
            model_name = "default_ocr"
        
        if model_name not in model_registry.list_models():
            raise HTTPException(status_code=503, detail="OCR model not available")
        
        ocr_model = model_registry.get_model(model_name)
        if not ocr_model.is_model_loaded():
            logger.info(f"Loading OCR model: {model_name}")
            ocr_model.load_model()
        
        # Set confidence threshold
        if hasattr(ocr_model, 'set_confidence_threshold'):
            ocr_model.set_confidence_threshold(confidence_threshold)
        
        # Perform OCR
        result = ocr_model.predict(image)
        
        # Add request metadata
        if result.metadata is None:
            result.metadata = {}
        result.metadata.update({
            "file_name": file.filename,
            "file_size_bytes": len(image_data),
            "content_type": file.content_type,
            "model_used": model_name,
            "request_id": request_id
        })
        
        logger.info(f"OCR completed for {file.filename} in {result.processing_time:.3f}s")
        
        return OCRResponse(
            success=result.success,
            extracted_text=result.extracted_text,
            confidence=result.confidence,
            processing_time=result.processing_time,
            metadata=result.metadata,
            request_id=request_id
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"OCR processing failed for {file.filename}: {str(e)}")
        
        return OCRResponse(
            success=False,
            extracted_text="",
            confidence=0.0,
            processing_time=processing_time,
            metadata={"error": str(e), "file_name": file.filename},
            request_id=request_id
        )


@router.post("/extract-base64", response_model=OCRResponse)
async def extract_text_from_base64(
    request: Request,
    ocr_request: OCRRequest,
    settings: Settings = Depends(get_settings)
):
    """
    Extract mathematical text from a base64-encoded image using OCR.
    
    Args:
        ocr_request: OCR request containing base64 image data
    
    Returns:
        OCR result with extracted text and metadata
    """
    if not ocr_request.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        import base64
        
        start_time = time.time()
        
        # Decode base64 image
        image_data = base64.b64decode(ocr_request.image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # Get appropriate OCR model
        model_registry = get_model_registry()
        model_name = "mathematical_ocr" if ocr_request.use_mathematical_model else "default_ocr"
        
        if model_name not in model_registry.list_models():
            model_name = "default_ocr"
        
        if model_name not in model_registry.list_models():
            raise HTTPException(status_code=503, detail="OCR model not available")
        
        ocr_model = model_registry.get_model(model_name)
        if not ocr_model.is_model_loaded():
            logger.info(f"Loading OCR model: {model_name}")
            ocr_model.load_model()
        
        # Set confidence threshold
        if hasattr(ocr_model, 'set_confidence_threshold'):
            ocr_model.set_confidence_threshold(ocr_request.confidence_threshold)
        
        # Perform OCR
        result = ocr_model.predict(image)
        
        # Add request metadata
        if result.metadata is None:
            result.metadata = {}
        result.metadata.update({
            "input_type": "base64",
            "image_size_bytes": len(image_data),
            "model_used": model_name,
            "request_id": request_id
        })
        
        logger.info(f"OCR completed for base64 image in {result.processing_time:.3f}s")
        
        return OCRResponse(
            success=result.success,
            extracted_text=result.extracted_text,
            confidence=result.confidence,
            processing_time=result.processing_time,
            metadata=result.metadata,
            request_id=request_id
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"OCR processing failed for base64 image: {str(e)}")
        
        return OCRResponse(
            success=False,
            extracted_text="",
            confidence=0.0,
            processing_time=processing_time,
            metadata={"error": str(e), "input_type": "base64"},
            request_id=request_id
        )


@router.post("/extract-batch", response_model=BatchOCRResponse)
async def extract_text_batch(
    request: Request,
    batch_request: BatchOCRRequest,
    settings: Settings = Depends(get_settings)
):
    """
    Extract mathematical text from multiple base64-encoded images using OCR.
    
    Args:
        batch_request: Batch OCR request containing multiple base64 images
    
    Returns:
        Batch OCR results with extracted text and metadata for each image
    """
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        import base64
        
        start_time = time.time()
        results = []
        successful_count = 0
        failed_count = 0
        
        # Get appropriate OCR model
        model_registry = get_model_registry()
        model_name = "mathematical_ocr" if batch_request.use_mathematical_model else "default_ocr"
        
        if model_name not in model_registry.list_models():
            model_name = "default_ocr"
        
        if model_name not in model_registry.list_models():
            raise HTTPException(status_code=503, detail="OCR model not available")
        
        ocr_model = model_registry.get_model(model_name)
        if not ocr_model.is_model_loaded():
            logger.info(f"Loading OCR model: {model_name}")
            ocr_model.load_model()
        
        # Set confidence threshold
        if hasattr(ocr_model, 'set_confidence_threshold'):
            ocr_model.set_confidence_threshold(batch_request.confidence_threshold)
        
        # Process each image
        for i, image_base64 in enumerate(batch_request.images_base64):
            try:
                # Decode base64 image
                image_data = base64.b64decode(image_base64)
                image = Image.open(io.BytesIO(image_data))
                
                # Perform OCR
                result = ocr_model.predict(image)
                
                # Add request metadata
                if result.metadata is None:
                    result.metadata = {}
                result.metadata.update({
                    "input_type": "base64_batch",
                    "batch_index": i,
                    "image_size_bytes": len(image_data),
                    "model_used": model_name,
                    "request_id": request_id
                })
                
                ocr_response = OCRResponse(
                    success=result.success,
                    extracted_text=result.extracted_text,
                    confidence=result.confidence,
                    processing_time=result.processing_time,
                    metadata=result.metadata,
                    request_id=request_id
                )
                
                results.append(ocr_response)
                
                if result.success:
                    successful_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to process batch image {i}: {str(e)}")
                
                error_response = OCRResponse(
                    success=False,
                    extracted_text="",
                    confidence=0.0,
                    processing_time=0.0,
                    metadata={"error": str(e), "batch_index": i, "input_type": "base64_batch"},
                    request_id=request_id
                )
                results.append(error_response)
                failed_count += 1
        
        total_processing_time = time.time() - start_time
        
        logger.info(f"Batch OCR completed: {successful_count} successful, {failed_count} failed in {total_processing_time:.3f}s")
        
        return BatchOCRResponse(
            results=results,
            total_processing_time=total_processing_time,
            successful_count=successful_count,
            failed_count=failed_count
        )
        
    except Exception as e:
        total_processing_time = time.time() - start_time
        logger.error(f"Batch OCR processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@router.get("/models")
async def list_ocr_models():
    """List available OCR models."""
    model_registry = get_model_registry()
    models = []
    
    for model_name in model_registry.list_models():
        try:
            model = model_registry.get_model(model_name)
            if hasattr(model, 'get_model_info'):
                model_info = model.get_model_info()
                if model_info.get('model_type') == 'OCR':
                    models.append({
                        "name": model_name,
                        "info": model_info
                    })
        except Exception as e:
            logger.warning(f"Failed to get info for model {model_name}: {e}")
    
    return {"models": models}