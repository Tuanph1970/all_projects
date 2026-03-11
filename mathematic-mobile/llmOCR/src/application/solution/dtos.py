"""DTOs for solution use cases."""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SolveProblemCommand(BaseModel):
    """Input command for SolveProblemUseCase."""
    problem: str = Field(..., description="Mathematical problem text")
    context: Dict[str, Any] = Field(default_factory=dict)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class OCRAndSolveCommand(BaseModel):
    """Input command for OCRAndSolveUseCase."""
    ocr_confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    solution_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    use_mathematical_ocr: bool = Field(default=True)
