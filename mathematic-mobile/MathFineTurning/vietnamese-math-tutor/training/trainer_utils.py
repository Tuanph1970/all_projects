"""
Training utilities for Vietnamese Grade 12 Math Tutor.

Provides:
- Custom callbacks for training monitoring
- Metrics computation
- Data collation for causal LM
- Training helper functions
"""

import os
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

import torch
from torch.utils.data import Dataset
from transformers import (
    Trainer,
    TrainingArguments,
    TrainerCallback,
    TrainerState,
    TrainerControl,
    PreTrainedTokenizer,
    DataCollatorForLanguageModeling,
)
from transformers.trainer_utils import EvalPrediction

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import get_config, Config
from utils.logger import get_logger

logger = get_logger("trainer_utils")


# ============================================================================
# Custom Dataset
# ============================================================================

class MathTutorDataset(Dataset):
    """
    Dataset for math tutor fine-tuning.

    Formats problems into instruction-following format.
    """

    def __init__(
        self,
        data: List[Dict],
        tokenizer: PreTrainedTokenizer,
        max_length: int = 2048,
        instruction_template: str = "### Instruction:\n{instruction}\n\n### Response:\n{response}",
    ):
        """
        Initialize the dataset.

        Args:
            data: List of training examples with 'instruction' and 'output' keys
            tokenizer: Tokenizer for encoding
            max_length: Maximum sequence length
            instruction_template: Template for formatting examples
        """
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.instruction_template = instruction_template

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        example = self.data[idx]

        # Format the text
        text = self.instruction_template.format(
            instruction=example.get("instruction", ""),
            response=example.get("output", ""),
        )

        # Tokenize
        encodings = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        # Prepare labels (same as input_ids for causal LM)
        input_ids = encodings["input_ids"].squeeze()
        attention_mask = encodings["attention_mask"].squeeze()

        # Labels: -100 for padding tokens (ignored in loss)
        labels = input_ids.clone()
        labels[attention_mask == 0] = -100

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


class MathTutorChatDataset(Dataset):
    """
    Dataset for chat-format fine-tuning.

    Uses the model's chat template if available.
    """

    def __init__(
        self,
        data: List[Dict],
        tokenizer: PreTrainedTokenizer,
        max_length: int = 2048,
        system_prompt: str = "You are a Vietnamese math tutor specializing in Grade 12 mathematics. Provide step-by-step solutions in Vietnamese.",
    ):
        """
        Initialize the chat dataset.

        Args:
            data: List of training examples with 'question' and 'solution' keys
            tokenizer: Tokenizer for encoding
            max_length: Maximum sequence length
            system_prompt: System prompt for the model
        """
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.system_prompt = system_prompt

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        example = self.data[idx]

        # Build chat messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": example.get("instruction", example.get("question", ""))},
            {"role": "assistant", "content": example.get("output", example.get("solution", ""))},
        ]

        # Apply chat template if available
        if hasattr(self.tokenizer, "apply_chat_template"):
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )
        else:
            # Fallback to simple format
            text = f"System: {self.system_prompt}\n\nUser: {messages[1]['content']}\n\nAssistant: {messages[2]['content']}"

        # Tokenize
        encodings = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )

        input_ids = encodings["input_ids"].squeeze()
        attention_mask = encodings["attention_mask"].squeeze()

        labels = input_ids.clone()
        labels[attention_mask == 0] = -100

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


# ============================================================================
# Custom Callbacks
# ============================================================================

class LoggingCallback(TrainerCallback):
    """
    Custom callback for detailed logging during training.
    """

    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file
        self.training_start_time = None
        self.logs: List[Dict] = []

    def on_train_begin(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs
    ):
        self.training_start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Training started")
        logger.info(f"  Total epochs: {args.num_train_epochs}")
        logger.info(f"  Batch size: {args.per_device_train_batch_size}")
        logger.info(f"  Gradient accumulation: {args.gradient_accumulation_steps}")
        logger.info(f"  Learning rate: {args.learning_rate}")
        logger.info("=" * 60)

    def on_log(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        logs: Dict[str, float] = None,
        **kwargs
    ):
        if logs:
            self.logs.append({
                "step": state.global_step,
                "epoch": state.epoch,
                **logs,
            })

            # Log to console
            log_str = f"Step {state.global_step}"
            if "loss" in logs:
                log_str += f" | Loss: {logs['loss']:.4f}"
            if "learning_rate" in logs:
                log_str += f" | LR: {logs['learning_rate']:.2e}"
            if "eval_loss" in logs:
                log_str += f" | Eval Loss: {logs['eval_loss']:.4f}"

            logger.info(log_str)

    def on_train_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs
    ):
        duration = datetime.now() - self.training_start_time
        logger.info("=" * 60)
        logger.info("Training completed")
        logger.info(f"  Total time: {duration}")
        logger.info(f"  Final step: {state.global_step}")
        logger.info(f"  Best metric: {state.best_metric}")
        logger.info("=" * 60)

        # Save logs to file
        if self.log_file:
            with open(self.log_file, 'w') as f:
                json.dump(self.logs, f, indent=2)
            logger.info(f"Training logs saved to: {self.log_file}")


