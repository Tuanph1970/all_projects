"""
Solution router for mathematical problem solving endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time
from loguru import logger

from ...models.base import get_model_registry
from ...models.solution_model import SolutionResult
from ...config.settings import get_settings, Settings

router = APIRouter()


class SolutionRequest(BaseModel):
    """Request model for problem solving."""
    problem: str = Field(..., description="Mathematical problem to solve")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the problem")
    confidence_threshold: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")


class SolutionResponse(BaseModel):
    """Response model for problem solving."""
    success: bool
    solution: str
    steps: List[str]
    final_answer: str
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]
    request_id: Optional[str] = None


class OCRSolutionRequest(BaseModel):
    """Request model for OCR + Solution pipeline."""
    image_base64: str = Field(..., description="Base64 encoded image data")
    ocr_confidence_threshold: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="OCR confidence threshold")
    solution_confidence_threshold: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="Solution confidence threshold")
    use_mathematical_ocr: Optional[bool] = Field(True, description="Use mathematical OCR model")


class OCRSolutionResponse(BaseModel):
    """Response model for OCR + Solution pipeline."""
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


@router.post("/solve", response_model=SolutionResponse)
async def solve_problem(
    request: Request,
    solution_request: SolutionRequest,
    settings: Settings = Depends(get_settings)
):
    """
    Solve a mathematical problem given as text.
    
    Args:
        solution_request: Problem solving request with problem text
    
    Returns:
        Solution with steps and final answer
    """
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        start_time = time.time()
        
        # Get solution model
        model_registry = get_model_registry()
        solution_model_name = "default_solution"
        
        if solution_model_name not in model_registry.list_models():
            raise HTTPException(status_code=503, detail="Solution model not available")
        
        solution_model = model_registry.get_model(solution_model_name)
        if not solution_model.is_model_loaded():
            logger.info(f"Loading solution model: {solution_model_name}")
            solution_model.load_model()
        
        # Set confidence threshold
        if hasattr(solution_model, 'set_confidence_threshold'):
            solution_model.set_confidence_threshold(solution_request.confidence_threshold)
        
        # Prepare input data
        input_data = {
            'problem': solution_request.problem,
            'context': solution_request.context or {}
        }
        
        # Solve the problem
        result = solution_model.predict(input_data)
        
        # Add request metadata
        if result.metadata is None:
            result.metadata = {}
        result.metadata.update({
            "input_type": "text_problem",
            "model_used": solution_model_name,
            "request_id": request_id
        })
        
        logger.info(f"Problem solved in {result.processing_time:.3f}s with confidence {result.confidence:.3f}")
        
        return SolutionResponse(
            success=result.success,
            solution=result.solution,
            steps=result.steps,
            final_answer=result.final_answer,
            confidence=result.confidence,
            processing_time=result.processing_time,
            metadata=result.metadata,
            request_id=request_id
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Problem solving failed: {str(e)}")
        
        return SolutionResponse(
            success=False,
            solution="",
            steps=[],
            final_answer="",
            confidence=0.0,
            processing_time=processing_time,
            metadata={"error": str(e)},
            request_id=request_id
        )


@router.post("/ocr-solve", response_model=OCRSolutionResponse)
async def ocr_and_solve(
    request: Request,
    ocr_solution_request: OCRSolutionRequest,
    settings: Settings = Depends(get_settings)
):
    """
    Extract mathematical problem from image and solve it.
    
    Args:
        ocr_solution_request: Combined OCR and solution request
    
    Returns:
        Combined OCR and solution results
    """
    request_id = getattr(request.state, 'request_id', None)
    
    try:
        import base64
        from io import BytesIO
        from PIL import Image
        
        start_time = time.time()
        
        # Step 1: OCR Processing
        logger.info("Starting OCR processing")
        
        # Decode base64 image
        image_data = base64.b64decode(ocr_solution_request.image_base64)
        image = Image.open(BytesIO(image_data))
        
        # Get OCR model
        model_registry = get_model_registry()
        ocr_model_name = "mathematical_ocr" if ocr_solution_request.use_mathematical_ocr else "default_ocr"
        
        if ocr_model_name not in model_registry.list_models():
            ocr_model_name = "default_ocr"
        
        if ocr_model_name not in model_registry.list_models():
            raise HTTPException(status_code=503, detail="OCR model not available")
        
        ocr_model = model_registry.get_model(ocr_model_name)
        if not ocr_model.is_model_loaded():
            logger.info(f"Loading OCR model: {ocr_model_name}")
            ocr_model.load_model()
        
        # Set OCR confidence threshold
        if hasattr(ocr_model, 'set_confidence_threshold'):
            ocr_model.set_confidence_threshold(ocr_solution_request.ocr_confidence_threshold)
        
        # Perform OCR
        ocr_result = ocr_model.predict(image)
        
        if not ocr_result.success or not ocr_result.extracted_text.strip():
            return OCRSolutionResponse(
                success=False,
                extracted_text=ocr_result.extracted_text,
                ocr_confidence=ocr_result.confidence,
                solution="OCR failed to extract text",
                solution_steps=[],
                final_answer="",
                solution_confidence=0.0,
                total_processing_time=time.time() - start_time,
                metadata={"error": "OCR extraction failed", "ocr_metadata": ocr_result.metadata},
                request_id=request_id
            )
        
        logger.info(f"OCR extracted text: {ocr_result.extracted_text}")
        
        # Step 2: Solution Processing
        logger.info("Starting solution processing")
        
        # Get solution model
        solution_model_name = "default_solution"
        
        if solution_model_name not in model_registry.list_models():
            raise HTTPException(status_code=503, detail="Solution model not available")
        
        solution_model = model_registry.get_model(solution_model_name)
        if not solution_model.is_model_loaded():
            logger.info(f"Loading solution model: {solution_model_name}")
            solution_model.load_model()
        
        # Set solution confidence threshold
        if hasattr(solution_model, 'set_confidence_threshold'):
            solution_model.set_confidence_threshold(ocr_solution_request.solution_confidence_threshold)
        
        # Prepare solution input
        solution_input = {
            'problem': ocr_result.extracted_text,
            'context': {
                'source': 'ocr',
                'ocr_confidence': ocr_result.confidence,
                'ocr_metadata': ocr_result.metadata
            }
        }
        
        # Solve the problem
        solution_result = solution_model.predict(solution_input)
        
        total_processing_time = time.time() - start_time
        
        # Combine metadata
        combined_metadata = {
            "pipeline": "ocr_and_solve",
            "ocr_model": ocr_model_name,
            "solution_model": solution_model_name,
            "ocr_processing_time": ocr_result.processing_time,
            "solution_processing_time": solution_result.processing_time,
            "request_id": request_id
        }
        
        if ocr_result.metadata:
            combined_metadata["ocr_metadata"] = ocr_result.metadata
        if solution_result.metadata:
            combined_metadata["solution_metadata"] = solution_result.metadata
        
        logger.info(f"OCR+Solution pipeline completed in {total_processing_time:.3f}s")
        
        return OCRSolutionResponse(
            success=solution_result.success,
            extracted_text=ocr_result.extracted_text,
            ocr_confidence=ocr_result.confidence,
            solution=solution_result.solution,
            solution_steps=solution_result.steps,
            final_answer=solution_result.final_answer,
            solution_confidence=solution_result.confidence,
            total_processing_time=total_processing_time,
            metadata=combined_metadata,
            request_id=request_id
        )
        
    except Exception as e:
        total_processing_time = time.time() - start_time
        logger.error(f"OCR+Solution pipeline failed: {str(e)}")
        
        return OCRSolutionResponse(
            success=False,
            extracted_text="",
            ocr_confidence=0.0,
            solution="",
            solution_steps=[],
            final_answer="",
            solution_confidence=0.0,
            total_processing_time=total_processing_time,
            metadata={"error": str(e)},
            request_id=request_id
        )


@router.get("/models")
async def list_solution_models():
    """List available solution models."""
    model_registry = get_model_registry()
    models = []
    
    for model_name in model_registry.list_models():
        try:
            model = model_registry.get_model(model_name)
            if hasattr(model, 'get_model_info'):
                model_info = model.get_model_info()
                if model_info.get('model_type') == 'SOLUTION':
                    models.append({
                        "name": model_name,
                        "info": model_info
                    })
        except Exception as e:
            logger.warning(f"Failed to get info for model {model_name}: {e}")
    
    return {"models": models}