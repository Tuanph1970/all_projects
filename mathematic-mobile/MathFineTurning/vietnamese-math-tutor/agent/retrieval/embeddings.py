"""
Embedding generation for Vietnamese Grade 12 Math formulas.

Uses multilingual sentence transformers for Vietnamese/English support.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""

    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    dimension: int = 384
    batch_size: int = 32
    normalize: bool = True
    device: str = "cpu"  # "cpu" or "cuda"
    cache_embeddings: bool = True

    # Fields to embed from formulas
    fields_to_embed: List[str] = field(
        default_factory=lambda: [
            "name",
            "name_vi",
            "description",
            "description_vi",
            "latex",
        ]
    )

    # Field weights for composite embedding
    field_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "name": 0.15,
            "name_vi": 0.20,
            "description": 0.15,
            "description_vi": 0.25,
            "latex": 0.10,
            "keywords": 0.15,
        }
    )


@dataclass
class EmbeddingResult:
    """Result of embedding operation."""

    id: str
    embedding: np.ndarray
    field: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class FormulaEmbedder:
    """
    Generate embeddings for math formulas using sentence transformers.

    Supports:
    - Field-based embeddings (separate embedding per field)
    - Composite embeddings (weighted average of fields)
    - Batch processing for efficiency
    - Caching to avoid recomputation
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize the embedder.

        Args:
            config: Embedding configuration
        """
        self.config = config or EmbeddingConfig()
        self._model = None
        self._cache: Dict[str, np.ndarray] = {}
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of the embedding model."""
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.config.model_name}")
            self._model = SentenceTransformer(
                self.config.model_name, device=self.config.device
            )
            self._initialized = True
            logger.info(
                f"Embedding model loaded. Dimension: {self._model.get_sentence_embedding_dimension()}"
            )

        except ImportError:
            logger.warning(
                "sentence-transformers not installed. Using fallback embeddings."
            )
            self._model = None
            self._initialized = True

    def _fallback_embedding(self, text: str) -> np.ndarray:
        """
        Generate a simple fallback embedding when sentence-transformers is not available.

        Uses TF-IDF-like character n-gram hashing for basic semantic similarity.
        """
        import hashlib

        # Generate deterministic embedding from text
        embedding = np.zeros(self.config.dimension, dtype=np.float32)

        # Character 3-grams
        text_lower = text.lower()
        ngrams = [text_lower[i : i + 3] for i in range(len(text_lower) - 2)]

        for ngram in ngrams:
            # Hash ngram to get indices
            hash_val = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
            idx = hash_val % self.config.dimension
            embedding[idx] += 1.0

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def embed_text(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            use_cache: Whether to use cached embeddings

        Returns:
            Embedding vector as numpy array
        """
        self._ensure_initialized()

        # Check cache
        if use_cache and self.config.cache_embeddings:
            cache_key = text[:200]  # Use first 200 chars as key
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Generate embedding
        if self._model is not None:
            embedding = self._model.encode(
                text, normalize_embeddings=self.config.normalize, show_progress_bar=False
            )
        else:
            embedding = self._fallback_embedding(text)

        # Cache result
        if use_cache and self.config.cache_embeddings:
            self._cache[cache_key] = embedding

        return embedding

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed

        Returns:
            Array of embeddings with shape (len(texts), dimension)
        """
        self._ensure_initialized()

        if self._model is not None:
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=self.config.normalize,
                batch_size=self.config.batch_size,
                show_progress_bar=len(texts) > 10,
            )
        else:
            embeddings = np.array([self._fallback_embedding(t) for t in texts])

        return embeddings

    def embed_formula(
        self, formula: Dict[str, Any], mode: str = "composite"
    ) -> Union[np.ndarray, Dict[str, EmbeddingResult]]:
        """
        Generate embeddings for a formula.

        Args:
            formula: Formula dictionary with fields
            mode: "composite" for single weighted embedding,
                  "fields" for separate embeddings per field

        Returns:
            Single embedding array (composite) or dict of EmbeddingResults (fields)
        """
        formula_id = formula.get("id", "unknown")

        if mode == "composite":
            return self._embed_formula_composite(formula)
        else:
            return self._embed_formula_fields(formula)

    def _embed_formula_composite(self, formula: Dict[str, Any]) -> np.ndarray:
        """Generate weighted composite embedding for formula."""
        weighted_embedding = np.zeros(self.config.dimension, dtype=np.float32)
        total_weight = 0.0

        for field_name, weight in self.config.field_weights.items():
            text = self._get_field_text(formula, field_name)
            if text:
                embedding = self.embed_text(text)
                weighted_embedding += weight * embedding
                total_weight += weight

        # Normalize
        if total_weight > 0:
            weighted_embedding /= total_weight

        if self.config.normalize:
            norm = np.linalg.norm(weighted_embedding)
            if norm > 0:
                weighted_embedding /= norm

        return weighted_embedding

    def _embed_formula_fields(
        self, formula: Dict[str, Any]
    ) -> Dict[str, EmbeddingResult]:
        """Generate separate embeddings for each formula field."""
        formula_id = formula.get("id", "unknown")
        results = {}

        for field_name in self.config.fields_to_embed:
            text = self._get_field_text(formula, field_name)
            if text:
                embedding = self.embed_text(text)
                results[field_name] = EmbeddingResult(
                    id=f"{formula_id}_{field_name}",
                    embedding=embedding,
                    field=field_name,
                    text=text,
                    metadata={
                        "formula_id": formula_id,
                        "category": formula.get("category", ""),
                        "topic": formula.get("topic", ""),
                    },
                )

        return results

    def _get_field_text(self, formula: Dict[str, Any], field_name: str) -> str:
        """Extract text from formula field, handling special cases."""
        if field_name == "keywords":
            # Combine keywords into single string
            keywords = formula.get("keywords", [])
            keywords_vi = formula.get("keywords_vi", [])
            return " ".join(keywords + keywords_vi)

        elif field_name == "examples":
            # Combine example problems
            examples = formula.get("examples", [])
            if examples:
                return " | ".join([ex.get("problem", "") for ex in examples[:3]])
            return ""

        else:
            return formula.get(field_name, "")

    def embed_formulas_batch(
        self, formulas: List[Dict[str, Any]], mode: str = "composite"
    ) -> Dict[str, Union[np.ndarray, Dict[str, EmbeddingResult]]]:
        """
        Generate embeddings for multiple formulas.

        Args:
            formulas: List of formula dictionaries
            mode: "composite" or "fields"

        Returns:
            Dictionary mapping formula_id to embeddings
        """
        results = {}

        for formula in formulas:
            formula_id = formula.get("id", "unknown")
            results[formula_id] = self.embed_formula(formula, mode=mode)

        return results

    def compute_similarity(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Similarity score in range [-1, 1]
        """
        if self.config.normalize:
            # For normalized vectors, dot product = cosine similarity
            return float(np.dot(embedding1, embedding2))
        else:
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(np.dot(embedding1, embedding2) / (norm1 * norm2))

    def find_similar(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: Dict[str, np.ndarray],
        top_k: int = 5,
    ) -> List[tuple]:
        """
        Find most similar embeddings to a query.

        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: Dict of candidate_id -> embedding
            top_k: Number of results to return

        Returns:
            List of (candidate_id, similarity_score) tuples
        """
        similarities = []

        for candidate_id, embedding in candidate_embeddings.items():
            sim = self.compute_similarity(query_embedding, embedding)
            similarities.append((candidate_id, sim))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()

    @property
    def model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        self._ensure_initialized()

        return {
            "model_name": self.config.model_name,
            "dimension": self.config.dimension,
            "device": self.config.device,
            "cache_size": len(self._cache),
            "model_loaded": self._model is not None,
        }
