#!/usr/bin/env python3
"""
Model download script for Mathematics LLM OCR Service.

This script downloads ML models from Hugging Face or other sources
and stores them locally for offline use.

Usage:
    python scripts/download_models.py [--models MODEL1,MODEL2] [--output-dir PATH]

Examples:
    # Download default models
    python scripts/download_models.py

    # Download specific models
    python scripts/download_models.py --models microsoft/trocr-base-handwritten,google/flan-t5-base

    # Download to custom directory
    python scripts/download_models.py --output-dir /path/to/models
"""
import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config.model_config import (
    ModelConfigFactory,
    ModelConfig,
    ModelType,
    ModelProvider,
    get_model_config_factory,
)


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)


class ModelDownloader:
    """
    Handles downloading of ML models from various providers.
    
    Supports:
    - Hugging Face models
    - Local model files
    - Custom model sources
    """
    
    def __init__(
        self,
        output_dir: str = "./models",
        hf_token: Optional[str] = None,
        force_download: bool = False
    ):
        """
        Initialize model downloader.
        
        Args:
            output_dir: Directory to store downloaded models
            hf_token: Hugging Face API token (optional)
            force_download: Force re-download even if model exists
        """
        self.output_dir = Path(output_dir)
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_API_TOKEN")
        self.force_download = force_download
        self.factory = get_model_config_factory()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Model metadata file
        self.metadata_file = self.output_dir / "models_metadata.json"
        
        logger.info(f"Model downloader initialized. Output directory: {self.output_dir}")
    
    def download_model(self, config: ModelConfig) -> Dict[str, Any]:
        """
        Download a single model.
        
        Args:
            config: Model configuration
            
        Returns:
            Dictionary with download status and metadata
        """
        model_name = config.name
        logger.info(f"Starting download for model: {model_name}")
        
        try:
            if config.provider == ModelProvider.HUGGING_FACE:
                result = self._download_huggingface_model(config)
            elif config.provider == ModelProvider.LOCAL:
                result = self._verify_local_model(config)
            else:
                result = {
                    "success": False,
                    "error": f"Unsupported provider: {config.provider}",
                    "model_name": model_name
                }
            
            # Update metadata
            if result.get("success"):
                self._update_metadata(model_name, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to download model {model_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "model_name": model_name
            }
    
    def _download_huggingface_model(self, config: ModelConfig) -> Dict[str, Any]:
        """
        Download model from Hugging Face.
        
        Args:
            config: Model configuration
            
        Returns:
            Download result dictionary
        """
        from huggingface_hub import snapshot_download, hf_hub_download
        from transformers import AutoTokenizer, AutoConfig
        
        model_id = config.model_id or config.name
        local_dir = self.output_dir / model_name_to_path(model_id)
        
        # Check if model already exists
        if local_dir.exists() and not self.force_download:
            if self._verify_model_files(local_dir, config):
                logger.info(f"Model {model_id} already exists at {local_dir}")
                return {
                    "success": True,
                    "model_name": config.name,
                    "path": str(local_dir),
                    "status": "already_exists"
                }
        
        logger.info(f"Downloading model {model_id} from Hugging Face...")
        
        try:
            # Download model files
            local_path = snapshot_download(
                repo_id=model_id,
                local_dir=local_dir,
                local_dir_use_symlinks=False,
                token=self.hf_token,
                revision=config.revision,
                ignore_patterns=["*.msgpack", "*.h5", "*.ot"],  # Only download safetensors/pytorch
            )
            
            # Download tokenizer if available
            try:
                logger.info(f"Downloading tokenizer for {model_id}...")
                tokenizer_path = local_dir / "tokenizer"
                tokenizer_path.mkdir(parents=True, exist_ok=True)
                
                AutoTokenizer.from_pretrained(
                    model_id,
                    revision=config.revision,
                ).save_pretrained(str(tokenizer_path))
                
            except Exception as e:
                logger.warning(f"Tokenizer download failed (may not be available): {e}")
            
            # Save model config
            self._save_model_config(local_dir, config)
            
            download_time = datetime.now().isoformat()
            
            logger.info(f"Successfully downloaded model {model_id} to {local_path}")
            
            return {
                "success": True,
                "model_name": config.name,
                "model_id": model_id,
                "path": str(local_path),
                "status": "downloaded",
                "download_time": download_time,
                "size_bytes": get_directory_size(Path(local_path))
            }
            
        except Exception as e:
            logger.error(f"Hugging Face download failed for {model_id}: {str(e)}")
            raise
    
    def _verify_local_model(self, config: ModelConfig) -> Dict[str, Any]:
        """
        Verify a local model exists and is valid.
        
        Args:
            config: Model configuration
            
        Returns:
            Verification result
        """
        model_path = Path(config.model_path) if config.model_path else None
        
        if not model_path or not model_path.exists():
            return {
                "success": False,
                "error": f"Local model path does not exist: {model_path}",
                "model_name": config.name
            }
        
        if self._verify_model_files(model_path, config):
            return {
                "success": True,
                "model_name": config.name,
                "path": str(model_path),
                "status": "verified"
            }
        else:
            return {
                "success": False,
                "error": "Model verification failed",
                "model_name": config.name
            }
    
    def _verify_model_files(self, model_path: Path, config: ModelConfig) -> bool:
        """
        Verify that required model files exist.
        
        Args:
            model_path: Path to model directory
            config: Model configuration
            
        Returns:
            True if all required files exist
        """
        # Check for common model files
        required_files = [
            "config.json",
        ]
        
        # Check for model weights (any of these)
        weight_files = [
            "pytorch_model.bin",
            "pytorch_model.safetensors",
            "model.safetensors",
            "tf_model.h5",
        ]
        
        has_weights = any((model_path / f).exists() for f in weight_files)
        has_config = any((model_path / f).exists() for f in required_files)
        
        return has_weights and has_config
    
    def _save_model_config(self, model_path: Path, config: ModelConfig) -> None:
        """
        Save model configuration metadata.
        
        Args:
            model_path: Path to model directory
            config: Model configuration
        """
        metadata = {
            "model_name": config.name,
            "model_id": config.model_id,
            "model_type": config.model_type,
            "provider": config.provider,
            "downloaded_at": datetime.now().isoformat(),
            "revision": config.revision,
            "config": config.dict()
        }
        
        config_path = model_path / "download_metadata.json"
        with open(config_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _update_metadata(self, model_name: str, result: Dict[str, Any]) -> None:
        """
        Update global metadata file.
        
        Args:
            model_name: Name of the model
            result: Download result
        """
        metadata = {}
        
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
            except Exception:
                metadata = {}
        
        metadata[model_name] = {
            **result,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def list_downloaded_models(self) -> List[Dict[str, Any]]:
        """
        List all downloaded models.
        
        Returns:
            List of model metadata
        """
        if not self.metadata_file.exists():
            return []
        
        with open(self.metadata_file, 'r') as f:
            return json.load(f)
    
    def cleanup_cache(self) -> int:
        """
        Clean up Hugging Face cache.
        
        Returns:
            Number of files removed
        """
        from huggingface_hub import scan_cache_dir
        
        try:
            cache_info = scan_cache_dir()
            logger.info(f"Hugging Face cache size: {cache_info.size_on_disk_str}")
            
            # Note: Actual cleanup would require deleting revisions
            # This is just informational for now
            return 0
            
        except Exception as e:
            logger.warning(f"Failed to scan cache: {e}")
            return 0


def model_name_to_path(model_name: str) -> str:
    """
    Convert model name to safe directory path.

    Args:
        model_name: Model name (e.g., 'microsoft/trocr-base-handwritten')

    Returns:
        Safe path string
    """
    return model_name.replace("/", "__")


def get_directory_size(path: Path) -> int:
    """
    Calculate total size of a directory.
    
    Args:
        path: Directory path
        
    Returns:
        Size in bytes
    """
    total_size = 0
    for entry in path.rglob('*'):
        if entry.is_file():
            total_size += entry.stat().st_size
    return total_size


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download ML models for Mathematics LLM OCR Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--models",
        type=str,
        default=None,
        help="Comma-separated list of model names to download (default: all default models)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./models",
        help="Directory to store downloaded models (default: ./models)"
    )
    
    parser.add_argument(
        "--hf-token",
        type=str,
        default=None,
        help="Hugging Face API token (or set HUGGINGFACE_API_TOKEN env var)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if model exists"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available models"
    )
    
    parser.add_argument(
        "--list-downloaded",
        action="store_true",
        help="List already downloaded models"
    )
    
    parser.add_argument(
        "--type",
        type=str,
        choices=["ocr", "solution", "all"],
        default="all",
        help="Type of models to download (default: all)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logger.level("DEBUG")
    
    # Initialize downloader
    downloader = ModelDownloader(
        output_dir=args.output_dir,
        hf_token=args.hf_token,
        force_download=args.force
    )
    
    # List available models
    if args.list:
        factory = get_model_config_factory()
        
        print("\n=== Available Models ===\n")
        
        if args.type in ["ocr", "all"]:
            print("OCR Models:")
            for name in factory.list_configs(ModelType.OCR):
                print(f"  - {name}")
            print()
        
        if args.type in ["solution", "all"]:
            print("Solution Models:")
            for name in factory.list_configs(ModelType.SOLUTION):
                print(f"  - {name}")
            print()
        
        return 0
    
    # List downloaded models
    if args.list_downloaded:
        models = downloader.list_downloaded_models()
        
        print("\n=== Downloaded Models ===\n")
        
        if not models:
            print("No models downloaded yet.")
        else:
            for name, metadata in models.items():
                status = metadata.get("status", "unknown")
                path = metadata.get("path", "N/A")
                size = metadata.get("size_bytes", 0)
                size_str = f"{size / (1024*1024):.2f} MB" if size else "N/A"
                
                print(f"  {name}")
                print(f"    Status: {status}")
                print(f"    Path: {path}")
                print(f"    Size: {size_str}")
                print()
        
        return 0
    
    # Download models
    factory = get_model_config_factory()
    
    if args.models:
        # Download specific models
        model_names = [m.strip() for m in args.models.split(",")]
    else:
        # Download default models based on type
        model_names = []
        
        if args.type in ["ocr", "all"]:
            model_names.append("microsoft/trocr-base-handwritten")
        
        if args.type in ["solution", "all"]:
            model_names.append("google/flan-t5-base")
    
    logger.info(f"Downloading {len(model_names)} model(s): {', '.join(model_names)}")
    
    # Download each model
    results = []
    for model_name in model_names:
        config = factory.get_config(model_name)
        
        if not config:
            logger.warning(f"Model configuration not found for {model_name}, using default")
            config = ModelConfig(
                name=model_name,
                model_type=ModelType.OCR if "trocr" in model_name.lower() else ModelType.SOLUTION,
                provider=ModelProvider.HUGGING_FACE,
                model_id=model_name,
            )
        
        result = downloader.download_model(config)
        results.append(result)
        
        if result.get("success"):
            logger.info(f"✓ Successfully downloaded {model_name}")
        else:
            logger.error(f"✗ Failed to download {model_name}: {result.get('error')}")
    
    # Summary
    print("\n=== Download Summary ===\n")
    successful = sum(1 for r in results if r.get("success"))
    total = len(results)
    
    print(f"Downloaded: {successful}/{total} models")
    
    if successful > 0:
        print(f"\nModels saved to: {args.output_dir}")
        print("\nTo use these models, set the environment variable:")
        print(f"  MODELS_PATH={args.output_dir}")
    
    return 0 if successful == total else 1


if __name__ == "__main__":
    sys.exit(main())
