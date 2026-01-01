import os
import logging
import asyncio
from typing import Optional
from PIL import Image
import pytesseract
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class OCRService:
    """Service for extracting text from images using OCR"""

    def __init__(self):
        self.tesseract_cmd = os.environ.get("TESSERACT_CMD", "/usr/bin/tesseract")
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    async def extract_text(self, image_path: str) -> Optional[str]:
        """
        Extract text from an image file using Tesseract OCR

        Args:
            image_path: Path to the image file

        Returns:
            Extracted text or None if extraction fails
        """
        try:
            # Run OCR in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._process_image, image_path)
            return text

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return None

    def _process_image(self, image_path: str) -> Optional[str]:
        """Process image and extract text"""
        try:
            # Load and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return None

            # Preprocess for better OCR
            processed = self._preprocess_image(image)

            # Convert to PIL Image for pytesseract
            pil_image = Image.fromarray(processed)

            # Configure Tesseract for math
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789+-*/=()[]{}^.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ '

            # Extract text
            text = pytesseract.image_to_string(pil_image, config=custom_config)

            # Clean up text
            text = self._clean_text(text)

            logger.info(f"OCR extracted: {text[:100]}...")
            return text

        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return None

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR accuracy"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Denoise
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)

        # Deskew if needed
        coords = np.column_stack(np.where(denoised < 255))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            if abs(angle) > 0.5:
                (h, w) = denoised.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                denoised = cv2.warpAffine(
                    denoised, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )

        return denoised

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""

        # Remove extra whitespace
        text = " ".join(text.split())

        # Fix common OCR mistakes in math
        replacements = {
            "×": "*",
            "÷": "/",
            "−": "-",
            "—": "-",
            "l": "1",  # Common OCR mistake
            "O": "0",  # Only if likely a number context
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text.strip()

    async def extract_equations(self, image_path: str) -> list:
        """
        Extract individual equations from an image

        Args:
            image_path: Path to the image file

        Returns:
            List of extracted equations
        """
        text = await self.extract_text(image_path)
        if not text:
            return []

        # Split by common equation separators
        equations = []
        for line in text.split("\n"):
            line = line.strip()
            if line and any(op in line for op in ["=", "+", "-", "*", "/", "^"]):
                equations.append(line)

        return equations
