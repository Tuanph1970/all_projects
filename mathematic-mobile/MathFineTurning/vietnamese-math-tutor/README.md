# Vietnamese Grade 12 Math Tutor 📐

A fine-tuned AI math tutor for Vietnamese Grade 12 students, combining a fine-tuned language model with an agentic tool system for accurate mathematical problem-solving.

## Features

- **Fine-tuned Model**: Qwen2.5-Math-7B-Instruct fine-tuned for Vietnamese Grade 12 math
- **ReAct Agent**: Intelligent agent with tool-use for computation and verification
- **Mathematical Tools**:
  - Calculator (SymPy-based computation)
  - Formula Database (86 Grade 12 formulas)
  - Solution Verifier
  - Graph Plotter (Matplotlib)
- **KG-RAG System** (Phase 2):
  - Semantic Formula Search (Vietnamese/English)
  - Knowledge Graph with 16 relationship types
  - Hybrid Retrieval (semantic + graph-based with RRF fusion)
  - Learning Path Generation
  - Student Progress Tracking
- **Textbook Data Import**: Easy integration of new problems and solutions
- **Gradio Web Interface**: User-friendly chat interface with multiple modes
- **8-bit Quantization**: Optimized for RTX 3060 12GB VRAM

## Supported Topics

| Topic | Vietnamese | Content |
|-------|------------|---------|
| Calculus | Giải tích | Derivatives, integrals, limits, optimization |
| Trigonometry | Lượng giác | Identities, equations, graphs |
| Geometry | Hình học | Spatial geometry, coordinate geometry, volumes |
| Probability | Xác suất | Combinations, permutations, probability |

## Installation

### Prerequisites

- Python 3.9+
- CUDA 11.8+ (for GPU support)
- RTX 3060 12GB or better (recommended)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd vietnamese-math-tutor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```bash
# 1. Import sample textbook data (optional)
python scripts/import_textbook_data.py --use-samples

# 2. Train the model
python run_train.py

# 3. Run the chatbot
python run_app.py --model output/final/final_model
```

## Usage

### 1. Training the Model

```bash
# Train with default settings
python run_train.py

# Train with custom parameters
python training/train.py --epochs 3 --batch-size 2 --lr 2e-5

# Dry run (validate setup without training)
python training/train.py --dry-run

# Resume from checkpoint
python training/train.py --resume output/checkpoints/checkpoint-500
```

### 2. Running the Chatbot

```bash
# Run with base model (no fine-tuning)
python run_app.py

# Run with fine-tuned model
python run_app.py --model output/final/final_model

# Create public share link
python run_app.py --model output/final/final_model --share
```

### 3. Adding Textbook Data

You can enrich the model with your own textbook problems and solutions:

```bash
# Import sample data to see the format
python scripts/import_textbook_data.py --use-samples

# Validate your data without importing
python scripts/import_textbook_data.py --source my_textbook.json --validate-only

# Import your textbook data
python scripts/import_textbook_data.py --source my_textbook.json
```

#### Textbook Data Format

Create a JSON file with problems from your textbook:

```json
{
  "problems": [
    {
      "id": "textbook_calc_001",
      "source": "SGK Toán 12, Trang 45",
      "question": "Tính đạo hàm của hàm số y = (2x + 1)^5",
      "solution": "**Bước 1:** Nhận dạng - đây là hàm hợp\n**Bước 2:** Áp dụng công thức (u^n)' = n·u^(n-1)·u'\n**Bước 3:** y' = 5(2x+1)^4 · 2 = 10(2x+1)^4",
      "answer": "y' = 10(2x+1)^4",
      "topic": "calculus",
      "subtopic": "chain_rule",
      "difficulty": "medium",
      "formulas_used": ["calc_006", "calc_001"],
      "keywords": ["đạo hàm", "hàm hợp"]
    }
  ],
  "formula_updates": [
    {
      "formula_id": "calc_006",
      "action": "add_examples",
      "examples": [
        {
          "id": "calc_006_ex1",
          "problem": "Tính đạo hàm: y = sin(3x)",
          "solution_steps": ["Đặt u = 3x", "y' = cos(u)·u' = 3cos(3x)"],
          "answer": "y' = 3cos(3x)",
          "difficulty": "easy"
        }
      ]
    }
  ],
  "new_relationships": [
    {
      "source": "calc_006",
      "target": "calc_007",
      "type": "used_in",
      "weight": 0.9,
      "description_vi": "Đạo hàm hàm hợp dùng với đạo hàm lượng giác"
    }
  ]
}
```

