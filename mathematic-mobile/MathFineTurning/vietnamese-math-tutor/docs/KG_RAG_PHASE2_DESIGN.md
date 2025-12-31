# KG-RAG Phase 2: Full Knowledge Graph RAG System Design

## Overview

This document outlines the design for enhancing the Vietnamese Grade 12 Math Tutor with a full Knowledge Graph-enhanced Retrieval Augmented Generation (KG-RAG) system. Building upon the simplified KG implemented in Phase 1, this system integrates semantic embeddings, hybrid retrieval, and graph-aware re-ranking.

### Goals

1. **Semantic Formula Discovery**: Find relevant formulas using natural language queries
2. **Context-Aware Retrieval**: Use graph structure to retrieve related prerequisite and application formulas
3. **Intelligent Re-ranking**: Combine semantic similarity with graph distance for optimal retrieval
4. **Learning Path Generation**: Create personalized study paths based on student knowledge state

### Current State (Phase 1)

```
┌─────────────────────────────────────────────────────────────┐
│                    Current Architecture                      │
├─────────────────────────────────────────────────────────────┤
│  FormulaDatabase          FormulaKnowledgeGraph             │
│  ├── 86 formulas          ├── 16 relation types             │
│  ├── Category search      ├── Multi-hop traversal           │
│  ├── Keyword search       ├── Prerequisite chains           │
│  └── ID lookup            └── Learning paths                │
│                                                              │
│  Limitations:                                                │
│  - No semantic search                                        │
│  - Manual keyword matching only                              │
│  - No embedding-based similarity                             │
│  - Graph and DB are separate                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 2 Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         KG-RAG Phase 2 Architecture                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────┐     ┌──────────────────────────────────────────────┐   │
│  │   Query     │     │              Hybrid Retriever                 │   │
│  │  (Vietnamese)│────▶│  ┌────────────┐    ┌─────────────────────┐  │   │
│  └─────────────┘     │  │  Semantic   │    │   Graph Traversal   │  │   │
│                      │  │  Retriever  │    │     Retriever       │  │   │
│                      │  └──────┬──────┘    └──────────┬──────────┘  │   │
│                      │         │                      │              │   │
│                      │         ▼                      ▼              │   │
│                      │  ┌────────────────────────────────────────┐  │   │
│                      │  │           Fusion & Re-ranking          │  │   │
│                      │  │  - RRF (Reciprocal Rank Fusion)        │  │   │
│                      │  │  - Graph distance weighting            │  │   │
│                      │  │  - Context relevance scoring           │  │   │
│                      │  └────────────────────────────────────────┘  │   │
│                      └──────────────────────┬───────────────────────┘   │
│                                             │                            │
│                                             ▼                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      Unified Knowledge Store                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │   Formula    │  │   Vector     │  │    Knowledge Graph   │   │   │
│  │  │   Database   │  │   Store      │  │    (Neo4j/NetworkX)  │   │   │
│  │  │   (JSON)     │  │  (ChromaDB)  │  │                      │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Embedding System

```python
# Proposed embedding configuration
embedding_config = {
    "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "dimension": 384,
    "fields_to_embed": [
        "name",           # Formula name
        "name_vi",        # Vietnamese name
        "description",    # English description
        "description_vi", # Vietnamese description
        "latex",          # LaTeX formula (for math-aware models)
        "keywords",       # Combined keywords
        "examples"        # Example problems
    ],
    "chunking": {
        "method": "field_based",  # Each field as separate chunk
        "combine_threshold": 100  # Combine short fields
    }
}
```

**Embedding Strategy**:
- **Multilingual Model**: Use `paraphrase-multilingual-MiniLM-L12-v2` for Vietnamese/English support
- **Field-Based Embedding**: Create separate embeddings for formula name, description, and examples
- **Composite Embedding**: Weighted average of field embeddings for overall formula representation

#### 2. Vector Store

```python
# ChromaDB collection schema
collection_schema = {
    "name": "math_formulas_vn",
    "metadata": {
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 200,
        "hnsw:search_ef": 100
    },
    "embedding_function": "multilingual_miniLM",
    "documents": [
        # Each formula generates multiple documents
        {
            "id": "calc_001_name",
            "content": "Đạo hàm hàm lũy thừa | Power Rule for Derivatives",
            "metadata": {
                "formula_id": "calc_001",
                "field": "name",
                "category": "calculus",
                "topic": "derivatives"
            }
        },
        {
            "id": "calc_001_description",
            "content": "Công thức tính đạo hàm của hàm lũy thừa x^n...",
            "metadata": {
                "formula_id": "calc_001",
                "field": "description",
                "category": "calculus",
                "topic": "derivatives"
            }
        }
        # ... more documents
    ]
}
```

#### 3. Knowledge Graph Enhancement

```python
# Enhanced graph schema
graph_schema = {
    "nodes": {
        "Formula": {
            "properties": ["id", "name", "name_vi", "latex", "category", "difficulty"],
            "embedding": "formula_embedding_384d"
        },
        "Concept": {
            "properties": ["id", "name", "name_vi", "description"],
            "embedding": "concept_embedding_384d"
        },
        "Topic": {
            "properties": ["id", "name", "name_vi", "parent_topic"]
        },
        "ProblemType": {
            "properties": ["id", "name", "name_vi", "solution_pattern"]
        }
    },
    "relationships": {
        "REQUIRES": {"weight": True, "description": True},
        "DERIVES_FROM": {"weight": True, "proof_sketch": True},
        "APPLIES_TO": {"problem_types": True},
        "SIMILAR_TO": {"similarity_score": True},
        "INVERSE_OF": {"bidirectional": True},
        "BELONGS_TO": {"topic_hierarchy": True},
        "PREREQUISITE_OF": {"learning_order": True}
    }
}
```

**Graph Storage Options**:

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| NetworkX | Simple, no deps, in-memory | Not persistent, limited scale | Dev/testing |
| Neo4j | Full-featured, Cypher queries | Requires server, complexity | Production |
| SQLite + custom | Lightweight, persistent | Manual graph queries | Middle ground |

**Recommended**: Start with **NetworkX + JSON persistence**, migrate to **Neo4j** for production.

#### 4. Hybrid Retriever

```python
class HybridRetriever:
    """
    Combines semantic search with graph traversal for optimal retrieval.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        knowledge_graph: FormulaKnowledgeGraph,
        semantic_weight: float = 0.6,
        graph_weight: float = 0.4
    ):
        self.vector_store = vector_store
        self.kg = knowledge_graph
        self.semantic_weight = semantic_weight
        self.graph_weight = graph_weight

    def retrieve(
        self,
        query: str,
        context_formulas: List[str] = None,  # Formulas from conversation
        k: int = 5,
        include_prerequisites: bool = True,
        include_applications: bool = False
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval pipeline:
        1. Semantic search in vector store
        2. Graph expansion from semantic results
        3. Graph-aware context retrieval
        4. Fusion and re-ranking
        """

        # Step 1: Semantic search
        semantic_results = self.vector_store.search(query, k=k*2)

        # Step 2: Graph expansion
        expanded_formulas = set()
        for result in semantic_results[:k]:
            formula_id = result.metadata["formula_id"]
            expanded_formulas.add(formula_id)

            if include_prerequisites:
                prereqs = self.kg.find_prerequisites(formula_id, max_depth=2)
                expanded_formulas.update([p.formula_id for p in prereqs])

            if include_applications:
                apps = self.kg.find_applications(formula_id, max_depth=1)
                expanded_formulas.update([a.formula_id for a in apps])

        # Step 3: Context-aware retrieval
        if context_formulas:
            for ctx_formula in context_formulas:
                related = self.kg.get_related(
                    ctx_formula,
                    relation_types=[RelationType.SIMILAR_TO, RelationType.REQUIRES],
                    max_depth=1
                )
                expanded_formulas.update([r[0] for r in related])

        # Step 4: Score and rank
        final_results = self._rank_results(
            query,
            list(expanded_formulas),
            semantic_results
        )

        return final_results[:k]

    def _rank_results(
        self,
        query: str,
        formula_ids: List[str],
        semantic_results: List[SearchResult]
    ) -> List[RetrievalResult]:
        """
        Reciprocal Rank Fusion with graph distance weighting.
        """
        scores = {}

        # Semantic scores
        for rank, result in enumerate(semantic_results):
            formula_id = result.metadata["formula_id"]
            rrf_score = 1 / (60 + rank)  # RRF constant = 60
            scores[formula_id] = scores.get(formula_id, 0) + \
                                 self.semantic_weight * rrf_score

        # Graph scores (based on centrality and connections)
        for formula_id in formula_ids:
            if formula_id not in scores:
                scores[formula_id] = 0

            centrality = self.kg.get_centrality(formula_id)
            connection_score = len(self.kg.get_neighbors(formula_id)) / 10

            scores[formula_id] += self.graph_weight * \
                                  (0.5 * centrality + 0.5 * connection_score)

        # Sort and return
        sorted_formulas = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            RetrievalResult(
                formula_id=fid,
                score=score,
                formula=self.kg.formula_db.get_formula(fid)
            )
            for fid, score in sorted_formulas
        ]
