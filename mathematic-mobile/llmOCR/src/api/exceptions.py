"""
Exception handlers for the Mathematics LLM OCR Service.
"""
from typing import Optional, Dict, Any, Callable
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from loguru import logger
import time


class MLServiceException(Exception):
    """Base exception for ML service errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ML_SERVICE_{status_code}"
        self.details = details or {}
        super().__init__(self.message)


class ModelNotLoadedException(MLServiceException):
    """Exception raised when a model is not loaded."""

    def __init__(
        self,
        model_name: str,
        message: Optional[str] = None
    ):
        self.model_name = model_name
        message = message or f"Model '{model_name}' is not loaded or unavailable"
        super().__init__(
            message=message,
            status_code=503,
            error_code="MODEL_NOT_LOADED",
            details={"model_name": model_name}
        )


class ModelLoadingException(MLServiceException):
    """Exception raised when model loading fails."""

    def __init__(
        self,
        model_name: str,
        reason: str,
        message: Optional[str] = None
    ):
        self.model_name = model_name
        self.reason = reason
        message = message or f"Failed to load model '{model_name}': {reason}"
        super().__init__(
            message=message,
            status_code=500,
            error_code="MODEL_LOADING_FAILED",
            details={"model_name": model_name, "reason": reason}
        )


class InferenceException(MLServiceException):
    """Exception raised during model inference."""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="INFERENCE_FAILED",
            details={"model_name": model_name, **(details or {})}
        )


class OCRException(MLServiceException):
    """Exception raised during OCR processing."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="OCR_PROCESSING_FAILED",
            details=details or {}
        )


class InvalidInputException(MLServiceException):
    """Exception raised for invalid input data."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_INPUT",
            details={"field": field, **(details or {})}
        )


class ImageProcessingException(MLServiceException):
    """Exception raised during image processing."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="IMAGE_PROCESSING_FAILED",
            details=details or {}
        )


class ConfigurationException(MLServiceException):
    """Exception raised for configuration errors."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key} if config_key else {}
        )


class RateLimitExceededException(MLServiceException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        retry_after: int,
        limit: int,
        window: int
    ):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={
                "retry_after": retry_after,
                "limit": limit,
                "window_seconds": window
            }
        )


class ServiceUnavailableException(MLServiceException):
    """Exception raised when service is temporarily unavailable."""

    def __init__(
        self,
        message: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(
            message=message or "Service temporarily unavailable",
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details={"retry_after": retry_after} if retry_after else {}
        )


def create_error_response(
    status_code: int,
    message: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a standardized error response."""
    content = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "status_code": status_code,
        },
        "timestamp": time.time(),
    }
    
    if details:
        content["error"]["details"] = details
    
    if request_id:
        content["request_id"] = request_id
    
    return JSONResponse(status_code=status_code, content=content)


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup all exception handlers for the FastAPI application."""
    
    @app.exception_handler(MLServiceException)
    async def ml_service_exception_handler(
        request: Request,
        exc: MLServiceException
    ) -> JSONResponse:
        """Handle ML service exceptions."""
        request_id = getattr(request.state, 'request_id', None)
        
        logger.error(
            f"ML service error: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "request_id": request_id,
            }
        )
        
        return create_error_response(
            status_code=exc.status_code,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
            request_id=request_id
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        request_id = getattr(request.state, 'request_id', None)
        
        logger.warning(
            f"HTTP error: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "request_id": request_id,
            }
        )
        
        return create_error_response(
            status_code=exc.status_code,
            message=str(exc.detail),
            error_code=f"HTTP_{exc.status_code}",
            request_id=request_id
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request,
        exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle Starlette HTTP exceptions."""
        request_id = getattr(request.state, 'request_id', None)
        
        return create_error_response(
            status_code=exc.status_code,
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            request_id=request_id
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        request_id = getattr(request.state, 'request_id', None)
        
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error.get("loc", [])),
                "message": error.get("msg", ""),
                "type": error.get("type", ""),
            })
        
        logger.warning(
            f"Request validation failed: {errors}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
            }
        )
        
        return create_error_response(
            status_code=422,
            message="Request validation failed",
            error_code="VALIDATION_ERROR",
            details={"errors": errors},
            request_id=request_id
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(
        request: Request,
        exc: ValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        request_id = getattr(request.state, 'request_id', None)
        
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error.get("loc", [])),
                "message": error.get("msg", ""),
                "type": error.get("type", ""),
            })
        
        logger.warning(
            f"Pydantic validation failed: {errors}",
            extra={
                "request_id": request_id,
            }
        )
        
        return create_error_response(
            status_code=400,
            message="Data validation failed",
            error_code="PYDANTIC_VALIDATION_ERROR",
            details={"errors": errors},
            request_id=request_id
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle unhandled exceptions."""
        request_id = getattr(request.state, 'request_id', None)
        
        logger.error(
            f"Unhandled exception: {str(exc)}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
            },
            exc_info=True
        )
        
        return create_error_response(
            status_code=500,
            message="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            details={"type": type(exc).__name__},
            request_id=request_id
        )


def add_custom_exception_handler(
    app: FastAPI,
    exception_class: type,
    handler: Callable[[Request, Exception], JSONResponse]
) -> None:
    """
    Add a custom exception handler.
    
    Args:
        app: FastAPI application
        exception_class: Exception class to handle
        handler: Handler function
    """
    app.add_exception_handler(exception_class, handler)