class SaveBestModelCallback(TrainerCallback):
    """
    Callback to save the best model based on validation loss.
    """

    def __init__(self, save_path: Path):
        self.save_path = Path(save_path)
        self.best_loss = float('inf')

    def on_evaluate(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        metrics: Dict[str, float] = None,
        **kwargs
    ):
        if metrics and "eval_loss" in metrics:
            current_loss = metrics["eval_loss"]
            if current_loss < self.best_loss:
                self.best_loss = current_loss
                logger.info(f"New best model! Eval loss: {current_loss:.4f}")

                # Save model
                model = kwargs.get("model")
                if model:
                    self.save_path.mkdir(parents=True, exist_ok=True)
                    model.save_pretrained(self.save_path / "best_model")
                    logger.info(f"Best model saved to: {self.save_path / 'best_model'}")


class EarlyStoppingCallback(TrainerCallback):
    """
    Early stopping callback based on validation loss.
    """

    def __init__(self, patience: int = 3, min_delta: float = 0.001):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float('inf')
        self.counter = 0

    def on_evaluate(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        metrics: Dict[str, float] = None,
        **kwargs
    ):
        if metrics and "eval_loss" in metrics:
            current_loss = metrics["eval_loss"]

            if current_loss < self.best_loss - self.min_delta:
                self.best_loss = current_loss
                self.counter = 0
            else:
                self.counter += 1
                logger.info(f"Early stopping counter: {self.counter}/{self.patience}")

                if self.counter >= self.patience:
                    logger.info("Early stopping triggered!")
                    control.should_training_stop = True


# ============================================================================
# Metrics
# ============================================================================

def compute_metrics(eval_pred: EvalPrediction) -> Dict[str, float]:
    """
    Compute metrics for evaluation.

    Args:
        eval_pred: Evaluation predictions from Trainer

    Returns:
        Dictionary of metric names and values
    """
    predictions, labels = eval_pred

    # For language modeling, we typically use perplexity
    # which is exp(cross_entropy_loss)

    # Get the loss from the model output if available
    if hasattr(eval_pred, "losses") and eval_pred.losses is not None:
        loss = eval_pred.losses.mean()
    else:
        # Calculate cross-entropy loss manually
        # This is a simplified version
        shift_logits = predictions[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()

        # Flatten
        loss_fct = torch.nn.CrossEntropyLoss(ignore_index=-100)
        loss = loss_fct(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1)
        )

    perplexity = math.exp(loss) if loss < 100 else float('inf')

    return {
        "perplexity": perplexity,
    }


# ============================================================================
# Data Collator
# ============================================================================

def get_data_collator(
    tokenizer: PreTrainedTokenizer,
    mlm: bool = False,
) -> DataCollatorForLanguageModeling:
    """
    Get data collator for language modeling.

    Args:
        tokenizer: Tokenizer
        mlm: Whether to use masked language modeling (False for causal LM)

    Returns:
        DataCollator instance
    """
    return DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=mlm,
        pad_to_multiple_of=8,  # Efficient for tensor cores
    )


# ============================================================================
# Training Arguments Helper
# ============================================================================