```

#### 5. Context Manager

```python
class ConversationContextManager:
    """
    Tracks conversation state for context-aware retrieval.
    """

    def __init__(self, max_history: int = 10):
        self.formula_history: List[str] = []        # Recent formula IDs
        self.topic_history: List[str] = []          # Recent topics
        self.problem_context: Dict[str, Any] = {}   # Current problem state
        self.student_knowledge: Set[str] = set()    # Known formulas
        self.max_history = max_history

    def add_formula(self, formula_id: str):
        """Track formula usage in conversation."""
        self.formula_history.append(formula_id)
        if len(self.formula_history) > self.max_history:
            self.formula_history.pop(0)

    def get_context_formulas(self, n: int = 3) -> List[str]:
        """Get recent relevant formulas for retrieval context."""
        return self.formula_history[-n:]

    def update_student_knowledge(self, formula_id: str):
        """Mark formula as understood by student."""
        self.student_knowledge.add(formula_id)

    def get_learning_gaps(
        self,
        target_formula: str,
        kg: FormulaKnowledgeGraph
    ) -> List[str]:
        """Find prerequisite formulas student hasn't learned."""
        prereqs = kg.find_prerequisites(target_formula, max_depth=3)
        return [p.formula_id for p in prereqs
                if p.formula_id not in self.student_knowledge]
