#!/usr/bin/env python3
"""
Main training script for Vietnamese Grade 12 Math Tutor.

Usage:
    python training/train.py [options]

Examples:
    # Train with default settings
    python training/train.py

    # Train with custom epochs and batch size
    python training/train.py --epochs 3 --batch-size 2

    # Resume from checkpoint
    python training/train.py --resume output/checkpoints/checkpoint-500

    # Dry run (validate setup without training)
    python training/train.py --dry-run
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
from transformers import set_seed

from config import get_config, Config
from utils.logger import setup_logger, get_logger
from data.dataset_loader import DatasetLoader
from data.data_validator import DataValidator
from training.model_config import (
    load_model_and_tokenizer,
    load_tokenizer,
    get_model_info,
    merge_and_save_model,
)
from training.trainer_utils import (
    MathTutorTrainer,
    MathTutorDataset,
    get_training_arguments,
    get_data_collator,
    LoggingCallback,
    SaveBestModelCallback,
    EarlyStoppingCallback,
    estimate_training_time,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Train Vietnamese Grade 12 Math Tutor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Data arguments
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Path to training data JSON file",
    )

    # Model arguments
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name or path (default: from config)",
    )
    parser.add_argument(
        "--quantization",
        type=int,
        choices=[4, 8],
        default=8,
        help="Quantization bits (4 or 8, default: 8)",
    )

    # Training arguments
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Training batch size per device",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=None,
        help="Learning rate",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=2048,
        help="Maximum sequence length",
    )

    # Output arguments
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for checkpoints",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default=None,
        help="Name for this training run",
    )

    # Control arguments
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Resume from checkpoint path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate setup without training",
    )
    parser.add_argument(
        "--no-eval",
        action="store_true",
        help="Skip evaluation during training",
    )
    parser.add_argument(
        "--merge-on-complete",
        action="store_true",
        help="Merge LoRA weights after training",
    )
    parser.add_argument(
        "--early-stopping",
        type=int,
        default=None,
        help="Early stopping patience (None to disable)",
    )

    # Misc
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    return parser.parse_args()


def setup_environment(args: argparse.Namespace, config: Config) -> Path:
    """
    Set up training environment.

    Returns:
        Output directory path
    """
    # Set seed
    set_seed(args.seed)

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        run_name = args.run_name or datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = config.CHECKPOINT_DIR / run_name

    output_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging
    log_file = output_dir / "training.log"
    setup_logger("training", log_file=log_file)

    return output_dir


def validate_data(config: Config, data_path: Path, logger) -> bool:
    """Validate training data."""
    logger.info("Validating training data...")

    validator = DataValidator()
    is_valid, results = validator.validate_file(data_path)

    if not is_valid:
        logger.error("Data validation failed!")
        for result in results:
            if not result.is_valid:
                logger.error(f"  {result.message}")
        return False

    # Log warnings
    warnings = [r for r in results if r.is_valid and r.message]
    if warnings:
        logger.warning(f"Data validation warnings: {len(warnings)}")
        for warning in warnings[:5]:  # Show first 5
            logger.warning(f"  {warning.message}")

    logger.info("Data validation passed!")
    return True


def load_and_prepare_data(
    config: Config,
    data_path: Path,
    tokenizer,
    max_length: int,
    logger,
):
    """Load and prepare training/validation datasets."""
    logger.info(f"Loading data from: {data_path}")

    # Load dataset
    loader = DatasetLoader(data_path)
    logger.info(f"Loaded {len(loader)} problems")

    # Print statistics
    stats = loader.get_statistics()
    logger.info(f"Topics: {list(stats['by_topic'].keys())}")
    logger.info(f"Difficulties: {stats['by_difficulty']}")

    # Split data
    train_problems, val_problems = loader.split(
        train_ratio=config.dataset.train_split,
        seed=config.training.seed,
        stratify_by="topic",
    )

    logger.info(f"Train: {len(train_problems)}, Validation: {len(val_problems)}")

    # Convert to training format
    train_data = loader.to_training_dataset(train_problems)
    val_data = loader.to_training_dataset(val_problems)

    # Create datasets
    train_dataset = MathTutorDataset(train_data, tokenizer, max_length)
    val_dataset = MathTutorDataset(val_data, tokenizer, max_length)

    return train_dataset, val_dataset


def run_training(
    args: argparse.Namespace,
    config: Config,
    output_dir: Path,
    logger,
) -> None:
    """Main training function."""

    # Determine data path
    data_path = Path(args.data) if args.data else config.DATA_DIR / "grade12_math_dataset.json"

    # Validate data
    if not validate_data(config, data_path, logger):
        sys.exit(1)

    # Update config with command line args
    if args.quantization:
        config.model.quantization_bits = args.quantization
    if args.epochs:
        config.training.num_epochs = args.epochs
    if args.batch_size:
        config.training.batch_size = args.batch_size
    if args.lr:
        config.training.learning_rate = args.lr

    # Log configuration
    logger.info("=" * 60)
    logger.info("Training Configuration")
    logger.info("=" * 60)
    logger.info(f"Model: {config.model.name}")
    logger.info(f"Quantization: {config.model.quantization_bits}-bit")
    logger.info(f"LoRA r={config.lora.r}, alpha={config.lora.alpha}")
    logger.info(f"Epochs: {config.training.num_epochs}")
    logger.info(f"Batch size: {config.training.batch_size}")
    logger.info(f"Gradient accumulation: {config.training.gradient_accumulation_steps}")
    logger.info(f"Learning rate: {config.training.learning_rate}")
    logger.info(f"Output: {output_dir}")
    logger.info("=" * 60)

    # Check GPU
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        logger.info(f"GPU: {gpu_name} ({gpu_memory:.1f} GB)")
    else:
        logger.warning("No GPU available! Training will be very slow.")

    # Load tokenizer first (for data preparation)
    logger.info("Loading tokenizer...")
    tokenizer = load_tokenizer(args.model, config)

    # Prepare data
    train_dataset, val_dataset = load_and_prepare_data(
        config, data_path, tokenizer, args.max_length, logger
    )

    # Estimate training time
    est_time = estimate_training_time(
        num_samples=len(train_dataset),
        batch_size=config.training.batch_size,
        num_epochs=config.training.num_epochs,
        gradient_accumulation=config.training.gradient_accumulation_steps,
        seconds_per_step=2.0,  # Rough estimate for 8-bit training
    )
    logger.info(f"Estimated training time: {est_time}")

    # Dry run check
    if args.dry_run:
        logger.info("Dry run complete. Exiting without training.")
        logger.info(f"Would train on {len(train_dataset)} samples for {config.training.num_epochs} epochs")
        return

    # Load model
    logger.info("Loading model...")
    model, tokenizer = load_model_and_tokenizer(
        args.model,
        config,
        quantization=True,
        for_training=True,
    )

    # Log model info
    model_info = get_model_info(model)
    logger.info(f"Model type: {model_info['model_type']}")
    logger.info(f"Total parameters: {model_info['total_parameters']:,}")
    if 'trainable_parameters' in model_info:
        logger.info(f"Trainable parameters: {model_info['trainable_parameters']:,} "
                    f"({model_info['trainable_percent']:.2f}%)")

    # Prepare training arguments
    training_args = get_training_arguments(
        output_dir,
        config,
        num_train_epochs=config.training.num_epochs,
        per_device_train_batch_size=config.training.batch_size,
        learning_rate=config.training.learning_rate,
        evaluation_strategy="no" if args.no_eval else "steps",
    )

    # Prepare callbacks
    callbacks = [
        LoggingCallback(log_file=output_dir / "training_logs.json"),
        SaveBestModelCallback(save_path=output_dir),
    ]

    if args.early_stopping:
        callbacks.append(EarlyStoppingCallback(patience=args.early_stopping))

    # Create trainer
    trainer = MathTutorTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset if not args.no_eval else None,
        tokenizer=tokenizer,
        data_collator=get_data_collator(tokenizer),
        custom_callbacks=callbacks,
    )

    # Log training summary
    trainer.log_training_summary()

    # Train!
    logger.info("Starting training...")

    if args.resume:
        logger.info(f"Resuming from: {args.resume}")
        trainer.train(resume_from_checkpoint=args.resume)
    else:
        trainer.train()

    # Save final model
    logger.info("Saving final model...")
    final_model_path = output_dir / "final_model"
    trainer.save_model(str(final_model_path))
    tokenizer.save_pretrained(str(final_model_path))
    logger.info(f"Final model saved to: {final_model_path}")

    # Merge weights if requested
    if args.merge_on_complete:
        logger.info("Merging LoRA weights with base model...")
        merged_path = output_dir / "merged_model"
        merge_and_save_model(final_model_path, merged_path, config)
        logger.info(f"Merged model saved to: {merged_path}")

    # Final summary
    logger.info("=" * 60)
    logger.info("Training Complete!")
    logger.info("=" * 60)
    logger.info(f"Final model: {final_model_path}")
    logger.info(f"Training logs: {output_dir / 'training_logs.json'}")
    logger.info(f"TensorBoard logs: {output_dir / 'logs'}")
    logger.info("")
    logger.info("To use the model:")
    logger.info(f"  python chatbot/app.py --model {final_model_path}")
    logger.info("=" * 60)


def main():
    """Main entry point."""
    args = parse_args()
    config = get_config()

    # Setup environment
    output_dir = setup_environment(args, config)
    logger = get_logger("training")

    try:
        run_training(args, config, output_dir, logger)
    except KeyboardInterrupt:
        logger.info("Training interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Training failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