**Data Integration Points:**

| Data Type | Target | Purpose |
|-----------|--------|---------|
| `problems` | Fine-tuning dataset | Teaches model HOW to solve |
| `formula_updates` | Formula database | Improves retrieval with examples |
| `new_relationships` | Knowledge Graph | Connects concepts for better recommendations |

### 4. Using Tools Directly

```python
from agent.tools import calculator_tool, formula_db_tool, verifier_tool, plotter_tool

# Calculate derivative
result = calculator_tool("derivative", expression="x^3 - 3*x^2 + 2*x", variable="x")
print(result["result"])  # 3*x**2 - 6*x + 2

# Search formulas
result = formula_db_tool(action="search", query="đạo hàm", language="vi")
for formula in result["results"]:
    print(f"{formula['name']}: {formula['formula']}")

# Verify calculation
result = verifier_tool(action="verify_derivative", expression="x^2", claimed_result="2*x")
print(result["is_correct"])  # True

# Plot function
result = plotter_tool(action="plot_function", expression="x^3 - 3*x", x_range=(-3, 3))
print(result["image_path"])
```

### 5. Using KG-RAG Tools

```python
from agent.tools import (
    semantic_search_tool,
    find_prerequisites_tool,
    learning_path_tool,
    find_similar_tool,
    get_weak_areas_tool,
)

# Semantic search (natural language in Vietnamese)
result = semantic_search_tool("đạo hàm hàm hợp", top_k=3)
for r in result["results"]:
    print(f"{r['name']}: score={r['score']:.2f}")

# Find prerequisites for a formula
result = find_prerequisites_tool("calc_012")  # Integration by parts
print(result["explanation"])

# Generate learning path
result = learning_path_tool("calc_010", known_formulas=["calc_001"])
for step in result["path"]:
    print(f"{step['step']}. {step['name']}")

# Find similar formulas
result = find_similar_tool("calc_004")  # Product rule
for s in result["similar"]:
    print(f"{s['name']}: {s['similarity']:.0%}")

# Get weak areas analysis
result = get_weak_areas_tool()
print(result["explanation"])
```

## Project Structure

```
vietnamese-math-tutor/
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── run_app.py               # Quick start chatbot
├── run_train.py             # Quick start training
│
├── data/
│   ├── grade12_math_dataset.json  # Training data
│   ├── formulas/             # Formula databases
│   │   ├── calculus.json     # 25 calculus formulas
│   │   ├── geometry.json     # 20 geometry formulas
│   │   ├── probability.json  # 21 probability formulas
│   │   ├── trigonometry.json # 20 trigonometry formulas
│   │   └── knowledge_graph.json  # KG relationships
│   ├── samples/              # Sample data for import
│   │   ├── sample_finetuning_data.json
│   │   ├── sample_formula_enrichment.json
│   │   └── sample_kg_enrichment.json
│   ├── vector_store/         # Semantic search embeddings
│   ├── dataset_loader.py     # Data loading utilities
│   └── data_validator.py     # Data validation
│
├── training/
│   ├── train.py              # Main training script
│   ├── model_config.py       # Model loading & LoRA config
│   └── trainer_utils.py      # Training utilities
│
├── agent/
│   ├── math_agent.py         # ReAct agent controller
│   ├── agent_prompts.py      # System prompts
│   ├── tools/
│   │   ├── calculator.py     # SymPy calculator
│   │   ├── formula_db.py     # Formula database
│   │   ├── formula_kg.py     # Knowledge Graph
│   │   ├── kg_rag_tools.py   # KG-RAG tool interfaces
│   │   ├── verifier.py       # Solution verifier
│   │   └── plotter.py        # Graph plotter
│   └── retrieval/            # KG-RAG System (Phase 2)
│       ├── embeddings.py     # Multilingual embeddings
│       ├── vector_store.py   # ChromaDB vector store
│       ├── semantic_search.py # Semantic search
│       ├── graph_metrics.py  # PageRank, centrality
│       ├── hybrid_retriever.py # RRF fusion retrieval
│       └── context_manager.py # Student progress tracking
│
├── chatbot/
│   ├── app.py                # Gradio web interface
│   ├── inference.py          # Simple inference
│   └── agent_inference.py    # Agent-based inference
│
├── scripts/
│   └── import_textbook_data.py  # Textbook data importer
│
├── docs/
│   └── KG_RAG_PHASE2_DESIGN.md # KG-RAG design document
│
├── utils/
│   ├── logger.py             # Logging utilities
│   └── helpers.py            # Helper functions
│
└── output/
    ├── checkpoints/          # Training checkpoints
    └── final/                # Final models
```

