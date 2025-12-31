"""
Agent tools for Vietnamese Grade 12 Math Tutor.

Available tools:
- calculator_tool: SymPy-based mathematical computation
- formula_db_tool: Formula database retrieval
- formula_kg_tool: Knowledge Graph enhanced formula retrieval
- verifier_tool: Solution verification
- plotter_tool: Function graphing

KG-RAG Tools (Phase 2):
- semantic_search_tool: Natural language formula search
- find_prerequisites_tool: Prerequisite discovery
- find_applications_tool: Application discovery
- learning_path_tool: Learning path generation
- find_similar_tool: Similar formula search
- get_weak_areas_tool: Learning gap analysis
- record_practice_result: Practice tracking
"""

from .calculator import Calculator, CalculationResult, calculator_tool
from .formula_db import FormulaDatabase, Formula, formula_db_tool
from .formula_kg import (
    FormulaKnowledgeGraph,
    KGRelationship,
    KGNode,
    KGPath,
    RelationType,
    formula_kg_tool,
)
from .verifier import SolutionVerifier, VerificationResult, verifier_tool
from .plotter import MathPlotter, PlotResult, plotter_tool
from .kg_rag_tools import (
    semantic_search_tool,
    find_prerequisites_tool,
    find_applications_tool,
    learning_path_tool,
    find_similar_tool,
    get_weak_areas_tool,
    record_practice_result,
)

__all__ = [
    # Classes
    "Calculator",
    "CalculationResult",
    "FormulaDatabase",
    "Formula",
    "FormulaKnowledgeGraph",
    "KGRelationship",
    "KGNode",
    "KGPath",
    "RelationType",
    "SolutionVerifier",
    "VerificationResult",
    "MathPlotter",
    "PlotResult",
    # Tool functions (for agent)
    "calculator_tool",
    "formula_db_tool",
    "formula_kg_tool",
    "verifier_tool",
    "plotter_tool",
    # KG-RAG Tools (Phase 2)
    "semantic_search_tool",
    "find_prerequisites_tool",
    "find_applications_tool",
    "learning_path_tool",
    "find_similar_tool",
    "get_weak_areas_tool",
    "record_practice_result",
]
