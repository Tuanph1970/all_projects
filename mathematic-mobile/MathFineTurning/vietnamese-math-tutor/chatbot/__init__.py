"""
Chatbot module for Vietnamese Grade 12 Math Tutor.

This module provides:
- Gradio-based web interface
- Simple mode inference (model-only)
- Agent mode inference (full agentic system)
"""

from .inference import (
    MathTutorInference,
    GenerationConfig,
    create_inference_engine,
)
from .agent_inference import (
    AgentInferenceEngine,
    AgentInferenceResult,
    create_agent_inference_engine,
)

__all__ = [
    # Simple inference
    "MathTutorInference",
    "GenerationConfig",
    "create_inference_engine",
    # Agent inference
    "AgentInferenceEngine",
    "AgentInferenceResult",
    "create_agent_inference_engine",
]
