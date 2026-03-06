"""
Image processing utilities for OCR preprocessing.
"""
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from typing import Tuple, Optional, Union, List
from loguru import logger


class ImagePreprocessor:
    """
    Image preprocessing class for OCR optimization.
    
    Provides various image enhancement techniques to improve OCR accuracy
    for mathematical expressions and text.
    """

    def __init__(
        self,
        target_width: int = 2048,
        target_height: int = 2048,
        dpi: int = 300
    ):
        """
        Initialize image preprocessor.
        
        Args:
            target_width: Target width for resized images
            target_height: Target height for resized images
            dpi: Target DPI for image processing
        """
        self.target_width = target_width
        self.target_height = target_height
        self.dpi = dpi

    def preprocess_for_ocr(self, image: Union[Image.Image, np.ndarray, str]) -> Image.Image:
        """
        Apply complete preprocessing pipeline for OCR.
        
        Args:
            image: PIL Image, numpy array, or file path
            
        Returns:
            Preprocessed PIL Image ready for OCR
        """
        # Load and convert image
        pil_image = self._load_image(image)
        
        # Apply preprocessing steps
        pil_image = self._resize_if_needed(pil_image)
        pil_image = self._convert_to_grayscale(pil_image)
        pil_image = self._apply_denoising(pil_image)
        pil_image = self._enhance_contrast(pil_image)
        pil_image = self._binarize(pil_image)
        pil_image = self._deskew(pil_image)
        pil_image = self._sharpen(pil_image)
        
        logger.debug(f"Image preprocessing completed. Final size: {pil_image.size}")
        return pil_image

    def _load_image(self, image: Union[Image.Image, np.ndarray, str]) -> Image.Image:
        """Load image from various sources."""
        if isinstance(image, str):
            # Load from file path
            try:
                pil_image = Image.open(image)
                logger.debug(f"Loaded image from file: {image}")
            except Exception as e:
                logger.error(f"Failed to load image from {image}: {e}")
                raise
        elif isinstance(image, np.ndarray):
            # Convert numpy array to PIL Image
            if len(image.shape) == 3 and image.shape[2] == 3:
                pil_image = Image.fromarray(image.astype('uint8'), 'RGB')
            elif len(image.shape) == 2:
                pil_image = Image.fromarray(image.astype('uint8'), 'L')
            else:
                raise ValueError(f"Unsupported image array shape: {image.shape}")
            logger.debug("Loaded image from numpy array")
        elif isinstance(image, Image.Image):
            pil_image = image
            logger.debug("Using provided PIL Image")
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")
        
        # Convert to RGB if necessary
        if pil_image.mode not in ['RGB', 'L']:
            pil_image = pil_image.convert('RGB')
            
        return pil_image

    def _resize_if_needed(self, image: Image.Image) -> Image.Image:
        """Resize image if it exceeds maximum dimensions."""
        width, height = image.size
        
        # Check if resizing is needed
        if width <= self.target_width and height <= self.target_height:
            return image
        
        # Calculate aspect ratio
        aspect_ratio = width / height
        
        # Determine new dimensions
        if aspect_ratio > 1:
            new_width = self.target_width
            new_height = int(self.target_width / aspect_ratio)
        else:
            new_height = self.target_height
            new_width = int(self.target_height * aspect_ratio)
        
        # Resize with high-quality resampling
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")
        
        return resized_image

    def _convert_to_grayscale(self, image: Image.Image) -> Image.Image:
        """Convert image to grayscale."""
        if image.mode == 'L':
            return image
        
        grayscale_image = image.convert('L')
        logger.debug("Converted image to grayscale")
        return grayscale_image

    def _apply_denoising(self, image: Image.Image) -> Image.Image:
        """Apply denoising filter to reduce image noise."""
        # Convert to numpy array for OpenCV processing
        image_array = np.array(image)
        
        # Apply non-local means denoising
        denoised_array = cv2.fastNlMeansDenoising(
            image_array,
            None,
            h=10,
            templateWindowSize=7,
            searchWindowSize=21
        )
        
        denoised_image = Image.fromarray(denoised_array, 'L')
        logger.debug("Applied denoising filter")
        return denoised_image

    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        """Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        image_array = np.array(image)
        
        # Apply CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced_array = clahe.apply(image_array)
        
        enhanced_image = Image.fromarray(enhanced_array, 'L')
        logger.debug("Applied contrast enhancement (CLAHE)")
        return enhanced_image

    def _binarize(self, image: Image.Image, method: str = 'otsu') -> Image.Image:
        """
        Binarize image using specified thresholding method.
        
        Args:
            image: Grayscale PIL Image
            method: Thresholding method ('otsu', 'adaptive', or 'simple')
            
        Returns:
            Binarized PIL Image
        """
        image_array = np.array(image)
        
        if method == 'otsu':
            # Otsu's thresholding
            _, binary_array = cv2.threshold(
                image_array,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            logger.debug("Applied Otsu's binarization")
            
        elif method == 'adaptive':
            # Adaptive thresholding
            binary_array = cv2.adaptiveThreshold(
                image_array,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )
            logger.debug("Applied adaptive binarization")
            
        else:
            # Simple thresholding
            _, binary_array = cv2.threshold(
                image_array,
                180,
                255,
                cv2.THRESH_BINARY
            )
            logger.debug("Applied simple binarization")
        
        return Image.fromarray(binary_array, 'L')

    def _deskew(self, image: Image.Image) -> Image.Image:
        """
        Deskew image to correct rotation.
        
        Args:
            image: PIL Image
            
        Returns:
            Deskewed PIL Image
        """
        image_array = np.array(image)
        
        # Calculate coordinates of non-zero points
        coords = np.column_stack(np.where(image_array > 0))
        
        if len(coords) < 10:
            # Not enough data points, return original
            return image
        
        # Fit minimum area rectangle
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        
        # Adjust angle for correct rotation
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Skip if angle is very small
        if abs(angle) < 0.5:
            return image
        
        # Rotate image to correct skew
        (h, w) = image_array.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_array = cv2.warpAffine(
            image_array,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        
        deskewed_image = Image.fromarray(rotated_array, 'L')
        logger.debug(f"Deskewed image by {angle:.2f} degrees")
        return deskewed_image

    def _sharpen(self, image: Image.Image) -> Image.Image:
        """Apply sharpening filter to enhance edges."""
        # Use PIL's sharpen filter
        sharpened_image = image.filter(ImageFilter.SHARPEN)
        logger.debug("Applied sharpening filter")
        return sharpened_image

    def enhance_for_handwriting(self, image: Union[Image.Image, np.ndarray, str]) -> Image.Image:
        """
        Apply specialized preprocessing for handwritten mathematical expressions.
        
        Args:
            image: Input image
            
        Returns:
            Enhanced PIL Image optimized for handwriting OCR
        """
        pil_image = self._load_image(image)
        pil_image = self._resize_if_needed(pil_image)
        pil_image = self._convert_to_grayscale(pil_image)
        
        # Apply stronger denoising for handwriting
        image_array = np.array(pil_image)
        denoised_array = cv2.fastNlMeansDenoising(
            image_array,
            None,
            h=15,
            templateWindowSize=7,
            searchWindowSize=21
        )
        pil_image = Image.fromarray(denoised_array, 'L')
        
        # Apply gamma correction for better contrast
        pil_image = self._apply_gamma_correction(pil_image, gamma=1.2)
        
        # Apply morphological operations to connect broken strokes
        pil_image = self._apply_morphological_operations(pil_image)
        
        # Binarize with adaptive thresholding
        pil_image = self._binarize(pil_image, method='adaptive')
        
        logger.debug("Applied handwriting-specific preprocessing")
        return pil_image

    def _apply_gamma_correction(self, image: Image.Image, gamma: float = 1.0) -> Image.Image:
        """Apply gamma correction to adjust brightness."""
        image_array = np.array(image).astype(np.float32) / 255.0
        corrected_array = np.power(image_array, 1.0 / gamma)
        corrected_array = (corrected_array * 255).astype(np.uint8)
        return Image.fromarray(corrected_array, 'L')

    def _apply_morphological_operations(self, image: Image.Image) -> Image.Image:
        """Apply morphological operations to enhance handwriting strokes."""
        image_array = np.array(image)
        
        # Define kernel for morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        
        # Apply closing to connect broken strokes
        closed_array = cv2.morphologyEx(image_array, cv2.MORPH_CLOSE, kernel)
        
        # Apply opening to remove small noise
        opened_array = cv2.morphologyEx(closed_array, cv2.MORPH_OPEN, kernel)
        
        logger.debug("Applied morphological operations")
        return Image.fromarray(opened_array, 'L')

    def detect_text_regions(
        self,
        image: Union[Image.Image, np.ndarray, str]
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect text regions in the image.
        
        Args:
            image: Input image
            
        Returns:
            List of bounding boxes (x, y, width, height) for detected text regions
        """
        pil_image = self._load_image(image)
        gray_image = self._convert_to_grayscale(pil_image)
        image_array = np.array(gray_image)
        
        # Apply thresholding
        _, binary_array = cv2.threshold(
            image_array,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        
        # Find contours
        contours, _ = cv2.findContours(
            binary_array,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Extract bounding boxes
        text_regions = []
        for contour in contours:
            # Filter small contours
            if cv2.contourArea(contour) > 100:
                x, y, w, h = cv2.boundingRect(contour)
                text_regions.append((x, y, w, h))
        
        logger.debug(f"Detected {len(text_regions)} text regions")
        return text_regions

    def crop_to_region(
        self,
        image: Union[Image.Image, np.ndarray, str],
        region: Tuple[int, int, int, int]
    ) -> Image.Image:
        """
        Crop image to specified region.
        
        Args:
            image: Input image
            region: Bounding box (x, y, width, height)
            
        Returns:
            Cropped PIL Image
        """
        pil_image = self._load_image(image)
        x, y, w, h = region
        cropped_image = pil_image.crop((x, y, x + w, y + h))
        logger.debug(f"Cropped image to region: {region}")
        return cropped_image

    def get_image_statistics(self, image: Union[Image.Image, np.ndarray, str]) -> dict:
        """
        Get statistical information about the image.
        
        Args:
            image: Input image
            
        Returns:
            Dictionary with image statistics
        """
        pil_image = self._load_image(image)
        gray_image = self._convert_to_grayscale(pil_image)
        image_array = np.array(gray_image)
        
        stats = {
            'width': pil_image.size[0],
            'height': pil_image.size[1],
            'mode': pil_image.mode,
            'mean_brightness': float(np.mean(image_array)),
            'std_brightness': float(np.std(image_array)),
            'min_brightness': int(np.min(image_array)),
            'max_brightness': int(np.max(image_array)),
            'histogram': np.histogram(image_array, bins=256, range=(0, 256))[0].tolist()
        }
        
        logger.debug(f"Image statistics: {stats['width']}x{stats['height']}, mean={stats['mean_brightness']:.2f}")
        return stats