def get_training_arguments(
    output_dir: Path,
    config: Optional[Config] = None,
    **overrides,
) -> TrainingArguments:
    """
    Create TrainingArguments with sensible defaults.

    Args:
        output_dir: Output directory for checkpoints
        config: Config object
        **overrides: Override specific arguments

    Returns:
        TrainingArguments instance
    """
    if config is None:
        config = get_config()

    # Default arguments
    args = {
        "output_dir": str(output_dir),
        "num_train_epochs": config.training.num_epochs,
        "per_device_train_batch_size": config.training.batch_size,
        "per_device_eval_batch_size": config.training.batch_size,
        "gradient_accumulation_steps": config.training.gradient_accumulation_steps,
        "learning_rate": config.training.learning_rate,
        "lr_scheduler_type": config.training.lr_scheduler_type,
        "warmup_ratio": config.training.warmup_ratio,
        "weight_decay": config.training.weight_decay,
        "fp16": config.training.fp16,
        "bf16": config.training.bf16,
        "logging_steps": config.training.logging_steps,
        "save_steps": config.training.save_steps,
        "eval_steps": config.training.eval_steps,
        "evaluation_strategy": "steps",
        "save_strategy": "steps",
        "save_total_limit": config.training.save_total_limit,
        "load_best_model_at_end": True,
        "metric_for_best_model": "eval_loss",
        "greater_is_better": False,
        "report_to": "tensorboard",
        "logging_dir": str(output_dir / "logs"),
        "seed": config.training.seed,
        "dataloader_num_workers": 4,
        "remove_unused_columns": False,
        "optim": "adamw_torch",
        "gradient_checkpointing": True,
        "max_grad_norm": 1.0,
    }

    # Apply overrides
    args.update(overrides)

    return TrainingArguments(**args)


# ============================================================================
# Trainer Wrapper
# ============================================================================

class MathTutorTrainer(Trainer):
    """
    Custom trainer for Math Tutor with additional functionality.
    """

    def __init__(self, *args, **kwargs):
        # Extract custom callbacks
        custom_callbacks = kwargs.pop("custom_callbacks", [])

        super().__init__(*args, **kwargs)

        # Add custom callbacks
        for callback in custom_callbacks:
            self.add_callback(callback)

    def log_training_summary(self) -> None:
        """Log a summary of training configuration."""
        logger.info("Training Summary:")
        logger.info(f"  Model: {self.model.config.model_type}")
        logger.info(f"  Train samples: {len(self.train_dataset)}")
        if self.eval_dataset:
            logger.info(f"  Eval samples: {len(self.eval_dataset)}")
        logger.info(f"  Epochs: {self.args.num_train_epochs}")
        logger.info(f"  Batch size: {self.args.per_device_train_batch_size}")
        logger.info(f"  Gradient accumulation: {self.args.gradient_accumulation_steps}")
        logger.info(f"  Effective batch size: {self.args.per_device_train_batch_size * self.args.gradient_accumulation_steps}")
        logger.info(f"  Learning rate: {self.args.learning_rate}")


# ============================================================================
# Utility Functions
# ============================================================================

def prepare_training_data(
    problems: List[Dict],
    tokenizer: PreTrainedTokenizer,
    max_length: int = 2048,
    format: str = "instruction",
) -> Dataset:
    """
    Prepare dataset for training.

    Args:
        problems: List of problem dictionaries
        tokenizer: Tokenizer
        max_length: Maximum sequence length
        format: "instruction" or "chat"

    Returns:
        Dataset instance
    """
    if format == "instruction":
        return MathTutorDataset(problems, tokenizer, max_length)
    elif format == "chat":
        return MathTutorChatDataset(problems, tokenizer, max_length)
    else:
        raise ValueError(f"Unknown format: {format}")


def estimate_training_time(
    num_samples: int,
    batch_size: int,
    num_epochs: int,
    gradient_accumulation: int = 1,
    seconds_per_step: float = 1.0,
) -> str:
    """
    Estimate training time.

    Args:
        num_samples: Number of training samples
        batch_size: Batch size per device
        num_epochs: Number of epochs
        gradient_accumulation: Gradient accumulation steps
        seconds_per_step: Estimated seconds per optimization step

    Returns:
        Formatted time string
    """
    effective_batch_size = batch_size * gradient_accumulation
    steps_per_epoch = num_samples // effective_batch_size
    total_steps = steps_per_epoch * num_epochs
    total_seconds = total_steps * seconds_per_step

    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)

    return f"{hours}h {minutes}m ({total_steps} steps)"


if __name__ == "__main__":
    # Test utilities
    config = get_config()

    print("=" * 60)
    print("Trainer Utilities Test")
    print("=" * 60)

    # Test training arguments
    train_args = get_training_arguments(Path("output/test"))
    print(f"\nTraining Arguments:")
    print(f"  Output dir: {train_args.output_dir}")
    print(f"  Epochs: {train_args.num_train_epochs}")
    print(f"  Batch size: {train_args.per_device_train_batch_size}")
    print(f"  Learning rate: {train_args.learning_rate}")

    # Test time estimation
    est_time = estimate_training_time(
        num_samples=50,
        batch_size=4,
        num_epochs=5,
        gradient_accumulation=4,
        seconds_per_step=2.0,
    )
    print(f"\nEstimated training time: {est_time}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