```

---

## Implementation Plan

### Phase 2.1: Vector Store Integration (Week 1-2)

**Tasks**:
1. Install ChromaDB or similar lightweight vector store
2. Create embedding pipeline for formulas
3. Implement batch embedding for all 86 formulas
4. Build semantic search interface
5. Unit tests for vector operations

**Files to Create**:
```
agent/
├── retrieval/
│   ├── __init__.py
│   ├── embeddings.py      # Embedding generation
│   ├── vector_store.py    # ChromaDB wrapper
│   └── semantic_search.py # Search interface
```

**Dependencies**:
```python
# requirements.txt additions
chromadb>=0.4.0
sentence-transformers>=2.2.0
```

### Phase 2.2: Enhanced Knowledge Graph (Week 2-3)

**Tasks**:
1. Add embedding vectors to graph nodes
2. Implement graph centrality metrics
3. Add topic hierarchy nodes
4. Create problem type → formula mappings
5. Build graph persistence layer

**Files to Create/Modify**:
```
agent/
├── tools/
│   └── formula_kg.py      # Enhanced with embeddings
├── retrieval/
│   ├── graph_store.py     # Graph persistence
│   └── graph_metrics.py   # Centrality, clustering
data/
├── formulas/
│   └── knowledge_graph.json  # Enhanced schema
```

### Phase 2.3: Hybrid Retriever (Week 3-4)

**Tasks**:
1. Implement HybridRetriever class
2. Build RRF fusion algorithm
3. Add graph-aware re-ranking
4. Create retriever configuration system
5. Integration tests

**Files to Create**:
```
agent/
├── retrieval/
│   ├── hybrid_retriever.py  # Main retriever
│   ├── reranker.py          # Re-ranking logic
│   └── fusion.py            # Score fusion
```

### Phase 2.4: Context Management (Week 4-5)

**Tasks**:
1. Implement ConversationContextManager
2. Add student knowledge tracking
3. Build learning gap detection
4. Create personalized retrieval
5. Integration with chat interface

**Files to Create**:
```
agent/
├── retrieval/
│   └── context_manager.py  # Conversation tracking
chatbot/
├── session_manager.py      # Session state
```

### Phase 2.5: Integration & Testing (Week 5-6)

**Tasks**:
1. Integrate KG-RAG with MathAgent
2. Update ReAct prompts for retrieval
3. Add retrieval tools for agent
4. End-to-end testing
5. Performance optimization

---

## Technical Specifications

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB |
| Storage | 2GB | 5GB |
| GPU | Not required | CUDA for embeddings |

### Performance Targets

| Metric | Target |
|--------|--------|
| Semantic search latency | < 100ms |
| Hybrid retrieval latency | < 200ms |
| Graph traversal (2-hop) | < 50ms |
| Memory footprint | < 500MB |

### API Design

```python
# Proposed KG-RAG API
class KGRAGSystem:
    """Main interface for KG-RAG retrieval."""

    def retrieve(
        self,
        query: str,
        mode: str = "hybrid",  # "semantic", "graph", "hybrid"
        k: int = 5,
        filters: Dict[str, Any] = None,
        context: ConversationContext = None
    ) -> RetrievalResponse:
        """
        Retrieve relevant formulas for a query.

        Args:
            query: Natural language query (Vietnamese or English)
            mode: Retrieval mode
            k: Number of results
            filters: Category, topic, difficulty filters
            context: Conversation context for personalization

        Returns:
            RetrievalResponse with formulas and metadata
        """
        pass

    def get_learning_path(
        self,
        target_formula: str,
        known_formulas: List[str] = None
    ) -> LearningPath:
        """Generate optimal learning sequence."""
        pass

    def explain_relationship(
        self,
        formula_a: str,
        formula_b: str
    ) -> RelationshipExplanation:
        """Explain how two formulas are related."""
        pass
