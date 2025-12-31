"""
Vietnamese Grade 12 Math Tutor - Centralized Configuration
Version: 2.0.0

This module contains all configuration settings for the math tutor system.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import os


@dataclass
class ModelConfig:
    """Model and quantization settings."""
    name: str = "Qwen/Qwen2.5-Math-7B-Instruct"
    quantization_bits: int = 8
    device_map: str = "auto"
    torch_dtype: str = "float16"
    trust_remote_code: bool = True
    max_memory: Optional[dict] = None  # e.g., {0: "10GB", "cpu": "30GB"}


@dataclass
class LoRAConfig:
    """LoRA (Low-Rank Adaptation) settings for fine-tuning."""
    r: int = 64
    alpha: int = 128
    dropout: float = 0.05
    target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj"
    ])
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


@dataclass
class TrainingConfig:
    """Training hyperparameters."""
    num_epochs: int = 5
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    lr_scheduler_type: str = "cosine"
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    fp16: bool = True
    bf16: bool = False
    max_length: int = 2048
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 100
    save_total_limit: int = 3
    seed: int = 42


@dataclass
class DatasetConfig:
    """Dataset configuration for Grade 12."""
    grade: int = 12
    train_split: float = 0.85
    val_split: float = 0.15
    min_problems: int = 50
    supported_topics: List[str] = field(default_factory=lambda: [
        "calculus",
        "spatial_geometry",
        "coordinate_geometry_3d",
        "probability_statistics"
    ])
    supported_languages: List[str] = field(default_factory=lambda: ["vi", "en"])
    default_language: str = "vi"


@dataclass
class AgentConfig:
    """Agent system configuration."""
    enabled: bool = True
    max_iterations: int = 10
    timeout_seconds: int = 60

    # Tool settings
    calculator_enabled: bool = True
    formula_db_enabled: bool = True
    verifier_enabled: bool = True
    plotter_enabled: bool = True

    # ReAct loop settings
    think_token: str = "THINK:"
    action_token: str = "ACTION:"
    observation_token: str = "OBSERVATION:"
    answer_token: str = "ANSWER:"


@dataclass
class InferenceConfig:
    """Inference settings."""
    modes: List[str] = field(default_factory=lambda: ["simple", "agent", "auto"])
    default_mode: str = "agent"

    # Generation parameters
    max_new_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    do_sample: bool = True
    repetition_penalty: float = 1.1

    # Streaming
    streaming_enabled: bool = True


@dataclass
class UIConfig:
    """Gradio UI configuration."""
    title: str = "Vietnamese Grade 12 Math Tutor"
    title_vi: str = "Gia Su Toan Lop 12"
    description: str = "AI-powered math tutor for Vietnamese Grade 12 curriculum"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 7860
    share: bool = False

    # Theme
    theme: str = "soft"


@dataclass
class Config:
    """Main configuration class combining all settings."""

    # Project metadata
    PROJECT_NAME: str = "Vietnamese Grade 12 Math Tutor"
    VERSION: str = "2.0.0"

    # Sub-configurations
    model: ModelConfig = field(default_factory=ModelConfig)
    lora: LoRAConfig = field(default_factory=LoRAConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    # Paths (computed)
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent)

    @property
    def DATA_DIR(self) -> Path:
        return self.BASE_DIR / "data"

    @property
    def FORMULA_DIR(self) -> Path:
        return self.DATA_DIR / "formulas"

    @property
    def TRAINING_DIR(self) -> Path:
        return self.BASE_DIR / "training"

    @property
    def AGENT_DIR(self) -> Path:
        return self.BASE_DIR / "agent"

    @property
    def CHATBOT_DIR(self) -> Path:
        return self.BASE_DIR / "chatbot"

    @property
    def OUTPUT_DIR(self) -> Path:
        return self.BASE_DIR / "output"

    @property
    def CHECKPOINT_DIR(self) -> Path:
        return self.OUTPUT_DIR / "checkpoints"

    @property
    def FINAL_MODEL_DIR(self) -> Path:
        return self.OUTPUT_DIR / "final_model"

    @property
    def LOG_DIR(self) -> Path:
        return self.OUTPUT_DIR / "logs"

    @property
    def PLOT_DIR(self) -> Path:
        return self.OUTPUT_DIR / "plots"

    def ensure_directories(self) -> None:
        """Create all necessary directories."""
        directories = [
            self.DATA_DIR,
            self.FORMULA_DIR,
            self.OUTPUT_DIR,
            self.CHECKPOINT_DIR,
            self.FINAL_MODEL_DIR,
            self.LOG_DIR,
            self.PLOT_DIR,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        """Create config with environment variable overrides."""
        config = cls()

        # Override from environment variables
        if os.getenv("MATH_TUTOR_MODEL"):
            config.model.name = os.getenv("MATH_TUTOR_MODEL")

        if os.getenv("MATH_TUTOR_QUANTIZATION"):
            config.model.quantization_bits = int(os.getenv("MATH_TUTOR_QUANTIZATION"))

        if os.getenv("MATH_TUTOR_BATCH_SIZE"):
            config.training.batch_size = int(os.getenv("MATH_TUTOR_BATCH_SIZE"))

        if os.getenv("MATH_TUTOR_EPOCHS"):
            config.training.num_epochs = int(os.getenv("MATH_TUTOR_EPOCHS"))

        if os.getenv("MATH_TUTOR_PORT"):
            config.ui.port = int(os.getenv("MATH_TUTOR_PORT"))

        return config


# Global config instance
config = Config()


# Convenience function
def get_config() -> Config:
    """Get the global configuration instance."""
    return config


if __name__ == "__main__":
    # Print configuration for debugging
    cfg = get_config()
    print(f"Project: {cfg.PROJECT_NAME} v{cfg.VERSION}")
    print(f"Model: {cfg.model.name}")
    print(f"LoRA r={cfg.lora.r}, alpha={cfg.lora.alpha}")
    print(f"Training: {cfg.training.num_epochs} epochs, batch={cfg.training.batch_size}")
    print(f"Agent enabled: {cfg.agent.enabled}")
    print(f"Default inference mode: {cfg.inference.default_mode}")
