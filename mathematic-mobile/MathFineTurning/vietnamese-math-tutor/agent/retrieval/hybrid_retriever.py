"""
Hybrid Retriever combining semantic search with Knowledge Graph traversal.

Implements Reciprocal Rank Fusion (RRF) and graph-aware re-ranking.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .embeddings import EmbeddingConfig
from .vector_store import FormulaVectorStore, SearchResult, VectorStoreConfig
from .graph_metrics import GraphMetricsCalculator
from .semantic_search import SemanticFormulaSearch

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from hybrid retrieval."""

    formula_id: str
    score: float
    semantic_score: float = 0.0
    graph_score: float = 0.0
    source: str = "hybrid"  # "semantic", "graph", "hybrid"
    matched_fields: List[str] = field(default_factory=list)
    graph_context: Dict[str, Any] = field(default_factory=dict)
    formula_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "formula_id": self.formula_id,
            "score": self.score,
            "semantic_score": self.semantic_score,
            "graph_score": self.graph_score,
            "source": self.source,
            "matched_fields": self.matched_fields,
            "graph_context": self.graph_context,
            "formula_data": self.formula_data,
        }


@dataclass
class HybridRetrieverConfig:
    """Configuration for hybrid retriever."""

    semantic_weight: float = 0.6  # Weight for semantic search
    graph_weight: float = 0.4  # Weight for graph-based features
    rrf_k: int = 60  # RRF constant (default 60)
    include_prerequisites: bool = True
    include_applications: bool = False
    max_graph_hops: int = 2
    score_threshold: float = 0.2
    centrality_weight: float = 0.3  # Weight for centrality in graph score
    connection_weight: float = 0.4  # Weight for connection count
    path_weight: float = 0.3  # Weight for path-based relevance


