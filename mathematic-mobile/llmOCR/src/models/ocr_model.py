"""
OCR Model implementation for mathematical text recognition.
"""
import time
from typing import Any, Dict, List, Optional, Union
import torch
from PIL import Image
import numpy as np
import cv2
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from loguru import logger

from .base import BaseMLModel, OCRResult, ModelType
from ..utils.image_processing import ImagePreprocessor


class OCRModel(BaseMLModel):
    """OCR model for mathematical text recognition."""
    
    def __init__(
        self, 
        model_name: str = "microsoft/trocr-base-math",
        device: str = "cpu",
        confidence_threshold: float = 0.8
    ):
        super().__init__(model_name, device)
        self.confidence_threshold = confidence_threshold
        self.processor: Optional[TrOCRProcessor] = None
        self.image_preprocessor = ImagePreprocessor()
        
    def load_model(self, model_path: Optional[str] = None) -> None:
        """Load the OCR model and processor."""
        try:
            start_time = time.time()
            logger.info(f"Loading OCR model: {self.model_name}")
            
            # Load processor and model
            self.processor = TrOCRProcessor.from_pretrained(self.model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(self.model_name)
            
            # Move model to specified device
            if self.device != "cpu":
                self.model = self.model.to(self.device)
            
            # Set model to evaluation mode
            self.model.eval()
            
            self._load_time = time.time() - start_time
            self.is_loaded = True
            
            logger.info(f"OCR model loaded successfully in {self._load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to load OCR model: {str(e)}")
            raise RuntimeError(f"OCR model loading failed: {str(e)}")
    
    def predict(self, input_data: Union[Image.Image, np.ndarray, str]) -> OCRResult:
        """
        Perform OCR on the input image.
        
        Args:
            input_data: PIL Image, numpy array, or image path
            
        Returns:
            OCRResult containing extracted text and metadata
        """
        if not self.is_model_loaded():
            raise RuntimeError("OCR model is not loaded")
        
        start_time = time.time()
        
        try:
            # Preprocess image
            image = self._prepare_image(input_data)
            processed_image = self.image_preprocessor.preprocess_for_ocr(image)
            
            # Generate pixel values
            pixel_values = self.processor(processed_image, return_tensors="pt").pixel_values
            
            if self.device != "cpu":
                pixel_values = pixel_values.to(self.device)
            
            # Generate predictions
            with torch.no_grad():
                generated_ids = self.model.generate(pixel_values)
            
            # Decode predictions
            generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Estimate confidence (simplified approach)
            confidence = self._calculate_confidence(generated_ids, generated_text)
            
            # Extract additional metadata
            metadata = {
                "image_size": processed_image.size,
                "model_name": self.model_name,
                "device": self.device,
                "preprocessing_applied": True
            }
            
            result = OCRResult(
                success=True,
                extracted_text=generated_text.strip(),
                confidence=confidence,
                processing_time=processing_time,
                metadata=metadata
            )
            
            logger.info(f"OCR completed in {processing_time:.3f}s with confidence {confidence:.3f}")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"OCR prediction failed: {str(e)}")
            
            return OCRResult(
                success=False,
                extracted_text="",
                confidence=0.0,
                processing_time=processing_time,
                metadata={"error": str(e)}
            )
    
    def predict_batch(self, images: List[Union[Image.Image, np.ndarray]]) -> List[OCRResult]:
        """
        Perform OCR on a batch of images.
        
        Args:
            images: List of PIL Images or numpy arrays
            
        Returns:
            List of OCRResult objects
        """
        if not self.is_model_loaded():
            raise RuntimeError("OCR model is not loaded")
        
        results = []
        for image in images:
            result = self.predict(image)
            results.append(result)
        
        return results
    
    def _prepare_image(self, input_data: Union[Image.Image, np.ndarray, str]) -> Image.Image:
        """Prepare image from various input formats."""
        if isinstance(input_data, str):
            # Load from file path
            image = Image.open(input_data)
        elif isinstance(input_data, np.ndarray):
            # Convert numpy array to PIL Image
            if len(input_data.shape) == 3 and input_data.shape[2] == 3:
                # RGB image
                image = Image.fromarray(input_data.astype('uint8'), 'RGB')
            elif len(input_data.shape) == 2:
                # Grayscale image
                image = Image.fromarray(input_data.astype('uint8'), 'L')
            else:
                raise ValueError(f"Unsupported image array shape: {input_data.shape}")
        elif isinstance(input_data, Image.Image):
            image = input_data
        else:
            raise TypeError(f"Unsupported input type: {type(input_data)}")
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image
    
    def _calculate_confidence(self, generated_ids: torch.Tensor, generated_text: str) -> float:
        """
        Calculate confidence score for the OCR result.
        This is a simplified approach - in practice, you might use model logits.
        """
        # Basic confidence estimation based on text length and token characteristics
        if not generated_text.strip():
            return 0.0
        
        # Penalize very short results
        if len(generated_text.strip()) < 3:
            base_confidence = 0.5
        else:
            base_confidence = 0.85
        
        # Adjust based on presence of mathematical symbols
        math_symbols = ['=', '+', '-', '*', '/', '^', '(', ')', 'x', 'y', 'z']
        math_symbol_count = sum(1 for char in generated_text if char in math_symbols)
        
        if math_symbol_count > 0:
            # Mathematical text detected, likely higher confidence
            confidence_boost = min(0.1, math_symbol_count * 0.02)
            base_confidence += confidence_boost
        
        return min(base_confidence, 1.0)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the OCR model."""
        info = {
            "model_name": self.model_name,
            "model_type": ModelType.OCR.value,
            "device": self.device,
            "is_loaded": self.is_loaded,
            "confidence_threshold": self.confidence_threshold,
            "supported_formats": ["PIL.Image", "numpy.ndarray", "file_path"]
        }
        
        if self._load_time is not None:
            info["load_time_seconds"] = self._load_time
        
        if self.is_loaded and self.model is not None:
            try:
                # Get model parameter count
                total_params = sum(p.numel() for p in self.model.parameters())
                trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
                
                info.update({
                    "total_parameters": total_params,
                    "trainable_parameters": trainable_params,
                    "model_size_mb": total_params * 4 / (1024 * 1024)  # Approximate size in MB
                })
            except Exception as e:
                logger.warning(f"Could not get model parameter info: {e}")
        
        info.update(self.get_device_info())
        
        return info
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """Set the confidence threshold for OCR results."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        self.confidence_threshold = threshold
        logger.info(f"OCR confidence threshold set to {threshold}")
    
    def validate_result(self, result: OCRResult) -> bool:
        """Validate OCR result against confidence threshold."""
        return result.success and result.confidence >= self.confidence_threshold


