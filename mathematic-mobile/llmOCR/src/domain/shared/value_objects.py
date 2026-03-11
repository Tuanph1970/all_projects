"""
Shared domain value objects for the Mathematics LLM OCR Service.

These are pure Python types with no framework dependencies beyond Pydantic,
which is used as the project-standard value object library.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelType(str, Enum):
    """Classification of ML model types."""
    OCR = "ocr"
    LLM = "llm"
    CHAT = "chat"
    SOLUTION = "solution"
    FINE_TUNE = "fine_tune"
    AGENT = "agent"


class TaskStatus(str, Enum):
    """Lifecycle status of an ML processing task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingResult(BaseModel):
    """Base result for all ML processing operations."""
    success: bool = Field(description="Whether the operation succeeded")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    processing_time: float = Field(ge=0.0, description="Wall-clock seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OCRResult(ProcessingResult):
    """Result from OCR processing."""
    extracted_text: str = Field(description="Text extracted from the image")
    bounding_boxes: Optional[List[Dict[str, Any]]] = Field(default=None)
    detected_language: Optional[str] = Field(default=None)


class LLMResult(ProcessingResult):
    """Result from LLM inference."""
    generated_text: str = Field(description="Model-generated text")
    tokens_used: int = Field(ge=0, description="Number of tokens consumed")
    model_name: str = Field(description="Name of the model used")


class SolutionStep(BaseModel):
    """A single step in a mathematical solution."""
    step_number: int = Field(ge=1)
    description: str
    formula: Optional[str] = None
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)


class SolutionResult(ProcessingResult):
    """Result from mathematical problem solving."""
    problem_type: str = Field(default="unknown", description="Classified problem type")
    solution: str = Field(default="", description="Full solution text")
    steps: List[str] = Field(default_factory=list, description="Step-by-step solution")
    final_answer: str = Field(default="", description="Final computed answer")
    alternative_methods: Optional[List[str]] = Field(default=None)


class MLTask(BaseModel):
    """
    Aggregate representing a single ML processing task.

    NOTE: Currently defined for future async task tracking (P2).
    The task lifecycle is managed via mark_* methods.
    """
    id: str = Field(description="Unique task identifier")
    task_type: str = Field(description="Type of ML task")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    input_data: Dict[str, Any] = Field(description="Serialisable input payload")
    result: Optional[ProcessingResult] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = Field(default=None)

    def mark_processing(self) -> None:
        self.status = TaskStatus.PROCESSING
        self.updated_at = datetime.utcnow()

    def mark_completed(self, result: ProcessingResult) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.error_message = None
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message: str) -> None:
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.result = None
        self.updated_at = datetime.utcnow()