## Configuration

Edit `config.py` to customize:

```python
# Model settings
model.name = "Qwen/Qwen2.5-Math-7B-Instruct"
model.quantization_bits = 8  # 4 or 8

# LoRA settings
lora.r = 64
lora.alpha = 128
lora.dropout = 0.05

# Training settings
training.num_epochs = 5
training.batch_size = 4
training.learning_rate = 2e-5
```

## Two Inference Modes

### Simple Mode
- Direct model inference without tools
- Faster response time (~1-2s)
- Good for simple questions

### Agent Mode
- Uses ReAct pattern with tool orchestration
- Accurate computation via Calculator
- Formula lookup from database with KG-RAG
- Solution verification
- Graph generation
- Learning path recommendations

## API Reference

### Calculator Tool

```python
calculator_tool(
    operation: str,      # eval, derivative, integral, limit, solve, simplify
    expression: str,     # Mathematical expression
    variable: str = "x", # Variable name
    **kwargs            # Additional parameters (lower, upper for integrals)
)
```

### Formula DB Tool

```python
formula_db_tool(
    action: str,         # search, get, list_category
    query: str = "",     # Search query
    category: str = None,# Filter: calculus, trigonometry, geometry, probability
    language: str = "vi" # Output language
)
```

### Verifier Tool

```python
verifier_tool(
    action: str,            # verify_calculation, verify_derivative, verify_integral
    expression: str,        # Original expression
    claimed_result: str,    # Result to verify
    expected_answer: str = None
)
```

### Plotter Tool

```python
plotter_tool(
    action: str,            # plot_function, plot_derivative, plot_integral
    expression: str,        # Function expression
    x_range: tuple = (-10, 10),
    language: str = "vi"
)
```

### KG-RAG Tools (Phase 2)

```python
# Semantic search - natural language formula discovery
semantic_search_tool(
    query: str,             # Vietnamese or English query
    top_k: int = 5,         # Number of results
    category: str = None,   # Filter by category
    language: str = "vi"    # Output language
)

# Find prerequisite formulas
find_prerequisites_tool(
    formula_id: str,        # Target formula ID
    max_depth: int = 3,     # Search depth
    language: str = "vi"
)

# Find applications of a formula
find_applications_tool(
    formula_id: str,        # Source formula ID
    max_depth: int = 2,
    language: str = "vi"
)

# Generate optimal learning path
learning_path_tool(
    target_formula: str,    # Formula to learn
    known_formulas: List[str] = None,  # Already known
    language: str = "vi"
)

# Find similar formulas
find_similar_tool(
    formula_id: str,        # Reference formula
    top_k: int = 5,
    language: str = "vi"
)

# Analyze weak areas and get recommendations
get_weak_areas_tool(language: str = "vi")

# Record practice results for progress tracking
record_practice_result(
    formula_id: str,        # Formula practiced
    correct: bool,          # Was answer correct
    problem_text: str = "", # Problem statement
    topic: str = ""         # Problem topic
)
```

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | RTX 3060 12GB | RTX 4090 24GB |
| RAM | 16GB | 32GB |
| Storage | 20GB | 50GB |

## Performance

| Metric | Value |
|--------|-------|
| Training | ~2 hours for 5 epochs on 50 samples (RTX 3060) |
| Inference (Simple) | ~1-2 seconds per response |
| Inference (Agent) | ~3-5 seconds per response |
| Memory Usage | ~8GB VRAM (8-bit quantization) |
| Semantic Search | <100ms latency |
| Hybrid Retrieval | <200ms latency |

## Knowledge Graph Statistics