class MathematicalOCRModel(OCRModel):
    """Specialized OCR model optimized for mathematical expressions."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Add mathematical symbol mappings
        self.math_symbol_corrections = {
            '×': '*',
            '÷': '/',
            '−': '-',
            '±': '±',
            '∞': 'infinity',
            '∑': 'sum',
            '∫': 'integral',
            '∂': 'partial',
            '√': 'sqrt',
            'α': 'alpha',
            'β': 'beta',
            'γ': 'gamma',
            'δ': 'delta',
            'π': 'pi',
            'θ': 'theta',
            'λ': 'lambda',
            'μ': 'mu',
            'σ': 'sigma',
        }
    
    def predict(self, input_data: Union[Image.Image, np.ndarray, str]) -> OCRResult:
        """Perform mathematical OCR with post-processing."""
        result = super().predict(input_data)
        
        if result.success:
            # Apply mathematical symbol corrections
            corrected_text = self._apply_math_corrections(result.extracted_text)
            
            # Update result with corrected text
            result.extracted_text = corrected_text
            result.metadata.update({
                "math_corrections_applied": True,
                "original_text": result.extracted_text
            })
        
        return result
    
    def _apply_math_corrections(self, text: str) -> str:
        """Apply mathematical symbol corrections to the extracted text."""
        corrected_text = text
        
        for symbol, correction in self.math_symbol_corrections.items():
            corrected_text = corrected_text.replace(symbol, correction)
        
        return corrected_text