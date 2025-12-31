"""
Model configuration for Vietnamese Grade 12 Math Tutor.

Handles:
- Model loading with 8-bit/4-bit quantization (BitsAndBytes)
- LoRA/PEFT configuration for efficient fine-tuning
- Tokenizer setup with proper padding
"""

import torch
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    PreTrainedModel,
    PreTrainedTokenizer,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType,
)

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import get_config, Config
from utils.logger import get_logger

logger = get_logger("model_config")


def get_quantization_config(bits: int = 8) -> BitsAndBytesConfig:
    """
    Create BitsAndBytes quantization configuration.

    Args:
        bits: Quantization bits (4 or 8)

    Returns:
        BitsAndBytesConfig for model loading
    """
    if bits == 4:
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    elif bits == 8:
        return BitsAndBytesConfig(
            load_in_8bit=True,
            llm_int8_threshold=6.0,
            llm_int8_has_fp16_weight=False,
        )
    else:
        raise ValueError(f"Unsupported quantization bits: {bits}. Use 4 or 8.")


def get_peft_config(config: Optional[Config] = None) -> LoraConfig:
    """
    Create LoRA configuration for PEFT.

    Args:
        config: Config object (uses global config if None)

    Returns:
        LoraConfig for PEFT model
    """
    if config is None:
        config = get_config()

    lora_config = LoraConfig(
        r=config.lora.r,
        lora_alpha=config.lora.alpha,
        lora_dropout=config.lora.dropout,
        target_modules=config.lora.target_modules,
        bias=config.lora.bias,
        task_type=TaskType.CAUSAL_LM,
    )

    logger.info(f"LoRA config: r={lora_config.r}, alpha={lora_config.lora_alpha}, "
                f"dropout={lora_config.lora_dropout}")
    logger.info(f"Target modules: {lora_config.target_modules}")

    return lora_config


def load_tokenizer(
    model_name: Optional[str] = None,
    config: Optional[Config] = None,
) -> PreTrainedTokenizer:
    """
    Load and configure tokenizer.

    Args:
        model_name: Model name/path (uses config if None)
        config: Config object (uses global config if None)

    Returns:
        Configured tokenizer
    """
    if config is None:
        config = get_config()

    if model_name is None:
        model_name = config.model.name

    logger.info(f"Loading tokenizer: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=config.model.trust_remote_code,
    )

    # Set padding token if not set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
        logger.info("Set pad_token to eos_token")

    # Set padding side for causal LM
    tokenizer.padding_side = "right"

    logger.info(f"Tokenizer loaded. Vocab size: {tokenizer.vocab_size}")

    return tokenizer


def load_model(
    model_name: Optional[str] = None,
    config: Optional[Config] = None,
    quantization: bool = True,
    for_training: bool = True,
) -> PreTrainedModel:
    """
    Load model with optional quantization and LoRA.

    Args:
        model_name: Model name/path (uses config if None)
        config: Config object (uses global config if None)
        quantization: Whether to apply quantization
        for_training: Whether to prepare for training (adds LoRA)

    Returns:
        Model ready for training or inference
    """
    if config is None:
        config = get_config()

    if model_name is None:
        model_name = config.model.name

    logger.info(f"Loading model: {model_name}")
    logger.info(f"Quantization: {quantization}, For training: {for_training}")

    # Prepare model kwargs
    model_kwargs: Dict[str, Any] = {
        "trust_remote_code": config.model.trust_remote_code,
        "device_map": config.model.device_map,
    }

    # Add quantization config
    if quantization:
        bits = config.model.quantization_bits
        model_kwargs["quantization_config"] = get_quantization_config(bits)
        logger.info(f"Using {bits}-bit quantization")
    else:
        # Use float16 without quantization
        model_kwargs["torch_dtype"] = torch.float16

    # Add max memory if specified
    if config.model.max_memory:
        model_kwargs["max_memory"] = config.model.max_memory

    # Load base model
    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    logger.info(f"Model loaded. Parameters: {model.num_parameters():,}")

    # Prepare for training
    if for_training:
        if quantization:
            # Prepare quantized model for k-bit training
            model = prepare_model_for_kbit_training(
                model,
                use_gradient_checkpointing=True,
            )
            logger.info("Model prepared for k-bit training")

        # Add LoRA adapters
        lora_config = get_peft_config(config)
        model = get_peft_model(model, lora_config)

        # Print trainable parameters
        trainable_params, total_params = model.get_nb_trainable_parameters()
        trainable_percent = 100 * trainable_params / total_params

        logger.info(f"Trainable parameters: {trainable_params:,} / {total_params:,} "
                    f"({trainable_percent:.2f}%)")

    return model