```

---

## Agent Integration

### New Tools for Agent

```python
# Tool 1: Semantic Formula Search
def semantic_search_tool(query: str, k: int = 3) -> str:
    """
    Tìm công thức bằng ngôn ngữ tự nhiên.

    Ví dụ:
    - "công thức tính đạo hàm của hàm hợp"
    - "cách tính tích phân của sin"
    - "formula for probability of independent events"
    """
    pass

# Tool 2: Find Prerequisites
def prerequisites_tool(formula_id: str) -> str:
    """
    Tìm các công thức tiên quyết cần biết trước.

    Ví dụ: prerequisites_tool("calc_006")
    → Danh sách công thức cần học trước đạo hàm hàm hợp
    """
    pass

# Tool 3: Learning Path
def learning_path_tool(target: str, known: List[str] = None) -> str:
    """
    Tạo lộ trình học tập tối ưu.

    Ví dụ: learning_path_tool("calc_012", known=["calc_001", "calc_004"])
    → Lộ trình học để hiểu tích phân từng phần
    """
    pass
```

### Updated ReAct Prompt

```python
KG_RAG_SYSTEM_PROMPT = """
Bạn là trợ lý toán học thông minh với khả năng:
1. Tìm kiếm công thức bằng ngôn ngữ tự nhiên (semantic_search)
2. Truy vấn cơ sở dữ liệu công thức (formula_db)
3. Khám phá mối quan hệ giữa các công thức (formula_kg)
4. Tìm công thức tiên quyết và ứng dụng (prerequisites, applications)
5. Tạo lộ trình học tập (learning_path)
6. Tính toán với SymPy (calculator)
7. Kiểm tra lời giải (verifier)
8. Vẽ đồ thị (plotter)

Khi học sinh hỏi về một công thức:
1. Dùng semantic_search để tìm công thức liên quan
2. Dùng formula_kg để tìm công thức tiên quyết
3. Giải thích mối quan hệ và cách áp dụng
4. Đề xuất lộ trình học nếu cần
"""
```

---

## Evaluation Metrics

### Retrieval Quality

| Metric | Formula | Target |
|--------|---------|--------|
| Precision@K | relevant_retrieved / k | > 0.8 |
| Recall@K | relevant_retrieved / total_relevant | > 0.7 |
| MRR | 1 / rank_of_first_relevant | > 0.9 |
| NDCG@K | Normalized discounted cumulative gain | > 0.85 |

### User Experience

| Metric | Description | Target |
|--------|-------------|--------|
| Answer relevance | Formula matches question intent | > 90% |
| Prerequisite accuracy | Correct prerequisite chains | > 95% |
| Learning path quality | Logical progression | > 85% user satisfaction |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Embedding quality for Vietnamese | Medium | High | Use multilingual models, fine-tune if needed |
| Graph sparsity | Low | Medium | Add implicit relationships, mine from examples |
| Latency concerns | Medium | Medium | Caching, async processing |
| Memory constraints | Low | Low | Lazy loading, pagination |

---

## Future Enhancements (Phase 3+)

1. **Fine-tuned Embeddings**: Train custom embedding model on Vietnamese math corpus
2. **Dynamic Graph Learning**: Learn new relationships from user interactions
3. **Multi-modal RAG**: Include diagrams and visual explanations
4. **Personalized Ranking**: Adapt to individual student learning patterns
5. **Explanation Generation**: Auto-generate relationship explanations
6. **Cross-lingual Retrieval**: Seamless Vietnamese-English formula search

---

## Summary

KG-RAG Phase 2 transforms the current keyword-based formula retrieval into an intelligent system combining:

- **Semantic Understanding**: Natural language queries in Vietnamese/English
- **Graph Intelligence**: Relationship-aware retrieval and learning paths
- **Hybrid Fusion**: Best of both semantic and graph-based approaches
- **Context Awareness**: Personalized retrieval based on conversation history

This enables the Math Tutor to provide more relevant, connected, and pedagogically sound responses to student queries.
