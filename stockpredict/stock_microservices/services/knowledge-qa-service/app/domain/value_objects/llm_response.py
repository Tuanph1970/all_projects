"""LLMResponse value object - response from LLM with metadata."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LLMResponse:
    """Response from LLM with text and metadata."""

    text: str
    model: str
    tokens_used: Optional[int] = None
    duration_ms: Optional[float] = None
    finish_reason: Optional[str] = None