| Metric | Value |
|--------|-------|
| Total Formulas | 86 |
| Relationship Types | 16 |
| Explicit Relationships | ~50 |
| Auto-generated Relationships | ~200 |
| Problem Type Mappings | 8 categories |

## Fine-tuning vs RAG: When to Use Each

Understanding when to add data to fine-tuning vs RAG/Knowledge Graph is crucial for optimal results.

### Quick Decision Guide

```
┌─────────────────────────────────────────────────────────────┐
│                    DECISION GUIDE                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Is this about HOW to solve?                                 │
│  ├─ YES → Fine-tuning                                        │
│  │        • Problem-solving steps                            │
│  │        • Reasoning patterns                               │
│  │        • Solution methodology                             │
│  │                                                           │
│  └─ NO → Is this factual knowledge?                          │
│          ├─ YES → RAG/KG                                     │
│          │        • Formula definitions                      │
│          │        • Concept relationships                    │
│          │        • Reference information                    │
│          │                                                   │
│          └─ BOTH → Add to both!                              │
│                    Fine-tune on solutions                    │
│                    RAG for formula lookup                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Fine-tuning (Training Data)

**Purpose**: Teaches the model **HOW** to solve problems

| Use Case | Example |
|----------|---------|
| Problem-solving patterns | Step-by-step derivative calculation |
| Reasoning style | Vietnamese math terminology and explanations |
| Output formats | "Bước 1... Bước 2... Kết quả:" structure |
| Solution strategies | LIATE rule for integration by parts |
| Conversational ability | Teacher-student dialogue patterns |

**Best for**: Worked examples, multi-step problems, exam-style questions, dialogue explanations

### RAG/Knowledge Graph

**Purpose**: Provides **WHAT** knowledge to retrieve at inference time

| Use Case | Example |
|----------|---------|
| Factual formulas | `(u·v)' = u'v + uv'` |
| Relationships | "Chain rule requires basic derivative" |
| Formula lookup | "Find all integration formulas" |
| Prerequisites | "Before integration by parts, learn basic integrals" |
| Reference materials | Formula definitions, conditions, edge cases |

**Best for**: Formula definitions, concept relationships, quick-reference tables, common mistakes

### Content Type Decision Matrix

| Content Type | Fine-tuning | RAG/KG | Notes |
|--------------|:-----------:|:------:|-------|
| Worked examples with reasoning | ✅ Primary | ⚪ Optional | Teaches problem-solving |
| Formula definitions | ⚪ Optional | ✅ Primary | Factual reference |
| Concept relationships | ❌ No | ✅ Primary | Graph structure |
| Common mistakes | ⚪ Optional | ✅ Primary | Warning knowledge |
| Problem-solving dialogues | ✅ Primary | ❌ No | Conversational patterns |
| Prerequisite chains | ❌ No | ✅ Primary | Learning paths |
| Exam-style problems | ✅ Primary | ⚪ Optional | Pattern training |

### Practical Example

For the problem "Tính đạo hàm y = (2x+1)^5":

| Component | Target | Reason |
|-----------|--------|--------|
| Full solution with steps | Fine-tuning | Teaches reasoning process |
| Chain rule formula | RAG (Formula DB) | Factual reference |
| "Chain rule requires basic derivative" | RAG (KG relationship) | Concept connection |
| Common mistake: "forgetting inner derivative" | RAG (KG enrichment) | Reference knowledge |

**Rule of thumb**:
- **Fine-tuning** = Teaching a student to think
- **RAG/KG** = Giving a student a reference book

## Workflow: Adding Your Textbook

```
┌─────────────────────────────────────────────────────────────┐
│                    Textbook Integration                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Extract problems from textbook                           │
│     ↓                                                        │
│  2. Format as JSON (see data/samples/)                       │
│     ↓                                                        │
│  3. Run import script                                        │
│     python scripts/import_textbook_data.py --source file.json│
│     ↓                                                        │
│  4. Re-train model                                           │
│     python run_train.py                                      │
│     ↓                                                        │
│  5. Test with chatbot                                        │
│     python run_app.py --model output/final/final_model       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## License

MIT License

## Acknowledgments

- Qwen2.5-Math by Alibaba Cloud
- Hugging Face Transformers
- SymPy for symbolic computation
- Sentence Transformers for embeddings
- ChromaDB for vector storage
- Gradio for the web interface