def load_model_and_tokenizer(
    model_name: Optional[str] = None,
    config: Optional[Config] = None,
    quantization: bool = True,
    for_training: bool = True,
) -> Tuple[PreTrainedModel, PreTrainedTokenizer]:
    """
    Load both model and tokenizer.

    Args:
        model_name: Model name/path
        config: Config object
        quantization: Whether to apply quantization
        for_training: Whether to prepare for training

    Returns:
        Tuple of (model, tokenizer)
    """
    tokenizer = load_tokenizer(model_name, config)
    model = load_model(model_name, config, quantization, for_training)

    return model, tokenizer


def load_trained_model(
    checkpoint_path: Path,
    config: Optional[Config] = None,
    quantization: bool = True,
) -> Tuple[PreTrainedModel, PreTrainedTokenizer]:
    """
    Load a trained model from checkpoint.

    Args:
        checkpoint_path: Path to saved checkpoint
        config: Config object
        quantization: Whether to use quantization

    Returns:
        Tuple of (model, tokenizer)
    """
    from peft import PeftModel

    if config is None:
        config = get_config()

    logger.info(f"Loading trained model from: {checkpoint_path}")

    # Load tokenizer
    tokenizer = load_tokenizer(config=config)

    # Load base model (without LoRA for inference)
    base_model = load_model(
        config=config,
        quantization=quantization,
        for_training=False,  # Don't add new LoRA
    )

    # Load LoRA weights
    model = PeftModel.from_pretrained(
        base_model,
        checkpoint_path,
        is_trainable=False,
    )

    logger.info("Trained model loaded successfully")

    return model, tokenizer


def merge_and_save_model(
    checkpoint_path: Path,
    output_path: Path,
    config: Optional[Config] = None,
) -> None:
    """
    Merge LoRA weights with base model and save.

    This creates a standalone model without needing PEFT for inference.

    Args:
        checkpoint_path: Path to LoRA checkpoint
        output_path: Path to save merged model
        config: Config object
    """
    from peft import PeftModel

    if config is None:
        config = get_config()

    logger.info(f"Merging LoRA weights from: {checkpoint_path}")

    # Load base model without quantization for merging
    base_model = AutoModelForCausalLM.from_pretrained(
        config.model.name,
        trust_remote_code=config.model.trust_remote_code,
        torch_dtype=torch.float16,
        device_map="auto",
    )

    # Load LoRA weights
    model = PeftModel.from_pretrained(base_model, checkpoint_path)

    # Merge weights
    model = model.merge_and_unload()

    # Save merged model
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    model.save_pretrained(output_path)

    # Also save tokenizer
    tokenizer = load_tokenizer(config=config)
    tokenizer.save_pretrained(output_path)

    logger.info(f"Merged model saved to: {output_path}")


def get_model_info(model: PreTrainedModel) -> Dict[str, Any]:
    """
    Get information about a model.

    Args:
        model: The model to inspect

    Returns:
        Dictionary with model information
    """
    info = {
        "model_type": model.config.model_type,
        "vocab_size": model.config.vocab_size,
        "hidden_size": model.config.hidden_size,
        "num_layers": getattr(model.config, "num_hidden_layers", None),
        "num_attention_heads": getattr(model.config, "num_attention_heads", None),
        "total_parameters": model.num_parameters(),
    }

    # Check if PEFT model
    if hasattr(model, "get_nb_trainable_parameters"):
        trainable, total = model.get_nb_trainable_parameters()
        info["trainable_parameters"] = trainable
        info["trainable_percent"] = 100 * trainable / total

    return info


if __name__ == "__main__":
    # Test model loading (dry run without actually loading)
    config = get_config()

    print("=" * 60)
    print("Model Configuration Test")
    print("=" * 60)

    print(f"\nModel: {config.model.name}")
    print(f"Quantization: {config.model.quantization_bits}-bit")

    print("\nLoRA Configuration:")
    lora_config = get_peft_config(config)
    print(f"  r: {lora_config.r}")
    print(f"  alpha: {lora_config.lora_alpha}")
    print(f"  dropout: {lora_config.lora_dropout}")
    print(f"  target_modules: {lora_config.target_modules}")

    print("\nQuantization Configuration:")
    quant_config = get_quantization_config(config.model.quantization_bits)
    print(f"  8-bit: {quant_config.load_in_8bit}")
    print(f"  4-bit: {quant_config.load_in_4bit}")

    print("\n" + "=" * 60)
    print("Configuration test complete!")
    print("To load actual model, run with --load flag")
    print("=" * 60)
