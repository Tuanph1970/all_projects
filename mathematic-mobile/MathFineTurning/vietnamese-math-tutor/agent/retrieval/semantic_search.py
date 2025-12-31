"""
Semantic search interface for Vietnamese Grade 12 Math formulas.

Provides natural language search over the formula database.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .embeddings import EmbeddingConfig
from .vector_store import FormulaVectorStore, SearchResult, VectorStoreConfig

logger = logging.getLogger(__name__)


@dataclass
class SemanticSearchConfig:
    """Configuration for semantic search."""

    vector_store_config: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    default_top_k: int = 5
    score_threshold: float = 0.3  # Minimum similarity score
    deduplicate_formulas: bool = True  # Group results by formula_id
    boost_vietnamese: bool = True  # Boost Vietnamese field matches


@dataclass
class FormulaSearchResult:
    """Aggregated search result for a formula."""

    formula_id: str
    score: float
    matched_fields: List[str]
    formula_data: Optional[Dict[str, Any]] = None
    relevance_explanation: str = ""


class SemanticFormulaSearch:
    """
    Semantic search over math formulas.

    Features:
    - Natural language queries in Vietnamese or English
    - Field-level matching with score aggregation
    - Category and topic filtering
    - Result deduplication and ranking
    """

    def __init__(
        self,
        config: Optional[SemanticSearchConfig] = None,
        formula_db=None,  # FormulaDatabase instance
    ):
        """
        Initialize semantic search.

        Args:
            config: Search configuration
            formula_db: FormulaDatabase instance for enriching results
        """
        self.config = config or SemanticSearchConfig()
        self.vector_store = FormulaVectorStore(self.config.vector_store_config)
        self.formula_db = formula_db
        self._indexed = False

    def index_formulas(
        self, formulas: List[Dict[str, Any]], mode: str = "fields"
    ) -> int:
        """
        Index formulas for semantic search.

        Args:
            formulas: List of formula dictionaries
            mode: "fields" for separate embeddings, "composite" for single

        Returns:
            Number of documents indexed
        """
        # Clear existing index
        self.vector_store.clear()

        # Add formulas
        doc_count = self.vector_store.add_formulas_batch(formulas, mode=mode)

        # Persist
        self.vector_store.persist()
        self._indexed = True

        logger.info(f"Indexed {len(formulas)} formulas ({doc_count} documents)")
        return doc_count

    def index_from_database(self, formula_db=None, mode: str = "fields") -> int:
        """
        Index formulas from a FormulaDatabase instance.

        Args:
            formula_db: FormulaDatabase instance (or use self.formula_db)
            mode: Indexing mode

        Returns:
            Number of documents indexed
        """
        db = formula_db or self.formula_db

        if db is None:
            raise ValueError("No FormulaDatabase provided")

        # Get all formulas
        all_formulas = db.get_all_formulas()

        return self.index_formulas(all_formulas, mode=mode)

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        category: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> List[FormulaSearchResult]:
        """
        Search for formulas using natural language query.

        Args:
            query: Search query (Vietnamese or English)
            top_k: Number of results (default: config.default_top_k)
            category: Filter by category
            min_score: Minimum similarity score

        Returns:
            List of FormulaSearchResult objects
        """
        top_k = top_k or self.config.default_top_k
        min_score = min_score or self.config.score_threshold

        # Search vector store (get more results for aggregation)
        raw_results = self.vector_store.search(
            query=query, k=top_k * 3, filter_category=category
        )

        # Filter by score
        filtered_results = [r for r in raw_results if r.score >= min_score]

        # Deduplicate and aggregate by formula_id
        if self.config.deduplicate_formulas:
            return self._aggregate_results(filtered_results, top_k)
        else:
            return [
                FormulaSearchResult(
                    formula_id=r.formula_id,
                    score=r.score,
                    matched_fields=[r.field],
                    formula_data=self._get_formula_data(r.formula_id),
                )
                for r in filtered_results[:top_k]
            ]

    def _aggregate_results(
        self, results: List[SearchResult], top_k: int
    ) -> List[FormulaSearchResult]:
        """
        Aggregate results by formula_id and compute combined score.

        Args:
            results: Raw search results
            top_k: Number of final results

        Returns:
            Aggregated and ranked results
        """
        formula_scores: Dict[str, Dict[str, Any]] = {}

        for result in results:
            formula_id = result.formula_id

            if formula_id not in formula_scores:
                formula_scores[formula_id] = {
                    "max_score": 0.0,
                    "sum_score": 0.0,
                    "count": 0,
                    "fields": [],
                }

            entry = formula_scores[formula_id]
            entry["max_score"] = max(entry["max_score"], result.score)
            entry["sum_score"] += result.score
            entry["count"] += 1
            entry["fields"].append((result.field, result.score))

            # Boost for Vietnamese matches
            if self.config.boost_vietnamese and result.field.endswith("_vi"):
                entry["sum_score"] += result.score * 0.2

        # Compute final scores (combination of max and average)
        final_results = []
        for formula_id, entry in formula_scores.items():
            avg_score = entry["sum_score"] / entry["count"]
            # Weighted combination: 60% max score, 40% average
            final_score = 0.6 * entry["max_score"] + 0.4 * avg_score

            # Sort fields by score for explanation
            sorted_fields = sorted(entry["fields"], key=lambda x: x[1], reverse=True)
            matched_fields = [f[0] for f in sorted_fields]

            # Generate relevance explanation
            top_field, top_score = sorted_fields[0]
            explanation = f"Best match in {top_field} (score: {top_score:.3f})"

            final_results.append(
                FormulaSearchResult(
                    formula_id=formula_id,
                    score=final_score,
                    matched_fields=matched_fields,
                    formula_data=self._get_formula_data(formula_id),
                    relevance_explanation=explanation,
                )
            )

        # Sort by final score
        final_results.sort(key=lambda x: x.score, reverse=True)

        return final_results[:top_k]

    def _get_formula_data(self, formula_id: str) -> Optional[Dict[str, Any]]:
        """Get formula data from database if available."""
        if self.formula_db:
            formula = self.formula_db.get_formula(formula_id)
            if formula:
                return formula.to_dict() if hasattr(formula, "to_dict") else formula
        return None

    def search_similar(
        self, formula_id: str, top_k: int = 5, exclude_self: bool = True
    ) -> List[FormulaSearchResult]:
        """
        Find formulas similar to a given formula.

        Args:
            formula_id: Reference formula ID
            top_k: Number of similar formulas
            exclude_self: Whether to exclude the reference formula

        Returns:
            List of similar formulas
        """
        # Get embedding for the formula
        embedding = self.vector_store.get_embedding(formula_id)

        if embedding is None:
            logger.warning(f"No embedding found for formula: {formula_id}")
            return []

        # Search for similar (need text for the API, but we'll override)
        # Get formula name as query proxy
        formula_data = self._get_formula_data(formula_id)
        if formula_data:
            query = formula_data.get("name_vi", "") or formula_data.get("name", "")
        else:
            query = formula_id

        results = self.search(query, top_k=top_k + 1)

        # Exclude self if requested
        if exclude_self:
            results = [r for r in results if r.formula_id != formula_id]

        return results[:top_k]

    def search_by_topic(
        self, topic: str, top_k: int = 10
    ) -> List[FormulaSearchResult]:
        """
        Search formulas by topic.

        Args:
            topic: Topic name (e.g., "derivatives", "integrals")
            top_k: Number of results

        Returns:
            List of formulas for the topic
        """
        # Enhance query with topic keywords
        topic_queries = {
            "derivatives": "đạo hàm derivative calculation",
            "integrals": "tích phân nguyên hàm integration",
            "limits": "giới hạn hàm số limit",
            "trigonometry": "lượng giác sin cos tan",
            "probability": "xác suất tổ hợp chỉnh hợp probability",
            "geometry": "hình học diện tích thể tích area volume",
        }

        query = topic_queries.get(topic.lower(), topic)
        return self.search(query, top_k=top_k)

    def explain_search(
        self, query: str, top_k: int = 3
    ) -> str:
        """
        Explain search results in natural language.

        Args:
            query: Search query
            top_k: Number of results to explain

        Returns:
            Vietnamese explanation of search results
        """
        results = self.search(query, top_k=top_k)

        if not results:
            return f"Không tìm thấy công thức phù hợp với '{query}'."

        lines = [f"Tìm thấy {len(results)} công thức phù hợp với '{query}':\n"]

        for i, result in enumerate(results, 1):
            formula_name = (
                result.formula_data.get("name_vi", result.formula_id)
                if result.formula_data
                else result.formula_id
            )
            lines.append(f"{i}. {formula_name}")
            lines.append(f"   - Độ phù hợp: {result.score:.1%}")
            lines.append(f"   - {result.relevance_explanation}")

            if result.formula_data:
                latex = result.formula_data.get("latex", "")
                if latex:
                    lines.append(f"   - Công thức: {latex}")

            lines.append("")

        return "\n".join(lines)

    @property
    def is_indexed(self) -> bool:
        """Check if formulas have been indexed."""
        return self._indexed or self.vector_store.count() > 0

    @property
    def info(self) -> Dict[str, Any]:
        """Get search system information."""
        return {
            "indexed": self.is_indexed,
            "vector_store": self.vector_store.info,
            "config": {
                "default_top_k": self.config.default_top_k,
                "score_threshold": self.config.score_threshold,
                "deduplicate": self.config.deduplicate_formulas,
                "boost_vietnamese": self.config.boost_vietnamese,
            },
        }


# Convenience function for quick searches
def create_semantic_search(
    formula_db=None,
    persist_directory: str = "./data/vector_store",
    auto_index: bool = True,
) -> SemanticFormulaSearch:
    """
    Create and initialize a semantic search instance.

    Args:
        formula_db: FormulaDatabase instance
        persist_directory: Where to store vector database
        auto_index: Whether to auto-index if not already indexed

    Returns:
        Configured SemanticFormulaSearch instance
    """
    config = SemanticSearchConfig(
        vector_store_config=VectorStoreConfig(persist_directory=persist_directory)
    )

    search = SemanticFormulaSearch(config=config, formula_db=formula_db)

    # Auto-index if database provided and not already indexed
    if auto_index and formula_db and not search.is_indexed:
        search.index_from_database(formula_db)

    return search