class HybridRetriever:
    """
    Hybrid retriever combining semantic search with Knowledge Graph.

    Features:
    - Semantic search using vector embeddings
    - Graph expansion from semantic results
    - Context-aware retrieval based on conversation
    - Reciprocal Rank Fusion (RRF) for score combination
    - Graph-aware re-ranking using centrality metrics
    """

    def __init__(
        self,
        knowledge_graph,  # FormulaKnowledgeGraph
        semantic_search: Optional[SemanticFormulaSearch] = None,
        config: Optional[HybridRetrieverConfig] = None,
    ):
        """
        Initialize hybrid retriever.

        Args:
            knowledge_graph: FormulaKnowledgeGraph instance
            semantic_search: SemanticFormulaSearch instance (created if None)
            config: Retrieval configuration
        """
        self.kg = knowledge_graph
        self.config = config or HybridRetrieverConfig()

        # Initialize semantic search
        if semantic_search:
            self.semantic_search = semantic_search
        else:
            self.semantic_search = SemanticFormulaSearch(
                formula_db=knowledge_graph.formula_db
            )

        # Initialize graph metrics calculator
        self.metrics_calculator = GraphMetricsCalculator(
            nodes=knowledge_graph.nodes,
            adjacency_list=knowledge_graph.adjacency_list,
        )

        # Cache for PageRank scores
        self._pagerank_cache: Optional[Dict[str, float]] = None

        logger.info(
            f"HybridRetriever initialized with weights: "
            f"semantic={self.config.semantic_weight}, graph={self.config.graph_weight}"
        )

    def retrieve(
        self,
        query: str,
        context_formulas: Optional[List[str]] = None,
        k: int = 5,
        include_prerequisites: Optional[bool] = None,
        include_applications: Optional[bool] = None,
        category_filter: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval pipeline.

        Steps:
        1. Semantic search in vector store
        2. Graph expansion from semantic results
        3. Context-aware retrieval from conversation history
        4. Fusion and re-ranking

        Args:
            query: Natural language query
            context_formulas: Formula IDs from conversation context
            k: Number of results
            include_prerequisites: Include prerequisite formulas
            include_applications: Include application formulas
            category_filter: Filter by category

        Returns:
            List of RetrievalResult objects
        """
        include_prerequisites = (
            include_prerequisites
            if include_prerequisites is not None
            else self.config.include_prerequisites
        )
        include_applications = (
            include_applications
            if include_applications is not None
            else self.config.include_applications
        )

        # Step 1: Semantic search
        semantic_results = self._semantic_search(query, k * 2, category_filter)

        # Step 2: Graph expansion
        expanded_formulas = self._graph_expansion(
            semantic_results,
            include_prerequisites,
            include_applications,
        )

        # Step 3: Context-aware retrieval
        if context_formulas:
            context_expanded = self._context_expansion(context_formulas)
            expanded_formulas.update(context_expanded)

        # Step 4: Score and rank
        final_results = self._rank_results(
            query=query,
            formula_ids=list(expanded_formulas),
            semantic_results=semantic_results,
        )

        # Filter by threshold
        final_results = [
            r for r in final_results if r.score >= self.config.score_threshold
        ]

        return final_results[:k]

    def _semantic_search(
        self, query: str, k: int, category_filter: Optional[str]
    ) -> List[Tuple[str, float, List[str]]]:
        """
        Perform semantic search.

        Returns:
            List of (formula_id, score, matched_fields) tuples
        """
        results = self.semantic_search.search(
            query=query, top_k=k, category=category_filter
        )

        return [
            (r.formula_id, r.score, r.matched_fields)
            for r in results
        ]

    def _graph_expansion(
        self,
        semantic_results: List[Tuple[str, float, List[str]]],
        include_prerequisites: bool,
        include_applications: bool,
    ) -> Set[str]:
        """
        Expand semantic results using graph relationships.

        Args:
            semantic_results: Results from semantic search
            include_prerequisites: Include prerequisite formulas
            include_applications: Include application formulas

        Returns:
            Set of expanded formula IDs
        """
        expanded = set()

        for formula_id, score, _ in semantic_results:
            expanded.add(formula_id)

            # Get prerequisites
            if include_prerequisites:
                prereqs = self.kg.find_prerequisites(
                    formula_id, max_depth=self.config.max_graph_hops
                )
                for path in prereqs:
                    for node_id in path.nodes:
                        if not node_id.startswith("concept_"):
                            expanded.add(node_id)

            # Get applications
            if include_applications:
                apps = self.kg.find_applications(
                    formula_id, max_depth=self.config.max_graph_hops
                )
                for path in apps:
                    for node_id in path.nodes:
                        if not node_id.startswith("concept_"):
                            expanded.add(node_id)

        return expanded

    def _context_expansion(self, context_formulas: List[str]) -> Set[str]:
        """
        Expand from conversation context formulas.

        Args:
            context_formulas: Formula IDs from conversation

        Returns:
            Set of related formula IDs
        """
        expanded = set()

        for formula_id in context_formulas:
            # Get related formulas
            related = self.kg.get_related(
                formula_id,
                relation_types=None,  # All types
                max_depth=1,
            )

            for rel_id, rel in related:
                if not rel_id.startswith("concept_"):
                    expanded.add(rel_id)

        return expanded

    def _rank_results(
        self,
        query: str,
        formula_ids: List[str],
        semantic_results: List[Tuple[str, float, List[str]]],
    ) -> List[RetrievalResult]:
        """
        Rank results using RRF fusion and graph features.

        Args:
            query: Original query
            formula_ids: All candidate formula IDs
            semantic_results: Semantic search results

        Returns:
            Ranked list of RetrievalResult objects
        """
        # Build semantic rank map
        semantic_ranks = {}
        semantic_scores = {}
        semantic_fields = {}

        for rank, (formula_id, score, fields) in enumerate(semantic_results):
            semantic_ranks[formula_id] = rank
            semantic_scores[formula_id] = score
            semantic_fields[formula_id] = fields

        # Calculate scores for all candidates
        results = []

        for formula_id in formula_ids:
            # Semantic score (RRF)
            if formula_id in semantic_ranks:
                rank = semantic_ranks[formula_id]
                rrf_semantic = 1.0 / (self.config.rrf_k + rank)
                raw_semantic = semantic_scores[formula_id]
            else:
                rrf_semantic = 0.0
                raw_semantic = 0.0

            # Graph score
            graph_score = self._calculate_graph_score(formula_id, semantic_results)

            # Combined score
            combined_score = (
                self.config.semantic_weight * rrf_semantic
                + self.config.graph_weight * graph_score
            )

            # Get formula data
            formula_data = None
            if formula_id in self.kg.formula_db.formulas:
                formula = self.kg.formula_db.formulas[formula_id]
                formula_data = {
                    "id": formula.id,
                    "name": formula.name,
                    "name_vi": formula.name_vi,
                    "latex": formula.formula,
                    "category": formula.category,
                }

            # Determine source
            if formula_id in semantic_ranks and graph_score > 0:
                source = "hybrid"
            elif formula_id in semantic_ranks:
                source = "semantic"
            else:
                source = "graph"

            # Build graph context
            graph_context = self._build_graph_context(formula_id)

            results.append(
                RetrievalResult(
                    formula_id=formula_id,
                    score=combined_score,
                    semantic_score=raw_semantic,
                    graph_score=graph_score,
                    source=source,
                    matched_fields=semantic_fields.get(formula_id, []),
                    graph_context=graph_context,
                    formula_data=formula_data,
                )
            )

        # Sort by combined score
        results.sort(key=lambda x: x.score, reverse=True)

        return results

    def _calculate_graph_score(
        self,
        formula_id: str,
        semantic_results: List[Tuple[str, float, List[str]]],
    ) -> float:
        """
        Calculate graph-based score for a formula.

        Considers:
        - Centrality (PageRank)
        - Connection count
        - Path relevance to semantic results
        """
        # Get PageRank
        if self._pagerank_cache is None:
            self._pagerank_cache = self.metrics_calculator.pagerank()

        pagerank = self._pagerank_cache.get(formula_id, 0.0)

        # Normalize PageRank to [0, 1]
        max_pr = max(self._pagerank_cache.values()) if self._pagerank_cache else 1.0
        centrality_score = pagerank / max_pr if max_pr > 0 else 0.0

        # Connection score
        node = self.kg.nodes.get(formula_id)
        if node:
            connection_count = len(node.outgoing_edges) + len(node.incoming_edges)
            max_connections = 20  # Normalize against expected max
            connection_score = min(connection_count / max_connections, 1.0)
        else:
            connection_score = 0.0

        # Path relevance to semantic results
        path_score = 0.0
        semantic_ids = {r[0] for r in semantic_results[:5]}

        if formula_id not in semantic_ids:
            # Check if connected to any semantic result
            for sem_id in semantic_ids:
                # Check direct connection
                if formula_id in self.kg.adjacency_list.get(sem_id, {}):
                    path_score = max(path_score, 0.8)
                elif sem_id in self.kg.adjacency_list.get(formula_id, {}):
                    path_score = max(path_score, 0.8)
                else:
                    # Check 2-hop connection
                    for mid_id in self.kg.adjacency_list.get(sem_id, {}):
                        if formula_id in self.kg.adjacency_list.get(mid_id, {}):
                            path_score = max(path_score, 0.5)
                            break
        else:
            path_score = 1.0

        # Weighted combination
        graph_score = (
            self.config.centrality_weight * centrality_score
            + self.config.connection_weight * connection_score
            + self.config.path_weight * path_score
        )

        return graph_score

    def _build_graph_context(self, formula_id: str) -> Dict[str, Any]:
        """
        Build graph context for a formula result.

        Includes related formulas, prerequisites, and applications.
        """
        context = {
            "prerequisites": [],
            "applications": [],
            "similar": [],
        }

        # Prerequisites (limit to 2)
        prereqs = self.kg.find_prerequisites(formula_id, max_depth=1)
        for path in prereqs[:2]:
            if len(path.nodes) > 1:
                prereq_id = path.nodes[1]
                if prereq_id in self.kg.formula_db.formulas:
                    f = self.kg.formula_db.formulas[prereq_id]
                    context["prerequisites"].append({
                        "id": prereq_id,
                        "name_vi": f.name_vi,
                    })

        # Similar formulas (limit to 2)
        similar = self.kg.find_similar(formula_id, top_k=2)
        for sim_id, score in similar:
            if sim_id in self.kg.formula_db.formulas:
                f = self.kg.formula_db.formulas[sim_id]
                context["similar"].append({
                    "id": sim_id,
                    "name_vi": f.name_vi,
                    "similarity": round(score, 2),
                })

        return context

    def retrieve_with_explanation(
        self,
        query: str,
        k: int = 5,
        language: str = "vi",
    ) -> Tuple[List[RetrievalResult], str]:
        """
        Retrieve formulas with natural language explanation.

        Args:
            query: Search query
            k: Number of results
            language: Output language

        Returns:
            Tuple of (results, explanation_text)
        """
        results = self.retrieve(query, k=k)

        if not results:
            explanation = (
                f"Không tìm thấy công thức phù hợp với '{query}'."
                if language == "vi"
                else f"No formulas found matching '{query}'."
            )
            return results, explanation

        if language == "vi":
            lines = [f"Tìm thấy {len(results)} công thức phù hợp:\n"]
            for i, r in enumerate(results, 1):
                name = r.formula_data.get("name_vi", r.formula_id) if r.formula_data else r.formula_id
                lines.append(f"{i}. {name}")
                lines.append(f"   • Điểm phù hợp: {r.score:.1%}")
                lines.append(f"   • Nguồn: {r.source}")

                if r.graph_context.get("prerequisites"):
                    prereq_names = [p["name_vi"] for p in r.graph_context["prerequisites"]]
                    lines.append(f"   • Tiên quyết: {', '.join(prereq_names)}")

                if r.graph_context.get("similar"):
                    sim_names = [s["name_vi"] for s in r.graph_context["similar"]]
                    lines.append(f"   • Tương tự: {', '.join(sim_names)}")

                lines.append("")
        else:
            lines = [f"Found {len(results)} matching formulas:\n"]
            for i, r in enumerate(results, 1):
                name = r.formula_data.get("name", r.formula_id) if r.formula_data else r.formula_id
                lines.append(f"{i}. {name}")
                lines.append(f"   • Score: {r.score:.1%}")
                lines.append(f"   • Source: {r.source}")
                lines.append("")

        return results, "\n".join(lines)

    def get_learning_path(
        self,
        target_formula_id: str,
        known_formulas: Optional[List[str]] = None,
    ) -> List[RetrievalResult]:
        """
        Get learning path as retrieval results.

        Args:
            target_formula_id: Target formula to learn
            known_formulas: Already known formulas

        Returns:
            Ordered list of formulas to learn
        """
        known_set = set(known_formulas) if known_formulas else set()
        path = self.kg.get_learning_path(target_formula_id, known_set)

        results = []
        for i, formula_id in enumerate(path):
            formula_data = None
            if formula_id in self.kg.formula_db.formulas:
                f = self.kg.formula_db.formulas[formula_id]
                formula_data = {
                    "id": f.id,
                    "name": f.name,
                    "name_vi": f.name_vi,
                    "latex": f.formula,
                    "category": f.category,
                }

            # Score by position (earlier = more foundational)
            position_score = 1.0 - (i / len(path)) if path else 0

            results.append(
                RetrievalResult(
                    formula_id=formula_id,
                    score=position_score,
                    source="learning_path",
                    formula_data=formula_data,
                    graph_context={"position": i + 1, "total": len(path)},
                )
            )

        return results

    def index_formulas(self) -> int:
        """
        Index all formulas for semantic search.

        Returns:
            Number of documents indexed
        """
        if not self.semantic_search.is_indexed:
            return self.semantic_search.index_from_database(self.kg.formula_db)
        return self.semantic_search.vector_store.count()

    @property
    def info(self) -> Dict[str, Any]:
        """Get retriever information."""
        return {
            "config": {
                "semantic_weight": self.config.semantic_weight,
                "graph_weight": self.config.graph_weight,
                "rrf_k": self.config.rrf_k,
                "max_graph_hops": self.config.max_graph_hops,
            },
            "semantic_search": self.semantic_search.info,
            "graph_stats": self.metrics_calculator.get_graph_statistics(),
        }
