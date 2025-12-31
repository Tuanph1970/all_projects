"""
KG-RAG Retrieval System for Vietnamese Grade 12 Math Tutor.

This module provides Knowledge Graph-enhanced Retrieval Augmented Generation:
- Semantic formula search using embeddings
- Knowledge Graph traversal and metrics
- Hybrid retrieval with RRF fusion
- Conversation context management
"""

from .embeddings import (
    EmbeddingConfig,
    EmbeddingResult,
    FormulaEmbedder,
)
from .vector_store import (
    FormulaVectorStore,
    SearchResult,
    VectorStoreConfig,
)
from .semantic_search import (
    SemanticFormulaSearch,
    SemanticSearchConfig,
    FormulaSearchResult,
    create_semantic_search,
)
from .graph_metrics import (
    GraphMetricsCalculator,
    NodeMetrics,
)
from .hybrid_retriever import (
    HybridRetriever,
    HybridRetrieverConfig,
    RetrievalResult,
)
from .context_manager import (
    ConversationContextManager,
    FormulaInteraction,
    ProblemAttempt,
    StudentKnowledgeState,
)

__all__ = [
    # Embeddings
    "EmbeddingConfig",
    "EmbeddingResult",
    "FormulaEmbedder",
    # Vector Store
    "FormulaVectorStore",
    "SearchResult",
    "VectorStoreConfig",
    # Semantic Search
    "SemanticFormulaSearch",
    "SemanticSearchConfig",
    "FormulaSearchResult",
    "create_semantic_search",
    # Graph Metrics
    "GraphMetricsCalculator",
    "NodeMetrics",
    # Hybrid Retriever
    "HybridRetriever",
    "HybridRetrieverConfig",
    "RetrievalResult",
    # Context Manager
    "ConversationContextManager",
    "FormulaInteraction",
    "ProblemAttempt",
    "StudentKnowledgeState",
]
