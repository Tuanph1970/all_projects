"""
Agent module for Vietnamese Grade 12 Math Tutor.

This module implements the Agentic/Tool-RAG system:
- ReAct-style agent controller
- Mathematical tools (Calculator, Formula DB, Verifier, Plotter)
- Agent prompts and templates
"""

from .math_agent import (
    MathTutorAgent,
    AgentAction,
    AgentStep,
    AgentResult,
    AgentState,
    create_agent,
)
from .agent_prompts import (
    get_system_prompt,
    get_tool_description,
    format_solution,
    format_error,
    REACT_SYSTEM_PROMPT,
    SYSTEM_PROMPT_VI,
    SYSTEM_PROMPT_EN,
    TOOL_DESCRIPTIONS,
    FEW_SHOT_EXAMPLES,
)
from .tools import (
    Calculator,
    FormulaDatabase,
    SolutionVerifier,
    MathPlotter,
    calculator_tool,
    formula_db_tool,
    verifier_tool,
    plotter_tool,
)

__all__ = [
    # Agent
    "MathTutorAgent",
    "AgentAction",
    "AgentStep",
    "AgentResult",
    "AgentState",
    "create_agent",
    # Prompts
    "get_system_prompt",
    "get_tool_description",
    "format_solution",
    "format_error",
    "REACT_SYSTEM_PROMPT",
    "SYSTEM_PROMPT_VI",
    "SYSTEM_PROMPT_EN",
    "TOOL_DESCRIPTIONS",
    "FEW_SHOT_EXAMPLES",
    # Tools
    "Calculator",
    "FormulaDatabase",
    "SolutionVerifier",
    "MathPlotter",
    "calculator_tool",
    "formula_db_tool",
    "verifier_tool",
    "plotter_tool",
]
