# Vietnamese Grade 12 Math Tutor - System Design Document v2.0

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Approach Comparison](#3-approach-comparison)
4. [Component Specifications](#4-component-specifications)
5. [Agent & Tools Design](#5-agent--tools-design)
6. [Grade 12 Curriculum Coverage](#6-grade-12-curriculum-coverage)
7. [Data Flow & API Contracts](#7-data-flow--api-contracts)
8. [Implementation Phases](#8-implementation-phases)
9. [Technical Implementation Details](#9-technical-implementation-details)

---

## 1. Executive Summary

### 1.1 Project Overview
A Vietnamese **Grade 12** Math Tutor system featuring:
- **Fine-tuning pipeline** for Qwen2.5-Math-7B-Instruct on Vietnamese math problems
- **Agentic/Tool-RAG** system for computation verification and formula retrieval
- Optimized for **RTX 3060 (12GB VRAM)** with 8-bit quantization
- **Bilingual support** (Vietnamese primary, English secondary)
- **Gradio chatbot interface** with dual inference modes

### 1.2 Key Changes from v1.0
| Aspect | v1.0 | v2.0 |
|--------|------|------|
| Grade Focus | 8-12 | **12 only** |
| Approach | Fine-tuning only | **Fine-tuning + Agentic/Tool-RAG** |
| Inference | Single model | **Dual mode** (model-only / agent) |
| Tools | None | **Calculator, Formula DB, Verifier, Plotter** |

### 1.3 Architecture Decision

**Chosen Approach: Fine-tuning + Agentic/Tool-RAG**

```
+------------------------------------------------------------------+
|                    DUAL-MODE INFERENCE                            |
+------------------------------------------------------------------+
|                                                                    |
|   Mode 1: Fine-tuned Model Only          Mode 2: Full Agent       |
|   +------------------------+         +------------------------+   |
|   | Fast, lightweight      |         | Accurate, verified     |   |
|   | Good for simple Qs     |         | For complex problems   |   |
|   | Lower latency          |         | Multi-step reasoning   |   |
|   +------------------------+         +------------------------+   |
|                                                                    |
|   User can choose: --mode simple | --mode agent                   |
+------------------------------------------------------------------+
```

### 1.4 Hardware Requirements
- **Minimum**: RTX 3060 12GB, 32GB RAM, 50GB storage
- **Recommended**: RTX 3080+ 16GB+, 64GB RAM, 100GB storage

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
+===========================================================================+
|                 VIETNAMESE GRADE 12 MATH TUTOR SYSTEM                      |
+===========================================================================+
|                                                                            |
|  USER INPUT                                                                |
|      |                                                                     |
|      v                                                                     |
|  +----------------+     +------------------+                               |
|  | Language       |---->| Mode Selection   |                               |
|  | Detection      |     | (simple/agent)   |                               |
|  +----------------+     +--------+---------+                               |
|                                  |                                         |
|            +---------------------+---------------------+                   |
|            |                                           |                   |
|            v                                           v                   |
|  +------------------+                     +---------------------------+   |
|  | MODE: SIMPLE     |                     | MODE: AGENT               |   |
|  |                  |                     |                           |   |
|  | Fine-tuned       |                     | +----------------------+  |   |
|  | Qwen Model       |                     | | Agent Controller     |  |   |
|  | (Direct Gen)     |                     | | (ReAct Loop)         |  |   |
|  +--------+---------+                     | +----------+-----------+  |   |
|           |                               |            |              |   |
|           |                               |  +---------+---------+    |   |
|           |                               |  |                   |    |   |
|           |                               |  v                   v    |   |
|           |                     +-----------+-------+  +-----------+  |   |
|           |                     | TOOLS             |  | Fine-tuned|  |   |
|           |                     | +---------------+ |  | Model     |  |   |
|           |                     | | Calculator    | |  | (Reasoner)|  |   |
|           |                     | | (SymPy)       | |  +-----------+  |   |
|           |                     | +---------------+ |                 |   |
|           |                     | | Formula DB    | |                 |   |
|           |                     | | (JSON/Vector) | |                 |   |
|           |                     | +---------------+ |                 |   |
|           |                     | | Step Verifier | |                 |   |
|           |                     | +---------------+ |                 |   |
|           |                     | | Graph Plotter | |                 |   |
|           |                     | | (Matplotlib)  | |                 |   |
|           |                     | +---------------+ |                 |   |
|           |                     +-------------------+                 |   |
|           |                               |                           |   |
|           +---------------+---------------+                           |   |
|                           |                                           |   |
|                           v                                           |   |
|                  +------------------+                                  |   |
|                  | Response         |                                  |   |
|                  | Formatter        |                                  |   |
|                  +--------+---------+                                  |   |
|                           |                                            |   |
|                           v                                            |   |
|                  +------------------+                                  |   |
|                  | Gradio UI        |                                  |   |
|                  | (Streaming)      |                                  |   |
|                  +------------------+                                  |   |
|                                                                        |   |
+===========================================================================+
```

### 2.2 Project Structure

```
vietnamese-math-tutor/
├── config.py                    # Centralized configuration
├── requirements.txt             # All dependencies
├── README.md                    # Documentation (EN/VI)
├── .gitignore
│
├── data/
│   ├── __init__.py
│   ├── grade12_math_dataset.json    # Grade 12 problems (50+ problems)
│   ├── dataset_loader.py            # Load, format, split
│   ├── data_validator.py            # JSON schema validation
│   └── formulas/                    # Formula databases
│       ├── calculus.json            # Derivatives, integrals
│       ├── geometry.json            # Spatial geometry formulas
│       ├── probability.json         # Probability & statistics
│       └── trigonometry.json        # Trig identities
│
├── training/
│   ├── __init__.py
│   ├── train.py                 # Main training script
│   ├── model_config.py          # Model loading with quantization
│   └── trainer_utils.py         # Callbacks, metrics
│
├── agent/                       # NEW: Agentic System
│   ├── __init__.py
│   ├── math_agent.py            # ReAct agent controller
│   ├── agent_prompts.py         # Agent system prompts
│   └── tools/
│       ├── __init__.py
│       ├── calculator.py        # SymPy computation tool
│       ├── formula_db.py        # Formula retrieval tool
│       ├── verifier.py          # Step verification tool
│       └── plotter.py           # Graph plotting tool
│
├── chatbot/
│   ├── __init__.py
│   ├── app.py                   # Gradio interface (dual mode)
│   ├── inference.py             # Model inference
│   ├── agent_inference.py       # Agent inference (NEW)
│   ├── language_detector.py     # Vietnamese/English detection
│   └── prompts.py               # System prompts
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py               # Common utilities
│   └── logger.py                # Logging configuration
│
├── output/
│   ├── checkpoints/
│   ├── final_model/
│   └── logs/
│
└── tests/
    ├── test_dataset.py
    ├── test_training.py
    ├── test_agent.py            # NEW
    └── test_tools.py            # NEW
```

---

## 3. Approach Comparison

### 3.1 Why Fine-tuning + Agentic/Tool-RAG?

| Requirement | Fine-tuning | Agent Tools | Combined |
|-------------|-------------|-------------|----------|
| Vietnamese terminology | ✅ Excellent | ❌ N/A | ✅ |
| Step-by-step style | ✅ Excellent | ⚠️ Partial | ✅ |
| Computation accuracy | ⚠️ Can hallucinate | ✅ Calculator verifies | ✅ |
| Formula precision | ⚠️ May forget | ✅ DB lookup | ✅ |
| Complex multi-step | ⚠️ May lose track | ✅ Agent orchestrates | ✅ |
| Function graphing | ❌ Cannot | ✅ Matplotlib | ✅ |
| Solution verification | ❌ Cannot self-verify | ✅ Verifier tool | ✅ |

### 3.2 When to Use Each Mode

```
+---------------------------+----------------------------------+
| MODE: SIMPLE              | MODE: AGENT                      |
| (Fine-tuned model only)   | (Full agentic system)            |
+---------------------------+----------------------------------+
| - Quick concept questions | - Complex multi-step problems    |
| - Definition queries      | - Numerical computation heavy    |
| - Simple derivatives      | - Function analysis (khao sat)   |
| - Formula explanations    | - Geometry calculations          |
| - Low latency needed      | - Need verification              |
| - ~2-5 seconds response   | - ~10-30 seconds response        |
+---------------------------+----------------------------------+
```

### 3.3 Agent Workflow Example

```
User: "Tim cuc tri cua ham so y = x^3 - 3x^2 + 4"

Agent Thinking:
┌─────────────────────────────────────────────────────────────┐
│ Step 1: THINK                                               │
│ This is a function extrema problem. Need to:                │
│ 1. Find derivative                                          │
│ 2. Solve y' = 0                                             │
│ 3. Determine max/min using second derivative or sign table  │
│                                                             │
│ Step 2: ACTION - Use Calculator Tool                        │
│ Input: derivative of x^3 - 3x^2 + 4                         │
│ Output: 3x^2 - 6x                                           │
│                                                             │
│ Step 3: ACTION - Use Calculator Tool                        │
│ Input: solve 3x^2 - 6x = 0                                  │
│ Output: x = 0, x = 2                                        │
│                                                             │
│ Step 4: ACTION - Use Calculator Tool                        │
│ Input: evaluate x^3 - 3x^2 + 4 at x=0 and x=2              │
│ Output: y(0) = 4, y(2) = 0                                  │
│                                                             │
│ Step 5: ACTION - Use Formula DB                             │
│ Query: "second derivative test for extrema"                 │
│ Output: If y''(x0) > 0 → min, if y''(x0) < 0 → max         │
│                                                             │
│ Step 6: ACTION - Use Calculator Tool                        │
│ Input: second derivative of x^3 - 3x^2 + 4                  │
│ Output: 6x - 6                                              │
│ y''(0) = -6 < 0 → max at x=0                               │
│ y''(2) = 6 > 0 → min at x=2                                │
│                                                             │
│ Step 7: ACTION - Use Verifier Tool                          │
│ Verify: max(0,4), min(2,0) for y = x^3 - 3x^2 + 4          │
│ Output: VERIFIED ✓                                          │
│                                                             │
│ Step 8: RESPOND - Generate Vietnamese explanation           │
└─────────────────────────────────────────────────────────────┘

Final Response:
**Bài giải:**

**Bước 1: Tìm đạo hàm**
y' = 3x² - 6x = 3x(x - 2)

**Bước 2: Tìm nghiệm y' = 0**
y' = 0 ⟺ x = 0 hoặc x = 2

**Bước 3: Xét dấu đạo hàm cấp hai**
y'' = 6x - 6
- y''(0) = -6 < 0 → x = 0 là điểm cực đại
- y''(2) = 6 > 0 → x = 2 là điểm cực tiểu

**Bước 4: Tính giá trị cực trị**
- Cực đại: y(0) = 4 → Điểm cực đại (0, 4)
- Cực tiểu: y(2) = 0 → Điểm cực tiểu (2, 0)

**Đáp án:**
- Cực đại tại (0, 4)
- Cực tiểu tại (2, 0)
```

---

## 4. Component Specifications

### 4.1 Configuration (`config.py`)

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

@dataclass
class Config:
    # Project Info
    PROJECT_NAME: str = "Vietnamese Grade 12 Math Tutor"
    VERSION: str = "2.0.0"

    # Model Configuration
    MODEL_NAME: str = "Qwen/Qwen2.5-Math-7B-Instruct"
    QUANTIZATION_BITS: int = 8
    DEVICE_MAP: str = "auto"

    # LoRA Configuration
    LORA_R: int = 64
    LORA_ALPHA: int = 128
    LORA_DROPOUT: float = 0.05
    LORA_TARGET_MODULES: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj"
    ])

    # Training Configuration
    NUM_EPOCHS: int = 5
    BATCH_SIZE: int = 4
    GRADIENT_ACCUMULATION_STEPS: int = 4
    LEARNING_RATE: float = 2e-4
    LR_SCHEDULER: str = "cosine"
    FP16: bool = True
    MAX_LENGTH: int = 2048

    # Dataset Configuration (Grade 12 ONLY)
    GRADE: int = 12
    TRAIN_SPLIT: float = 0.85
    VAL_SPLIT: float = 0.15

    # Agent Configuration
    AGENT_ENABLED: bool = True
    AGENT_MAX_ITERATIONS: int = 10
    AGENT_TIMEOUT: int = 60  # seconds

    # Tool Configuration
    CALCULATOR_ENABLED: bool = True
    FORMULA_DB_ENABLED: bool = True
    VERIFIER_ENABLED: bool = True
    PLOTTER_ENABLED: bool = True

    # Inference Modes
    INFERENCE_MODES: List[str] = field(default_factory=lambda: [
        "simple",  # Fine-tuned model only
        "agent"    # Full agentic system
    ])
    DEFAULT_MODE: str = "agent"

    # Paths
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    CHECKPOINT_DIR: Path = OUTPUT_DIR / "checkpoints"
    LOG_DIR: Path = OUTPUT_DIR / "logs"
    FORMULA_DIR: Path = DATA_DIR / "formulas"
```

### 4.2 Grade 12 Dataset Schema

```json
{
  "metadata": {
    "version": "2.0.0",
    "grade": 12,
    "curriculum": "Vietnamese National Curriculum 2025",
    "description": "Grade 12 Math Problems for Fine-tuning",
    "topics": [
      "calculus",
      "spatial_geometry",
      "coordinate_geometry",
      "probability_statistics"
    ]
  },
  "problems": [
    {
      "id": "calc_g12_001",
      "question": "Khảo sát sự biến thiên và vẽ đồ thị hàm số y = x³ - 3x² + 4",
      "solution": "**Phân tích đề bài:**\n...\n**Bước 1:**...",
      "answer": "Cực đại (0, 4), Cực tiểu (2, 0)",
      "grade": 12,
      "topic": "calculus",
      "subtopic": "function_analysis",
      "difficulty": "trung bình",
      "language": "vi",
      "requires_computation": true,
      "requires_graph": true,
      "keywords": ["khảo sát hàm số", "cực trị", "đồ thị"],
      "formulas_used": [
        "derivative_power_rule",
        "second_derivative_test"
      ],
      "hints": [
        "Tìm đạo hàm y'",
        "Giải phương trình y' = 0",
        "Xét dấu y'' hoặc lập bảng biến thiên"
      ],
      "common_mistakes": [
        "Nhầm dấu khi tính đạo hàm",
        "Quên kiểm tra cực đại/cực tiểu"
      ],
      "verification_steps": [
        "Thay x = 0 vào y kiểm tra giá trị",
        "Kiểm tra dấu y'' tại các điểm tới hạn"
      ]
    }
  ]
}
```

---

## 5. Agent & Tools Design

### 5.1 Math Agent (`agent/math_agent.py`)

```python
"""
ReAct-style agent for Vietnamese Grade 12 Math problems.

The agent follows a Think-Act-Observe loop:
1. THINK: Analyze the problem and plan approach
2. ACT: Use appropriate tool (calculator, formula_db, verifier, plotter)
3. OBSERVE: Process tool output
4. Repeat until solution is complete
5. RESPOND: Generate Vietnamese explanation
"""

from typing import List, Dict, Optional, Generator
from dataclasses import dataclass
from enum import Enum

class ToolType(Enum):
    CALCULATOR = "calculator"
    FORMULA_DB = "formula_db"
    VERIFIER = "verifier"
    PLOTTER = "plotter"
    REASONER = "reasoner"  # The fine-tuned model

@dataclass
class AgentAction:
    tool: ToolType
    input: str
    thought: str

@dataclass
class AgentObservation:
    tool: ToolType
    output: str
    success: bool

class MathAgent:
    """
    Orchestrates math problem solving using tools and the fine-tuned model.

    Architecture:
    - Uses fine-tuned Qwen model as the "brain" for reasoning
    - Tools provide reliable computation and verification
    - ReAct loop for multi-step problem solving
    """

    def __init__(
        self,
        model,
        tokenizer,
        calculator_tool,
        formula_db_tool,
        verifier_tool,
        plotter_tool,
        max_iterations: int = 10
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.tools = {
            ToolType.CALCULATOR: calculator_tool,
            ToolType.FORMULA_DB: formula_db_tool,
            ToolType.VERIFIER: verifier_tool,
            ToolType.PLOTTER: plotter_tool,
        }
        self.max_iterations = max_iterations

    def solve(
        self,
        problem: str,
        language: str = "vi"
    ) -> Generator[str, None, None]:
        """
        Solve a math problem using the agent loop.

        Yields partial responses for streaming.
        """
        pass

    def _think(self, problem: str, history: List) -> AgentAction:
        """Determine next action based on problem and history."""
        pass

    def _act(self, action: AgentAction) -> AgentObservation:
        """Execute the chosen tool."""
        pass

    def _should_finish(self, history: List) -> bool:
        """Check if problem is solved."""
        pass

    def _format_response(
        self,
        problem: str,
        history: List,
        language: str
    ) -> str:
        """Format final response in Vietnamese/English."""
        pass
```

### 5.2 Calculator Tool (`agent/tools/calculator.py`)

```python
"""
SymPy-based calculator for mathematical computations.

Capabilities:
- Symbolic differentiation
- Symbolic integration
- Equation solving
- Expression simplification
- Numerical evaluation
- Matrix operations
- Trigonometric simplifications
"""

from sympy import (
    symbols, diff, integrate, solve, simplify,
    sin, cos, tan, exp, log, sqrt, pi, E,
    Matrix, limit, series, factorial, binomial
)
from sympy.parsing.sympy_parser import parse_expr
from typing import Union, List, Dict

class CalculatorTool:
    """
    Mathematical computation tool using SymPy.

    Supports:
    - Derivatives: diff(expr, var)
    - Integrals: integrate(expr, var) or integrate(expr, (var, a, b))
    - Solve: solve(equation, var)
    - Simplify: simplify(expr)
    - Evaluate: expr.evalf()
    - Limits: limit(expr, var, point)
    """

    def __init__(self):
        self.x, self.y, self.z = symbols('x y z')
        self.t, self.n, self.k = symbols('t n k')

    def derivative(self, expr_str: str, var: str = "x", order: int = 1) -> str:
        """
        Compute derivative.

        Example:
            derivative("x**3 - 3*x**2 + 4", "x") -> "3*x**2 - 6*x"
        """
        expr = parse_expr(expr_str)
        var_sym = symbols(var)
        result = diff(expr, var_sym, order)
        return str(simplify(result))

    def integrate_indefinite(self, expr_str: str, var: str = "x") -> str:
        """
        Compute indefinite integral.

        Example:
            integrate_indefinite("3*x**2 - 6*x", "x") -> "x**3 - 3*x**2"
        """
        expr = parse_expr(expr_str)
        var_sym = symbols(var)
        result = integrate(expr, var_sym)
        return str(simplify(result))

    def integrate_definite(
        self, expr_str: str, var: str, lower: float, upper: float
    ) -> str:
        """
        Compute definite integral.

        Example:
            integrate_definite("x**2", "x", 0, 1) -> "1/3"
        """
        expr = parse_expr(expr_str)
        var_sym = symbols(var)
        result = integrate(expr, (var_sym, lower, upper))
        return str(simplify(result))

    def solve_equation(self, equation_str: str, var: str = "x") -> List[str]:
        """
        Solve equation (assumes = 0).

        Example:
            solve_equation("3*x**2 - 6*x", "x") -> ["0", "2"]
        """
        expr = parse_expr(equation_str)
        var_sym = symbols(var)
        solutions = solve(expr, var_sym)
        return [str(s) for s in solutions]

    def evaluate_at(self, expr_str: str, var: str, value: float) -> str:
        """
        Evaluate expression at a point.

        Example:
            evaluate_at("x**3 - 3*x**2 + 4", "x", 2) -> "0"
        """
        expr = parse_expr(expr_str)
        var_sym = symbols(var)
        result = expr.subs(var_sym, value)
        return str(simplify(result))

    def simplify_expression(self, expr_str: str) -> str:
        """Simplify mathematical expression."""
        expr = parse_expr(expr_str)
        return str(simplify(expr))

    def compute_limit(
        self, expr_str: str, var: str, point: str, direction: str = None
    ) -> str:
        """
        Compute limit.

        Example:
            compute_limit("sin(x)/x", "x", "0") -> "1"
        """
        from sympy import oo
        expr = parse_expr(expr_str)
        var_sym = symbols(var)

        if point == "oo" or point == "inf":
            point_val = oo
        elif point == "-oo" or point == "-inf":
            point_val = -oo
        else:
            point_val = parse_expr(point)

        if direction == "+":
            result = limit(expr, var_sym, point_val, '+')
        elif direction == "-":
            result = limit(expr, var_sym, point_val, '-')
        else:
            result = limit(expr, var_sym, point_val)

        return str(result)

    def combination(self, n: int, k: int) -> int:
        """Compute C(n,k) = n! / (k! * (n-k)!)"""
        return int(binomial(n, k))

    def permutation(self, n: int, k: int) -> int:
        """Compute P(n,k) = n! / (n-k)!"""
        return int(factorial(n) / factorial(n - k))
```

### 5.3 Formula Database Tool (`agent/tools/formula_db.py`)

```python
"""
Formula database for Grade 12 Vietnamese math curriculum.

Categories:
- Calculus (derivatives, integrals, limits)
- Spatial Geometry (volumes, distances)
- Coordinate Geometry (planes, lines)
- Probability & Statistics
- Trigonometry
"""

from typing import List, Dict, Optional
import json
from pathlib import Path

class FormulaDBTool:
    """
    Retrieval tool for mathematical formulas.

    Search methods:
    - Keyword matching (primary)
    - Category browsing
    - Formula name lookup
    """

    def __init__(self, formula_dir: Path):
        self.formulas = self._load_formulas(formula_dir)
        self.index = self._build_index()

    def _load_formulas(self, formula_dir: Path) -> Dict:
        """Load all formula JSON files."""
        formulas = {}
        for file in formula_dir.glob("*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                formulas[file.stem] = json.load(f)
        return formulas

    def _build_index(self) -> Dict[str, List[Dict]]:
        """Build keyword index for fast lookup."""
        index = {}
        for category, data in self.formulas.items():
            for formula in data.get("formulas", []):
                for keyword in formula.get("keywords", []):
                    keyword_lower = keyword.lower()
                    if keyword_lower not in index:
                        index[keyword_lower] = []
                    index[keyword_lower].append({
                        "category": category,
                        "formula": formula
                    })
        return index

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search formulas by keyword.

        Example:
            search("đạo hàm") -> [derivative formulas...]
        """
        query_lower = query.lower()
        results = []

        # Exact keyword match
        if query_lower in self.index:
            results.extend(self.index[query_lower])

        # Partial match
        for keyword, formulas in self.index.items():
            if query_lower in keyword or keyword in query_lower:
                for f in formulas:
                    if f not in results:
                        results.append(f)

        return results[:top_k]

    def get_by_name(self, formula_name: str) -> Optional[Dict]:
        """Get specific formula by name."""
        for category, data in self.formulas.items():
            for formula in data.get("formulas", []):
                if formula.get("name") == formula_name:
                    return formula
        return None

    def list_category(self, category: str) -> List[Dict]:
        """List all formulas in a category."""
        if category in self.formulas:
            return self.formulas[category].get("formulas", [])
        return []
```

### 5.4 Step Verifier Tool (`agent/tools/verifier.py`)

```python
"""
Mathematical step verification tool.

Verifies:
- Derivative calculations
- Integral calculations
- Equation solutions
- Numerical computations
- Logical reasoning steps
"""

from typing import Tuple, List, Dict
from .calculator import CalculatorTool

class VerifierTool:
    """
    Verifies mathematical steps and solutions.

    Returns (is_correct, explanation) for each verification.
    """

    def __init__(self):
        self.calculator = CalculatorTool()

    def verify_derivative(
        self,
        original: str,
        claimed_derivative: str,
        variable: str = "x"
    ) -> Tuple[bool, str]:
        """
        Verify if claimed_derivative is correct derivative of original.

        Example:
            verify_derivative("x^3 - 3*x^2 + 4", "3*x^2 - 6*x")
            -> (True, "Verified: derivative is correct")
        """
        try:
            computed = self.calculator.derivative(original, variable)
            # Simplify both for comparison
            computed_simplified = self.calculator.simplify_expression(computed)
            claimed_simplified = self.calculator.simplify_expression(claimed_derivative)

            if computed_simplified == claimed_simplified:
                return True, f"✓ Verified: {claimed_derivative} is correct"
            else:
                return False, f"✗ Incorrect. Expected: {computed}, Got: {claimed_derivative}"
        except Exception as e:
            return False, f"Error during verification: {str(e)}"

    def verify_integral(
        self,
        original: str,
        claimed_integral: str,
        variable: str = "x"
    ) -> Tuple[bool, str]:
        """Verify indefinite integral by differentiating."""
        try:
            # Differentiate the claimed integral
            derivative = self.calculator.derivative(claimed_integral, variable)
            derivative_simplified = self.calculator.simplify_expression(derivative)
            original_simplified = self.calculator.simplify_expression(original)

            if derivative_simplified == original_simplified:
                return True, f"✓ Verified: {claimed_integral} is correct"
            else:
                return False, f"✗ Derivative of {claimed_integral} = {derivative}, expected {original}"
        except Exception as e:
            return False, f"Error during verification: {str(e)}"

    def verify_equation_solution(
        self,
        equation: str,
        claimed_solutions: List[str],
        variable: str = "x"
    ) -> Tuple[bool, str]:
        """Verify equation solutions by substitution."""
        try:
            for sol in claimed_solutions:
                result = self.calculator.evaluate_at(equation, variable, float(sol))
                if abs(float(result)) > 1e-10:
                    return False, f"✗ x = {sol} does not satisfy equation (gives {result})"
            return True, f"✓ All solutions verified"
        except Exception as e:
            return False, f"Error during verification: {str(e)}"

    def verify_extrema(
        self,
        function: str,
        extrema_points: List[Dict],  # [{"x": 0, "y": 4, "type": "max"}, ...]
        variable: str = "x"
    ) -> Tuple[bool, str]:
        """Verify extrema points using second derivative test."""
        try:
            second_deriv = self.calculator.derivative(function, variable, order=2)

            for point in extrema_points:
                x_val = point["x"]
                claimed_y = point["y"]
                claimed_type = point["type"]

                # Verify y value
                actual_y = self.calculator.evaluate_at(function, variable, x_val)
                if str(actual_y) != str(claimed_y):
                    return False, f"✗ At x={x_val}, y={actual_y}, not {claimed_y}"

                # Verify type using second derivative
                second_deriv_val = float(self.calculator.evaluate_at(
                    second_deriv, variable, x_val
                ))

                if claimed_type == "max" and second_deriv_val >= 0:
                    return False, f"✗ At x={x_val}, y''={second_deriv_val} ≥ 0, not a max"
                if claimed_type == "min" and second_deriv_val <= 0:
                    return False, f"✗ At x={x_val}, y''={second_deriv_val} ≤ 0, not a min"

            return True, "✓ All extrema verified"
        except Exception as e:
            return False, f"Error during verification: {str(e)}"
```

### 5.5 Graph Plotter Tool (`agent/tools/plotter.py`)

```python
"""
Function graphing tool using Matplotlib.

Supports:
- Function plotting
- Multiple functions overlay
- Extrema marking
- Asymptotes
- Custom styling for Vietnamese math problems
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import io
import base64

class PlotterTool:
    """
    Graph plotting tool for function visualization.

    Designed for Grade 12 function analysis (khảo sát hàm số).
    """

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("output/plots")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Vietnamese-friendly settings
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False

    def plot_function(
        self,
        func_str: str,
        x_range: Tuple[float, float] = (-10, 10),
        y_range: Optional[Tuple[float, float]] = None,
        title: str = None,
        extrema: List[Dict] = None,
        asymptotes: Dict = None,
        save_path: str = None
    ) -> str:
        """
        Plot a function with optional annotations.

        Args:
            func_str: Function string (e.g., "x**3 - 3*x**2 + 4")
            x_range: (min_x, max_x)
            y_range: Optional (min_y, max_y)
            title: Plot title
            extrema: List of {"x": val, "y": val, "type": "max"|"min"}
            asymptotes: {"vertical": [...], "horizontal": [...], "oblique": [...]}
            save_path: Where to save the plot

        Returns:
            Base64 encoded image or file path
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        # Generate x values
        x = np.linspace(x_range[0], x_range[1], 1000)

        # Evaluate function (safely)
        try:
            y = eval(func_str.replace("^", "**"), {"x": x, "np": np,
                "sin": np.sin, "cos": np.cos, "tan": np.tan,
                "exp": np.exp, "log": np.log, "sqrt": np.sqrt})
        except Exception as e:
            return f"Error plotting: {str(e)}"

        # Plot function
        ax.plot(x, y, 'b-', linewidth=2, label=f'y = {func_str}')

        # Plot extrema
        if extrema:
            for pt in extrema:
                color = 'red' if pt["type"] == "max" else 'green'
                marker = '^' if pt["type"] == "max" else 'v'
                label = f'Cực {"đại" if pt["type"] == "max" else "tiểu"} ({pt["x"]}, {pt["y"]})'
                ax.plot(pt["x"], pt["y"], marker=marker, markersize=10,
                       color=color, label=label)

        # Plot asymptotes
        if asymptotes:
            for va in asymptotes.get("vertical", []):
                ax.axvline(x=va, color='gray', linestyle='--', alpha=0.7)
            for ha in asymptotes.get("horizontal", []):
                ax.axhline(y=ha, color='gray', linestyle='--', alpha=0.7)

        # Styling
        ax.axhline(y=0, color='k', linewidth=0.5)
        ax.axvline(x=0, color='k', linewidth=0.5)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')

        if title:
            ax.set_title(title, fontsize=14)
        ax.set_xlabel('x')
        ax.set_ylabel('y')

        if y_range:
            ax.set_ylim(y_range)

        # Save or return base64
        if save_path:
            full_path = self.output_dir / save_path
            plt.savefig(full_path, dpi=150, bbox_inches='tight')
            plt.close()
            return str(full_path)
        else:
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            return f"data:image/png;base64,{img_base64}"
```

---

## 6. Grade 12 Curriculum Coverage

### 6.1 Topic Structure (Grade 12 Only)

```yaml
grade_12_curriculum:
  calculus:
    function_analysis:
      - Khảo sát sự biến thiên và vẽ đồ thị (Function analysis & graphing)
      - Cực trị của hàm số (Extrema)
      - Tiệm cận (Asymptotes)
      - GTLN, GTNN (Max/Min values)
      - Tiếp tuyến của đồ thị (Tangent lines)

    derivatives_applications:
      - Đạo hàm của hàm hợp (Chain rule)
      - Đạo hàm cấp cao (Higher-order derivatives)
      - Ứng dụng đạo hàm (Applications)

    integrals:
      - Nguyên hàm (Antiderivatives)
      - Tích phân xác định (Definite integrals)
      - Ứng dụng tích phân tính diện tích (Area applications)
      - Ứng dụng tích phân tính thể tích (Volume applications)

  spatial_geometry:
    relations:
      - Quan hệ song song (Parallel relations)
      - Quan hệ vuông góc (Perpendicular relations)

    measurements:
      - Góc giữa đường thẳng và mặt phẳng (Line-plane angles)
      - Góc giữa hai mặt phẳng (Dihedral angles)
      - Khoảng cách (Distances)

    volumes:
      - Thể tích khối đa diện (Polyhedra volumes)
      - Thể tích khối tròn xoay (Revolution volumes)

  coordinate_geometry_3d:
    equations:
      - Phương trình mặt phẳng (Plane equations)
      - Phương trình đường thẳng (Line equations)

    calculations:
      - Khoảng cách trong không gian (Spatial distances)
      - Góc trong không gian (Spatial angles)
      - Vị trí tương đối (Relative positions)

  probability_statistics:
    probability:
      - Xác suất cơ bản (Basic probability)
      - Xác suất có điều kiện (Conditional probability)
      - Biến cố (Events)

    statistics:
      - Số liệu và bảng phân bố tần số (Data & frequency tables)
      - Trung bình, phương sai, độ lệch chuẩn (Mean, variance, std dev)
      - Đọc hiểu biểu đồ thống kê (Statistical charts)
```

### 6.2 Minimum Dataset: 50+ Problems

| Topic | Subtopic | Count | Difficulty Distribution |
|-------|----------|-------|------------------------|
| Function Analysis | Khảo sát hàm bậc 3 | 5 | 1 dễ, 3 TB, 1 khó |
| Function Analysis | Khảo sát hàm trùng phương | 3 | 1 TB, 2 khó |
| Function Analysis | Khảo sát hàm phân thức | 4 | 2 TB, 2 khó |
| Extrema | Cực trị hàm số | 4 | 2 dễ, 2 TB |
| Tangent Lines | Tiếp tuyến | 3 | 1 dễ, 1 TB, 1 khó |
| Integrals | Nguyên hàm | 4 | 2 dễ, 2 TB |
| Integrals | Tích phân xác định | 4 | 2 TB, 2 khó |
| Integrals | Diện tích | 4 | 2 TB, 2 khó |
| Spatial Geometry | Thể tích | 5 | 2 dễ, 2 TB, 1 khó |
| Spatial Geometry | Khoảng cách | 4 | 1 dễ, 2 TB, 1 khó |
| Coordinate 3D | Mặt phẳng | 4 | 2 TB, 2 khó |
| Coordinate 3D | Đường thẳng | 3 | 1 TB, 2 khó |
| Probability | Xác suất | 4 | 2 dễ, 2 TB |
| Statistics | Thống kê | 3 | 1 dễ, 2 TB |
| **TOTAL** | | **54** | 15 dễ, 25 TB, 14 khó |

---

## 7. Data Flow & API Contracts

### 7.1 Dual-Mode Inference Flow

```
+============================================================================+
|                          INFERENCE PIPELINE                                 |
+============================================================================+
|                                                                             |
|  User Question ──────────────────────────────────────────────────┐         |
|       │                                                          │         |
|       v                                                          │         |
|  ┌─────────────────┐                                            │         |
|  │ Language Detect │                                            │         |
|  └────────┬────────┘                                            │         |
|           │                                                      │         |
|           v                                                      │         |
|  ┌─────────────────┐     ┌──────────────────────────────────────┴───┐    |
|  │ Mode Selection  │────>│  Which mode?                              │    |
|  └─────────────────┘     │  - "simple": Direct model inference       │    |
|                          │  - "agent": Full agentic pipeline         │    |
|                          │  - "auto": Complexity-based selection     │    |
|                          └────────────────┬─────────────────────────┘    |
|                                           │                              |
|              ┌────────────────────────────┴────────────────────────┐     |
|              │                                                      │     |
|              v                                                      v     |
|  ┌───────────────────────┐                      ┌───────────────────────┐|
|  │   MODE: SIMPLE        │                      │   MODE: AGENT         │|
|  │                       │                      │                       │|
|  │  Fine-tuned Model     │                      │  Agent Controller     │|
|  │  Direct Generation    │                      │  ┌─────────────────┐ │|
|  │                       │                      │  │ ReAct Loop      │ │|
|  │  Latency: 2-5 sec     │                      │  │ ┌─────────────┐ │ │|
|  │                       │                      │  │ │ THINK       │ │ │|
|  │                       │                      │  │ │ ↓           │ │ │|
|  │                       │                      │  │ │ ACT (tool)  │ │ │|
|  │                       │                      │  │ │ ↓           │ │ │|
|  │                       │                      │  │ │ OBSERVE     │ │ │|
|  │                       │                      │  │ │ ↓           │ │ │|
|  │                       │                      │  │ │ REPEAT?     │ │ │|
|  │                       │                      │  │ └─────────────┘ │ │|
|  │                       │                      │  └─────────────────┘ │|
|  │                       │                      │                       │|
|  │                       │                      │  Latency: 10-30 sec   │|
|  └───────────┬───────────┘                      └───────────┬───────────┘|
|              │                                              │            |
|              └──────────────────┬───────────────────────────┘            |
|                                 │                                        |
|                                 v                                        |
|                    ┌────────────────────────┐                           |
|                    │ Response Formatter     │                           |
|                    │ (Vietnamese/English)   │                           |
|                    └───────────┬────────────┘                           |
|                                │                                        |
|                                v                                        |
|                    ┌────────────────────────┐                           |
|                    │ Gradio UI (Streaming)  │                           |
|                    └────────────────────────┘                           |
|                                                                          |
+============================================================================+
```

### 7.2 API Contracts

#### Training API (unchanged)
```bash
python training/train.py \
    --data data/grade12_math_dataset.json \
    --epochs 5 \
    --output output/checkpoints
```

#### Inference API (updated)
```bash
# Simple mode
python chatbot/app.py --model output/final --mode simple

# Agent mode (default)
python chatbot/app.py --model output/final --mode agent

# Auto mode (complexity-based selection)
python chatbot/app.py --model output/final --mode auto
```

#### Programmatic API
```python
# Simple mode
from chatbot.inference import InferenceEngine
engine = InferenceEngine(model_path)
response = engine.generate(prompt, system_prompt)

# Agent mode
from chatbot.agent_inference import AgentInferenceEngine
agent_engine = AgentInferenceEngine(model_path)
for chunk in agent_engine.solve(problem, language="vi"):
    print(chunk, end="", flush=True)
```

---

## 8. Implementation Phases

### Phase 1: Foundation + Grade 12 Data (Days 1-2)
**Priority: Critical**

```
Tasks:
├── Update project structure
├── Implement config.py (v2 with agent settings)
├── Create Grade 12 dataset (50+ problems)
├── Create formula databases (4 JSON files)
├── Implement utils/logger.py
├── Implement utils/helpers.py
├── Create requirements.txt (with sympy, langchain)
└── Setup .gitignore

Deliverables:
- Complete Grade 12 dataset
- Formula databases for all topics
- Working project skeleton
```

### Phase 2: Training Pipeline (Days 2-4)
**Priority: Critical**

```
Tasks:
├── Implement training/model_config.py
├── Implement training/trainer_utils.py
├── Implement training/train.py
├── Test training on sample data
└── Fine-tune model on Grade 12 dataset

Deliverables:
- Working training pipeline
- Fine-tuned model checkpoint
```

### Phase 3: Agent & Tools (Days 4-6)
**Priority: High**

```
Tasks:
├── Implement agent/tools/calculator.py
├── Implement agent/tools/formula_db.py
├── Implement agent/tools/verifier.py
├── Implement agent/tools/plotter.py
├── Implement agent/math_agent.py
├── Implement agent/agent_prompts.py
└── Test agent with sample problems

Deliverables:
- All 4 tools working
- Math agent with ReAct loop
- Agent tested on various problem types
```

### Phase 4: Chatbot Interface (Days 6-8)
**Priority: High**

```
Tasks:
├── Implement chatbot/inference.py (simple mode)
├── Implement chatbot/agent_inference.py (agent mode)
├── Implement chatbot/app.py (dual mode UI)
├── Add mode selection toggle
├── Add streaming support
└── Add graph display capability

Deliverables:
- Gradio interface with dual modes
- Streaming responses
- Graph visualization
```

### Phase 5: Polish & Documentation (Days 8-9)
**Priority: Medium**

```
Tasks:
├── Write README.md (EN/VI)
├── Add comprehensive docstrings
├── Create usage examples
├── Write test suite
├── Performance optimization
└── Final testing

Deliverables:
- Complete documentation
- Test coverage
- Production-ready system
```

---

## 9. Technical Implementation Details

### 9.1 Memory Budget (Agent Mode)

```
Component                          VRAM Usage
─────────────────────────────────────────────
Fine-tuned Qwen (8-bit)            ~7.5 GB
Agent overhead                     ~0.2 GB
Tool execution buffer              ~0.3 GB
Gradio interface                   ~0.1 GB
─────────────────────────────────────────────
Total                              ~8.1 GB

Margin for 12GB GPU: ~4GB buffer ✓
```

### 9.2 Latency Expectations

| Mode | Typical Latency | Use Case |
|------|-----------------|----------|
| Simple | 2-5 seconds | Quick Q&A, definitions |
| Agent (1-3 tool calls) | 10-15 seconds | Standard problems |
| Agent (5+ tool calls) | 20-30 seconds | Complex analysis |
| Agent with graph | 25-40 seconds | Function graphing |

### 9.3 Dependencies

```txt
# Core ML
torch>=2.1.0
transformers>=4.36.0
peft>=0.7.0
bitsandbytes>=0.41.0
accelerate>=0.25.0
datasets>=2.15.0

# Training
tensorboard>=2.15.0
tqdm>=4.66.0

# Agent & Tools
sympy>=1.12           # Calculator
numpy>=1.24.0         # Numerical
matplotlib>=3.7.0     # Plotter

# Inference & UI
gradio>=4.10.0

# Utilities
python-dotenv>=1.0.0
pyyaml>=6.0.0
```

---

## Summary of Changes

| Aspect | v1.0 | v2.0 |
|--------|------|------|
| **Grade Focus** | 8-12 | **12 only** |
| **Approach** | Fine-tuning only | **Fine-tuning + Agentic/Tool-RAG** |
| **Inference** | Single mode | **Dual mode** (simple/agent) |
| **Tools** | None | **Calculator, Formula DB, Verifier, Plotter** |
| **Dataset Size** | 10+ | **50+** |
| **Topics** | General | **Grade 12 curriculum specific** |

---

## Approval Requested

**Please confirm:**
1. Focus on Grade 12 only - **OK?**
2. Add Agentic/Tool-RAG approach - **OK?**
3. Integrated project (not separate) - **OK?**
4. Dual inference modes (simple/agent) - **OK?**

Once approved, I will proceed with implementation.
