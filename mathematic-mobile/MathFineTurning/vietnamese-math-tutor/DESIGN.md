# Vietnamese High School Math Tutor - System Design Document

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Component Specifications](#3-component-specifications)
4. [Data Flow & API Contracts](#4-data-flow--api-contracts)
5. [Technical Implementation Details](#5-technical-implementation-details)
6. [Vietnamese Math Curriculum Coverage](#6-vietnamese-math-curriculum-coverage)
7. [Implementation Phases](#7-implementation-phases)
8. [Risk Analysis & Mitigation](#8-risk-analysis--mitigation)

---

## 1. Executive Summary

### 1.1 Project Overview
A complete Vietnamese High School Math Tutor system featuring:
- Fine-tuning pipeline for **Qwen2.5-Math-7B-Instruct** on Vietnamese math problems
- Optimized for **RTX 3060 (12GB VRAM)** with 8-bit quantization
- **Bilingual support** (Vietnamese primary, English secondary)
- **Gradio chatbot interface** with language auto-detection
- Comprehensive dataset management utilities

### 1.2 Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Base Model | Qwen2.5-Math-7B-Instruct | Best math reasoning in its class, multilingual support |
| Quantization | 8-bit (BitsAndBytes) | Optimal balance for 12GB VRAM, minimal quality loss |
| Fine-tuning | LoRA (PEFT) | Memory efficient, preserves base knowledge |
| Training Framework | Transformers Trainer | Robust, well-documented, checkpoint support |
| UI Framework | Gradio Blocks | Rapid development, streaming support, customizable |

### 1.3 Hardware Requirements
- **Minimum**: RTX 3060 12GB, 32GB RAM, 50GB storage
- **Recommended**: RTX 3080+ 16GB+, 64GB RAM, 100GB storage
- **CPU Fallback**: Available but significantly slower

---

## 2. System Architecture

### 2.1 High-Level Architecture Diagram

```
+-----------------------------------------------------------------------------+
|                        VIETNAMESE MATH TUTOR SYSTEM                         |
+-----------------------------------------------------------------------------+
|                                                                             |
|  +---------------+    +---------------+    +---------------+                |
|  |   Dataset     |    |   Training    |    |   Chatbot     |                |
|  |   Module      |--->|   Pipeline    |--->|   Interface   |                |
|  +---------------+    +---------------+    +---------------+                |
|         |                   |                   |                           |
|         v                   v                   v                           |
|  +---------------+    +---------------+    +---------------+                |
|  | data/         |    | training/     |    | chatbot/      |                |
|  | - loader      |    | - train.py    |    | - app.py      |                |
|  | - validator   |    | - config      |    | - inference   |                |
|  | - dataset     |    | - utils       |    | - lang_det    |                |
|  +---------------+    +---------------+    +---------------+                |
|                                                                             |
|  +-------------------------------------------------------------+           |
|  |                    SHARED INFRASTRUCTURE                     |           |
|  |  +----------+  +----------+  +----------+  +----------+     |           |
|  |  | config   |  | utils/   |  | models/  |  | logs/    |     |           |
|  |  | .py      |  | helpers  |  | checkpts |  | training |     |           |
|  |  +----------+  +----------+  +----------+  +----------+     |           |
|  +-------------------------------------------------------------+           |
|                                                                             |
+-----------------------------------------------------------------------------+
```

### 2.2 Project Structure

```
vietnamese-math-tutor/
├── config.py                    # Centralized configuration
├── requirements.txt             # All dependencies with versions
├── README.md                    # Comprehensive documentation (EN/VI)
├── .gitignore                   # Git ignore rules
│
├── data/
│   ├── __init__.py
│   ├── vietnamese_math_dataset.json   # Sample dataset (10+ problems)
│   ├── dataset_loader.py              # Load, format, split datasets
│   ├── data_validator.py              # JSON schema validation
│   └── sample_problems/               # Additional problem sets by topic
│       ├── calculus.json
│       ├── algebra.json
│       ├── geometry.json
│       └── statistics.json
│
├── training/
│   ├── __init__.py
│   ├── train.py                 # Main training script with CLI
│   ├── model_config.py          # Model loading with quantization
│   └── trainer_utils.py         # Custom callbacks, metrics, utilities
│
├── chatbot/
│   ├── __init__.py
│   ├── app.py                   # Gradio interface (bilingual UI)
│   ├── inference.py             # Generation with streaming
│   ├── language_detector.py     # Vietnamese/English detection
│   └── prompts.py               # System prompts in both languages
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py               # Common utilities
│   └── logger.py                # Logging configuration
│
├── output/
│   ├── checkpoints/             # Training checkpoints
│   ├── final_model/             # Final trained model
│   └── logs/                    # TensorBoard logs
│
└── tests/
    ├── __init__.py
    ├── test_dataset.py
    ├── test_training.py
    └── test_inference.py
```

### 2.3 Module Dependency Graph

```
                    +-------------+
                    |  config.py  |
                    +------+------+
                           |
           +---------------+---------------+
           |               |               |
           v               v               v
    +------------+  +------------+  +------------+
    | utils/     |  | data/      |  | training/  |
    | logger.py  |  | loader.py  |  | train.py   |
    | helpers.py |  | validator  |  | config.py  |
    +-----+------+  +-----+------+  +-----+------+
          |               |               |
          |               +-------+-------+
          |                       |
          +-----------+-----------+
                      |
                      v
               +------------+
               | chatbot/   |
               | app.py     |
               | inference  |
               +------------+
```

---

## 3. Component Specifications

### 3.1 Configuration Module (`config.py`)

```python
# Configuration Structure
class Config:
    # Model Configuration
    MODEL_NAME: str = "Qwen/Qwen2.5-Math-7B-Instruct"
    QUANTIZATION_BITS: int = 8
    DEVICE_MAP: str = "auto"

    # LoRA Configuration
    LORA_R: int = 64
    LORA_ALPHA: int = 128
    LORA_DROPOUT: float = 0.05
    LORA_TARGET_MODULES: List[str] = ["q_proj", "k_proj", "v_proj", "o_proj"]

    # Training Configuration
    NUM_EPOCHS: int = 5
    BATCH_SIZE: int = 4
    GRADIENT_ACCUMULATION_STEPS: int = 4
    LEARNING_RATE: float = 2e-4
    LR_SCHEDULER: str = "cosine"
    FP16: bool = True

    # Dataset Configuration
    TRAIN_SPLIT: float = 0.80
    VAL_SPLIT: float = 0.05
    TEST_SPLIT: float = 0.15
    MAX_LENGTH: int = 2048

    # Paths
    DATA_PATH: Path
    OUTPUT_PATH: Path
    CHECKPOINT_PATH: Path
    LOG_PATH: Path

    # System Prompts (Vietnamese & English)
    SYSTEM_PROMPT_VI: str
    SYSTEM_PROMPT_EN: str
```

### 3.2 Data Module

#### 3.2.1 Dataset Schema (`vietnamese_math_dataset.json`)

```json
{
  "metadata": {
    "version": "1.0.0",
    "created_at": "2024-01-01",
    "description": "Vietnamese High School Math Problems",
    "language": "vi",
    "grades": [8, 9, 10, 11, 12],
    "topics": ["calculus", "algebra", "geometry", "statistics", "probability"]
  },
  "problems": [
    {
      "id": "calc_001",
      "question": "Tim dao ham cua ham so f(x) = x^3 - 3x^2 + 2x - 1",
      "solution": "**Buoc 1**: Ap dung quy tac dao ham...\n**Buoc 2**: ...\n**Ket qua**: f'(x) = 3x^2 - 6x + 2",
      "answer": "f'(x) = 3x^2 - 6x + 2",
      "grade": 11,
      "topic": "calculus",
      "subtopic": "derivatives",
      "difficulty": "trung binh",
      "language": "vi",
      "keywords": ["dao ham", "ham so", "derivative"],
      "hints": [
        "Su dung cong thuc (x^n)' = n*x^(n-1)",
        "Dao ham cua hang so bang 0"
      ],
      "common_mistakes": [
        "Quen tru 1 tu so mu",
        "Sai dau khi tinh dao ham"
      ],
      "verification": "Thay x = 1: f'(1) = 3 - 6 + 2 = -1"
    }
  ]
}
```

#### 3.2.2 DatasetLoader Class

```python
class VietnameseMathDatasetLoader:
    """
    Load and process Vietnamese math problems for training.

    Responsibilities:
    - Load JSON with UTF-8 encoding
    - Validate schema compliance
    - Format for Qwen chat template
    - Split into train/val/test
    - Generate statistics
    """

    def __init__(self, data_path: Path, tokenizer: AutoTokenizer):
        self.data_path = data_path
        self.tokenizer = tokenizer

    def load(self) -> Dataset:
        """Load and validate dataset from JSON."""

    def format_for_training(self, problem: Dict) -> str:
        """Format problem using Qwen chat template."""

    def split_dataset(self) -> Tuple[Dataset, Dataset, Dataset]:
        """Split into train (80%), val (5%), test (15%)."""

    def get_statistics(self) -> Dict:
        """Return statistics by grade, topic, difficulty."""
```

#### 3.2.3 DataValidator Class

```python
class DataValidator:
    """Validate dataset JSON structure and content."""

    REQUIRED_FIELDS = [
        "id", "question", "solution", "grade",
        "topic", "difficulty", "language"
    ]

    VALID_DIFFICULTIES = ["de", "trung binh", "kho"]
    VALID_GRADES = [8, 9, 10, 11, 12]
    VALID_TOPICS = [
        "calculus", "algebra", "geometry",
        "statistics", "probability", "functions"
    ]

    def validate(self, data_path: Path) -> ValidationResult:
        """Run all validations and return detailed report."""

    def validate_problem(self, problem: Dict) -> List[str]:
        """Validate single problem, return list of errors."""
```

### 3.3 Training Module

#### 3.3.1 Model Configuration (`model_config.py`)

```python
class ModelConfig:
    """Model loading and configuration utilities."""

    @staticmethod
    def get_quantization_config() -> BitsAndBytesConfig:
        """Configure 8-bit quantization for 12GB VRAM."""
        return BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False,
        )

    @staticmethod
    def get_lora_config() -> LoraConfig:
        """Configure LoRA for efficient fine-tuning."""
        return LoraConfig(
            r=64,
            lora_alpha=128,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            bias="none",
            task_type="CAUSAL_LM",
        )

    @staticmethod
    def load_model_for_training(
        model_name: str,
        device_map: str = "auto"
    ) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
        """Load quantized model prepared for LoRA training."""

    @staticmethod
    def load_model_for_inference(
        base_model_name: str,
        adapter_path: Path
    ) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
        """Load base model with trained LoRA adapters for inference."""
```

#### 3.3.2 Training Script (`train.py`)

```python
"""
Main training script for Vietnamese Math Tutor.

Usage:
    python training/train.py \
        --data data/vietnamese_math_dataset.json \
        --epochs 5 \
        --batch-size 4 \
        --output output/checkpoints

Features:
    - Argument parsing with sensible defaults
    - Automatic GPU detection with CPU fallback
    - Checkpoint saving every epoch
    - TensorBoard logging
    - Resume from checkpoint
    - CUDA OOM handling
    - Progress tracking with tqdm
"""

class MathTutorTrainer:
    """Orchestrates the training pipeline."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.config = Config()
        self.logger = setup_logger()

    def setup_training_args(self) -> TrainingArguments:
        """Configure TrainingArguments for Trainer."""

    def train(self) -> None:
        """Execute training pipeline."""

    def handle_oom(self) -> None:
        """Handle CUDA Out of Memory errors."""
```

### 3.4 Chatbot Module

#### 3.4.1 Gradio Interface (`app.py`)

```python
"""
Gradio chatbot interface for Vietnamese Math Tutor.

Usage:
    python chatbot/app.py --model output/checkpoints/final

Features:
    - Bilingual UI (Vietnamese/English toggle)
    - Auto-detect input language
    - Streaming responses
    - Grade/topic selection
    - Temperature control
    - Example problems dropdown
    - Copy solution button
"""

class MathTutorChatbot:
    """Gradio-based chatbot interface."""

    def __init__(self, model_path: Path):
        self.inference_engine = InferenceEngine(model_path)
        self.language_detector = LanguageDetector()

    def build_interface(self) -> gr.Blocks:
        """Build Gradio Blocks interface."""

    def respond(
        self,
        message: str,
        history: List[Tuple[str, str]],
        grade: int,
        topic: str,
        temperature: float,
        max_tokens: int
    ) -> Generator[str, None, None]:
        """Generate streaming response."""

    def launch(self, share: bool = False) -> None:
        """Launch Gradio interface."""
```

#### 3.4.2 Inference Engine (`inference.py`)

```python
class InferenceEngine:
    """Handle model inference with streaming support."""

    def __init__(self, model_path: Path):
        self.model, self.tokenizer = self._load_model(model_path)
        self.streamer = TextIteratorStreamer(self.tokenizer)

    def _load_model(self, model_path: Path):
        """Load model for inference."""

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.9
    ) -> Generator[str, None, None]:
        """Generate response with streaming."""

    def generate(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs
    ) -> str:
        """Non-streaming generation for batch use."""

    def build_prompt(
        self,
        user_message: str,
        system_prompt: str,
        history: List[Tuple[str, str]] = None
    ) -> str:
        """Build prompt using Qwen chat template."""
```

#### 3.4.3 Language Detector (`language_detector.py`)

```python
class LanguageDetector:
    """Detect Vietnamese vs English text."""

    # Vietnamese-specific characters (with diacritics)
    VIETNAMESE_CHARS = set("aaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooouuuuuuuuuuuyyyyyd")

    # Common Vietnamese math words
    VIETNAMESE_MATH_WORDS = [
        "tim", "giai", "tinh", "chung minh", "dao ham",
        "nguyen ham", "tich phan", "ham so", "phuong trinh",
        "bat phuong trinh", "gioi han", "cuc tri", "diem cuc"
    ]

    def detect(self, text: str) -> str:
        """Detect language of input text. Returns: 'vi' or 'en'"""

    def get_confidence(self, text: str) -> Tuple[str, float]:
        """Detect language with confidence score."""
```

#### 3.4.4 System Prompts (`prompts.py`)

```python
"""System prompts for the math tutor in Vietnamese and English."""

SYSTEM_PROMPT_VI = """Ban la mot gia su toan hoc trung hoc pho thong Viet Nam chuyen nghiep va tan tam.

NHIEM VU:
- Giai cac bai toan tu lop 8 den lop 12 theo chuong trinh Viet Nam
- Giai thich tung buoc mot cach ro rang va chi tiet
- Su dung thuat ngu toan hoc tieng Viet chinh xac

QUY TAC TRINH BAY:
1. Bat dau voi phan tich de bai
2. Trinh bay loi giai theo cac buoc: **Buoc 1**, **Buoc 2**, ...
3. Neu ro cong thuc va dinh ly duoc su dung
4. Ket thuc voi dap an va kiem tra (neu co the)

CHU DE HO TRO:
- Giai tich: Dao ham, nguyen ham, tich phan, cuc tri, khao sat ham so
- Dai so: Phuong trinh, bat phuong trinh, day so, to hop
- Hinh hoc: Hinh hoc khong gian, toa do trong khong gian
- Xac suat thong ke: Bien co, xac suat, trung binh, phuong sai

PHONG CACH:
- Kien nhan va khich le
- Giai thich phu hop voi trinh do hoc sinh
- Chi ra loi sai thuong gap de hoc sinh tranh"""

SYSTEM_PROMPT_EN = """You are a professional and dedicated Vietnamese high school math tutor.

MISSION:
- Solve math problems from grades 8-12 following the Vietnamese curriculum
- Explain step by step clearly and in detail
- Use correct Vietnamese mathematical terminology when appropriate

PRESENTATION RULES:
1. Start with problem analysis
2. Present solution in steps: **Step 1**, **Step 2**, ...
3. Clearly state formulas and theorems used
4. End with answer and verification (if possible)

SUPPORTED TOPICS:
- Calculus: Derivatives, antiderivatives, integrals, extrema, function analysis
- Algebra: Equations, inequalities, sequences, combinatorics
- Geometry: Spatial geometry, coordinate geometry in space
- Probability & Statistics: Events, probability, mean, variance

STYLE:
- Patient and encouraging
- Explain appropriately for student level
- Point out common mistakes to help students avoid them"""

def get_system_prompt(language: str = "vi") -> str:
    """Get system prompt for specified language."""
    return SYSTEM_PROMPT_VI if language == "vi" else SYSTEM_PROMPT_EN
```

---

## 4. Data Flow & API Contracts

### 4.1 Training Data Flow

```
+-----------------+     +-----------------+     +-----------------+
|  JSON Dataset   |---->|  DataValidator  |---->|  DatasetLoader  |
|  (UTF-8)        |     |  (Schema Check) |     |  (Format/Split) |
+-----------------+     +-----------------+     +--------+--------+
                                                         |
                                                         v
+-----------------+     +-----------------+     +-----------------+
|  Checkpoints    |<----|    Trainer      |<----|  Tokenized      |
|  (LoRA Adapters)|     |  (Train Loop)   |     |  Dataset        |
+-----------------+     +-----------------+     +-----------------+
```

### 4.2 Inference Data Flow

```
+-----------------+     +-----------------+     +-----------------+
|  User Input     |---->|  Language       |---->|  Prompt         |
|  (Question)     |     |  Detector       |     |  Builder        |
+-----------------+     +-----------------+     +--------+--------+
                                                         |
                                                         v
+-----------------+     +-----------------+     +-----------------+
|  Gradio UI      |<----|  Streaming      |<----|  Model          |
|  (Display)      |     |  Generator      |     |  Inference      |
+-----------------+     +-----------------+     +-----------------+
```

### 4.3 API Contracts

#### Training API

```bash
# Command-line interface
python training/train.py \
    --data <path>           # Required: Path to dataset JSON
    --output <path>         # Optional: Output directory (default: output/)
    --epochs <int>          # Optional: Number of epochs (default: 5)
    --batch-size <int>      # Optional: Batch size (default: 4)
    --learning-rate <float> # Optional: Learning rate (default: 2e-4)
    --resume <path>         # Optional: Resume from checkpoint
    --no-cuda               # Optional: Force CPU training

# Return codes
# 0: Success
# 1: Invalid arguments
# 2: Dataset validation failed
# 3: CUDA out of memory
# 4: Training interrupted
# 5: Checkpoint save failed
```

#### Inference API

```python
# Command-line interface
# python chatbot/app.py \
#     --model <path>          # Required: Path to trained model/adapters
#     --port <int>            # Optional: Server port (default: 7860)
#     --share                 # Optional: Create public link
#     --no-cuda               # Optional: Force CPU inference

# Programmatic API
engine = InferenceEngine(model_path)

# Streaming
for chunk in engine.generate_stream(
    prompt="Tim dao ham cua f(x) = x^3",
    system_prompt=SYSTEM_PROMPT_VI,
    temperature=0.7,
    max_tokens=1024
):
    print(chunk, end="", flush=True)

# Non-streaming
response = engine.generate(
    prompt="Find the derivative of f(x) = x^3",
    system_prompt=SYSTEM_PROMPT_EN
)
```

---

## 5. Technical Implementation Details

### 5.1 Memory Optimization for RTX 3060 (12GB)

```
# Memory budget breakdown
Base Model (8-bit quantized):    ~7.5 GB
LoRA Adapters (trainable):       ~0.5 GB
Optimizer States:                ~1.0 GB
Activation Memory:               ~2.0 GB
Buffer:                          ~1.0 GB
-----------------------------------------
Total:                           ~12.0 GB

# Key optimizations:
# 1. 8-bit quantization (not 4-bit for quality)
# 2. Gradient checkpointing
# 3. Small batch size with gradient accumulation
# 4. FP16 training
# 5. Aggressive memory clearing between batches
```

### 5.2 Qwen Chat Template

```python
def format_qwen_chat(
    system_prompt: str,
    user_message: str,
    assistant_response: str = None
) -> str:
    """
    Format conversation for Qwen2.5-Math-Instruct.

    Template:
    <|im_start|>system
    {system_prompt}<|im_end|>
    <|im_start|>user
    {user_message}<|im_end|>
    <|im_start|>assistant
    {response}<|im_end|>
    """
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
    prompt += f"<|im_start|>user\n{user_message}<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    if assistant_response:
        prompt += f"{assistant_response}<|im_end|>"
    return prompt
```

### 5.3 LoRA Target Modules Rationale

```
# Why these modules?
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]

q_proj (Query): Controls what the model "asks" about
k_proj (Key): Controls what information is available
v_proj (Value): Controls the actual content retrieved
o_proj (Output): Controls how attention results combine

For math tutoring:
- Strong attention modifications help the model focus on
  mathematical structures and step-by-step reasoning
- All attention projections modified for comprehensive adaptation
- Avoids MLP layers to preserve general knowledge
```

---

## 6. Vietnamese Math Curriculum Coverage

### 6.1 Topic Hierarchy

```yaml
calculus:
  derivatives:
    - Dao ham co ban (Basic derivatives)
    - Dao ham ham hop (Chain rule)
    - Dao ham cap cao (Higher-order derivatives)
  integrals:
    - Nguyen ham (Antiderivatives)
    - Tich phan xac dinh (Definite integrals)
    - Ung dung tich phan (Applications)
  functions:
    - Khao sat ham so (Function analysis)
    - Cuc tri (Extrema)
    - Tiem can (Asymptotes)

algebra:
  sequences:
    - Cap so cong (Arithmetic sequences)
    - Cap so nhan (Geometric sequences)
    - Gioi han day so (Sequence limits)
  combinatorics:
    - Hoan vi (Permutations)
    - Chinh hop (Arrangements)
    - To hop (Combinations)
    - Nhi thuc Newton (Binomial theorem)
  equations:
    - Phuong trinh (Equations)
    - Bat phuong trinh (Inequalities)
    - He phuong trinh (Systems)

geometry:
  spatial:
    - Quan he song song (Parallel relations)
    - Quan he vuong goc (Perpendicular relations)
    - Goc va khoang cach (Angles and distances)
    - The tich (Volumes)
  coordinate:
    - Phuong trinh mat phang (Plane equations)
    - Phuong trinh duong thang (Line equations)
    - Tinh khoang cach (Distance calculations)

probability_statistics:
  probability:
    - Xac suat co ban (Basic probability)
    - Xac suat co dieu kien (Conditional probability)
    - Bien co (Events)
  statistics:
    - Tan so, tan suat (Frequency)
    - Trung binh, phuong sai (Mean, variance)
    - Do lech chuan (Standard deviation)
```

### 6.2 Sample Problems per Topic (Minimum 10)

| Topic | Grade | Count | Difficulty Distribution |
|-------|-------|-------|------------------------|
| Derivatives | 11 | 3 | 1 easy, 1 medium, 1 hard |
| Integrals | 12 | 2 | 1 medium, 1 hard |
| Function Analysis | 12 | 2 | 1 medium, 1 hard |
| Sequences | 11 | 1 | 1 medium |
| Combinatorics | 11 | 1 | 1 easy |
| Spatial Geometry | 11-12 | 2 | 1 medium, 1 hard |
| Probability | 11 | 1 | 1 medium |

---

## 7. Implementation Phases

### Phase 1: Foundation (Days 1-2)
**Priority: Critical**

```
Tasks:
+-- Create project structure
+-- Implement config.py
+-- Implement utils/logger.py
+-- Implement utils/helpers.py
+-- Create requirements.txt
+-- Setup .gitignore

Deliverables:
- Runnable project skeleton
- Working logging system
- Device detection utilities
```

### Phase 2: Data Pipeline (Days 2-3)
**Priority: Critical**

```
Tasks:
+-- Design JSON schema
+-- Create vietnamese_math_dataset.json (10+ problems)
+-- Implement data/data_validator.py
+-- Implement data/dataset_loader.py
+-- Write validation tests

Deliverables:
- Complete sample dataset
- Working data validation
- Dataset loading and splitting
```

### Phase 3: Training Pipeline (Days 3-5)
**Priority: Critical**

```
Tasks:
+-- Implement training/model_config.py
+-- Implement training/trainer_utils.py
+-- Implement training/train.py
+-- Add checkpoint management
+-- Add TensorBoard logging
+-- Test full training loop

Deliverables:
- Working training script
- Checkpoint saving/loading
- Training monitoring
```

### Phase 4: Chatbot Interface (Days 5-7)
**Priority: High**

```
Tasks:
+-- Implement chatbot/language_detector.py
+-- Implement chatbot/prompts.py
+-- Implement chatbot/inference.py
+-- Implement chatbot/app.py
+-- Add streaming support
+-- Add bilingual UI

Deliverables:
- Working Gradio chatbot
- Streaming responses
- Language auto-detection
```

### Phase 5: Polish & Documentation (Days 7-8)
**Priority: Medium**

```
Tasks:
+-- Write comprehensive README.md
+-- Add inline documentation
+-- Create usage examples
+-- Write test suite
+-- Final testing and bug fixes

Deliverables:
- Complete documentation
- Tested, production-ready code
```

---

## 8. Risk Analysis & Mitigation

### 8.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CUDA OOM during training | High | High | Implement adaptive batch sizing, gradient checkpointing |
| Poor model quality | Medium | High | Careful dataset curation, validation during training |
| Slow inference | Medium | Medium | 8-bit quantization, streaming, caching |
| UTF-8 encoding issues | Low | Medium | Explicit encoding handling, validation |
| Checkpoint corruption | Low | High | Multiple checkpoint saves, validation on save |

### 8.2 Mitigation Strategies

```python
# CUDA OOM mitigation
try:
    trainer.train()
except RuntimeError as e:
    if "out of memory" in str(e):
        torch.cuda.empty_cache()
        new_batch_size = max(1, current_batch_size // 2)
        logger.warning(f"OOM! Reducing batch size to {new_batch_size}")
        # Retry with smaller batch

# Checkpoint validation
def save_checkpoint(model, path):
    """Save checkpoint with validation."""
    temp_path = path.with_suffix('.tmp')
    model.save_pretrained(temp_path)

    # Validate saved checkpoint
    try:
        test_load = AutoModelForCausalLM.from_pretrained(temp_path)
        del test_load
        shutil.move(temp_path, path)
    except Exception as e:
        logger.error(f"Checkpoint validation failed: {e}")
        raise
```

### 8.3 Fallback Strategies

| Scenario | Primary Approach | Fallback |
|----------|-----------------|----------|
| No GPU available | CUDA training | CPU training (slower) |
| Model not found | Load from HuggingFace | Error with download instructions |
| Invalid dataset | Validate and reject | Show specific errors and fixes |
| Streaming failure | WebSocket streaming | Polling-based updates |

---

## Appendix A: Dependencies

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
evaluate>=0.4.0

# Inference & UI
gradio>=4.10.0

# Utilities
python-dotenv>=1.0.0
pyyaml>=6.0.0

# Optional: Development
pytest>=7.4.0
black>=23.12.0
isort>=5.13.0
```

---

## Appendix B: Example Interactions

### Vietnamese Interaction

```
User: Tim dao ham cua ham so f(x) = x^3 - 3x^2 + 2x - 1