"""DTOs (Data Transfer Objects) for OCR use cases."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExtractTextCommand(BaseModel):
    """Input command for the ExtractTextUseCase."""
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    use_mathematical_model: bool = Field(default=True)
    source_metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchExtractTextCommand(BaseModel):
    """Input command for the BatchExtractTextUseCase."""
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    use_mathematical_model: bool = Field(default=True)
