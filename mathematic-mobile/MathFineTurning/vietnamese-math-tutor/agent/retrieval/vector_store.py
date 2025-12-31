"""
Vector store for formula embeddings using ChromaDB.

Provides persistent storage and efficient similarity search for math formulas.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from .embeddings import EmbeddingConfig, FormulaEmbedder

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from vector store search."""

    id: str
    formula_id: str
    score: float
    text: str
    field: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorStoreConfig:
    """Configuration for the vector store."""

    collection_name: str = "math_formulas_vn"
    persist_directory: str = "./data/vector_store"
    embedding_config: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    distance_metric: str = "cosine"  # "cosine", "l2", "ip"


class FormulaVectorStore:
    """
    Vector store for math formula embeddings.

    Supports ChromaDB for production or a simple in-memory fallback.
    """

    def __init__(self, config: Optional[VectorStoreConfig] = None):
        """
        Initialize the vector store.

        Args:
            config: Vector store configuration
        """
        self.config = config or VectorStoreConfig()
        self.embedder = FormulaEmbedder(self.config.embedding_config)
        self._client = None
        self._collection = None
        self._fallback_store: Dict[str, Dict[str, Any]] = {}
        self._use_chromadb = False
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of the vector store."""
        if self._initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            persist_path = Path(self.config.persist_directory)
            persist_path.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.Client(
                Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=str(persist_path),
                    anonymized_telemetry=False,
                )
            )

            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": self.config.distance_metric},
            )

            self._use_chromadb = True
            logger.info(
                f"ChromaDB initialized. Collection: {self.config.collection_name}"
            )

        except ImportError:
            logger.warning("ChromaDB not installed. Using in-memory fallback store.")
            self._use_chromadb = False
            self._load_fallback_store()

        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}. Using fallback.")
            self._use_chromadb = False
            self._load_fallback_store()

        self._initialized = True

    def _load_fallback_store(self):
        """Load fallback store from disk if exists."""
        fallback_path = Path(self.config.persist_directory) / "fallback_store.json"
        if fallback_path.exists():
            try:
                with open(fallback_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert embeddings back to numpy arrays
                    for doc_id, doc in data.items():
                        if "embedding" in doc:
                            doc["embedding"] = np.array(doc["embedding"])
                    self._fallback_store = data
                logger.info(f"Loaded {len(data)} documents from fallback store")
            except Exception as e:
                logger.warning(f"Failed to load fallback store: {e}")

    def _save_fallback_store(self):
        """Save fallback store to disk."""
        fallback_path = Path(self.config.persist_directory) / "fallback_store.json"
        fallback_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Convert numpy arrays to lists for JSON serialization
            data = {}
            for doc_id, doc in self._fallback_store.items():
                data[doc_id] = {
                    k: v.tolist() if isinstance(v, np.ndarray) else v
                    for k, v in doc.items()
                }

            with open(fallback_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save fallback store: {e}")

    def add_formula(
        self, formula: Dict[str, Any], mode: str = "fields"
    ) -> List[str]:
        """
        Add a formula to the vector store.

        Args:
            formula: Formula dictionary
            mode: "fields" for separate docs per field, "composite" for single doc

        Returns:
            List of document IDs created
        """
        self._ensure_initialized()

        formula_id = formula.get("id", "unknown")
        doc_ids = []

        if mode == "fields":
            # Create separate document for each field
            embeddings = self.embedder.embed_formula(formula, mode="fields")

            for field_name, result in embeddings.items():
                doc_id = result.id

                if self._use_chromadb:
                    self._collection.add(
                        ids=[doc_id],
                        embeddings=[result.embedding.tolist()],
                        documents=[result.text],
                        metadatas=[
                            {
                                "formula_id": formula_id,
                                "field": field_name,
                                **result.metadata,
                            }
                        ],
                    )
                else:
                    self._fallback_store[doc_id] = {
                        "text": result.text,
                        "embedding": result.embedding,
                        "metadata": {
                            "formula_id": formula_id,
                            "field": field_name,
                            **result.metadata,
                        },
                    }

                doc_ids.append(doc_id)

        else:
            # Single composite document
            embedding = self.embedder.embed_formula(formula, mode="composite")
            doc_id = f"{formula_id}_composite"

            # Combine text from all fields
            text = " | ".join(
                [
                    formula.get("name_vi", ""),
                    formula.get("name", ""),
                    formula.get("description_vi", ""),
                ]
            )

            if self._use_chromadb:
                self._collection.add(
                    ids=[doc_id],
                    embeddings=[embedding.tolist()],
                    documents=[text],
                    metadatas=[
                        {
                            "formula_id": formula_id,
                            "field": "composite",
                            "category": formula.get("category", ""),
                            "topic": formula.get("topic", ""),
                        }
                    ],
                )
            else:
                self._fallback_store[doc_id] = {
                    "text": text,
                    "embedding": embedding,
                    "metadata": {
                        "formula_id": formula_id,
                        "field": "composite",
                        "category": formula.get("category", ""),
                        "topic": formula.get("topic", ""),
                    },
                }

            doc_ids.append(doc_id)

        return doc_ids

    def add_formulas_batch(
        self, formulas: List[Dict[str, Any]], mode: str = "fields"
    ) -> int:
        """
        Add multiple formulas to the vector store.

        Args:
            formulas: List of formula dictionaries
            mode: "fields" or "composite"

        Returns:
            Number of documents added
        """
        total_docs = 0

        for formula in formulas:
            doc_ids = self.add_formula(formula, mode=mode)
            total_docs += len(doc_ids)

        # Persist fallback store
        if not self._use_chromadb:
            self._save_fallback_store()

        logger.info(f"Added {total_docs} documents from {len(formulas)} formulas")
        return total_docs

    def search(
        self,
        query: str,
        k: int = 5,
        filter_category: Optional[str] = None,
        filter_field: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search for similar formulas.

        Args:
            query: Search query (Vietnamese or English)
            k: Number of results to return
            filter_category: Optional category filter
            filter_field: Optional field filter

        Returns:
            List of SearchResult objects
        """
        self._ensure_initialized()

        # Generate query embedding
        query_embedding = self.embedder.embed_text(query)

        if self._use_chromadb:
            return self._search_chromadb(
                query_embedding, k, filter_category, filter_field
            )
        else:
            return self._search_fallback(
                query_embedding, k, filter_category, filter_field
            )

    def _search_chromadb(
        self,
        query_embedding: np.ndarray,
        k: int,
        filter_category: Optional[str],
        filter_field: Optional[str],
    ) -> List[SearchResult]:
        """Search using ChromaDB."""
        # Build where clause
        where = None
        if filter_category or filter_field:
            conditions = []
            if filter_category:
                conditions.append({"category": filter_category})
            if filter_field:
                conditions.append({"field": filter_field})

            if len(conditions) == 1:
                where = conditions[0]
            else:
                where = {"$and": conditions}

        # Query ChromaDB
        results = self._collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Convert to SearchResult
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # Convert distance to similarity score
                distance = results["distances"][0][i] if results["distances"] else 0
                # For cosine distance, similarity = 1 - distance
                score = 1.0 - distance if self.config.distance_metric == "cosine" else -distance

                metadata = results["metadatas"][0][i] if results["metadatas"] else {}

                search_results.append(
                    SearchResult(
                        id=doc_id,
                        formula_id=metadata.get("formula_id", ""),
                        score=score,
                        text=results["documents"][0][i] if results["documents"] else "",
                        field=metadata.get("field", ""),
                        metadata=metadata,
                    )
                )

        return search_results

    def _search_fallback(
        self,
        query_embedding: np.ndarray,
        k: int,
        filter_category: Optional[str],
        filter_field: Optional[str],
    ) -> List[SearchResult]:
        """Search using fallback in-memory store."""
        results = []

        for doc_id, doc in self._fallback_store.items():
            metadata = doc.get("metadata", {})

            # Apply filters
            if filter_category and metadata.get("category") != filter_category:
                continue
            if filter_field and metadata.get("field") != filter_field:
                continue

            # Compute similarity
            doc_embedding = doc.get("embedding")
            if doc_embedding is None:
                continue

            score = self.embedder.compute_similarity(query_embedding, doc_embedding)

            results.append(
                SearchResult(
                    id=doc_id,
                    formula_id=metadata.get("formula_id", ""),
                    score=score,
                    text=doc.get("text", ""),
                    field=metadata.get("field", ""),
                    metadata=metadata,
                )
            )

        # Sort by score and return top k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]

    def search_by_formula_id(self, formula_id: str) -> List[SearchResult]:
        """
        Get all documents for a specific formula.

        Args:
            formula_id: Formula ID to search for

        Returns:
            List of SearchResult objects
        """
        self._ensure_initialized()

        if self._use_chromadb:
            results = self._collection.get(
                where={"formula_id": formula_id},
                include=["documents", "metadatas", "embeddings"],
            )

            search_results = []
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"]):
                    metadata = results["metadatas"][i] if results["metadatas"] else {}
                    search_results.append(
                        SearchResult(
                            id=doc_id,
                            formula_id=formula_id,
                            score=1.0,
                            text=results["documents"][i] if results["documents"] else "",
                            field=metadata.get("field", ""),
                            metadata=metadata,
                        )
                    )
            return search_results

        else:
            return [
                SearchResult(
                    id=doc_id,
                    formula_id=formula_id,
                    score=1.0,
                    text=doc.get("text", ""),
                    field=doc.get("metadata", {}).get("field", ""),
                    metadata=doc.get("metadata", {}),
                )
                for doc_id, doc in self._fallback_store.items()
                if doc.get("metadata", {}).get("formula_id") == formula_id
            ]

    def get_embedding(self, formula_id: str) -> Optional[np.ndarray]:
        """
        Get the composite embedding for a formula.

        Args:
            formula_id: Formula ID

        Returns:
            Embedding vector or None if not found
        """
        self._ensure_initialized()

        doc_id = f"{formula_id}_composite"

        if self._use_chromadb:
            results = self._collection.get(
                ids=[doc_id], include=["embeddings"]
            )
            if results["embeddings"] and results["embeddings"][0]:
                return np.array(results["embeddings"][0])
            return None

        else:
            doc = self._fallback_store.get(doc_id)
            if doc:
                return doc.get("embedding")
            return None

    def delete_formula(self, formula_id: str) -> int:
        """
        Delete all documents for a formula.

        Args:
            formula_id: Formula ID to delete

        Returns:
            Number of documents deleted
        """
        self._ensure_initialized()

        if self._use_chromadb:
            # Get all docs for this formula
            results = self._collection.get(where={"formula_id": formula_id})
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                return len(results["ids"])
            return 0

        else:
            # Find and delete from fallback store
            to_delete = [
                doc_id
                for doc_id, doc in self._fallback_store.items()
                if doc.get("metadata", {}).get("formula_id") == formula_id
            ]

            for doc_id in to_delete:
                del self._fallback_store[doc_id]

            if to_delete:
                self._save_fallback_store()

            return len(to_delete)

    def count(self) -> int:
        """Get total number of documents in the store."""
        self._ensure_initialized()

        if self._use_chromadb:
            return self._collection.count()
        else:
            return len(self._fallback_store)

    def clear(self):
        """Clear all documents from the store."""
        self._ensure_initialized()

        if self._use_chromadb:
            # Delete and recreate collection
            self._client.delete_collection(self.config.collection_name)
            self._collection = self._client.create_collection(
                name=self.config.collection_name,
                metadata={"hnsw:space": self.config.distance_metric},
            )
        else:
            self._fallback_store.clear()
            self._save_fallback_store()

        logger.info("Vector store cleared")

    def persist(self):
        """Persist changes to disk."""
        if self._use_chromadb and self._client:
            self._client.persist()
        elif not self._use_chromadb:
            self._save_fallback_store()

    @property
    def info(self) -> Dict[str, Any]:
        """Get information about the vector store."""
        self._ensure_initialized()

        return {
            "backend": "chromadb" if self._use_chromadb else "fallback",
            "collection_name": self.config.collection_name,
            "document_count": self.count(),
            "embedding_model": self.config.embedding_config.model_name,
            "dimension": self.config.embedding_config.dimension,
            "distance_metric": self.config.distance_metric,
        }
