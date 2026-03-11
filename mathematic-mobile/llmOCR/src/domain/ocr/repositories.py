"""
OCR domain repository interface.

Defines the contract that any OCR model adapter must satisfy.
Infrastructure implementations live in src/infrastructure/ml/.
"""
from abc import ABC, abstractmethod

from PIL import Image

from ..shared.value_objects import OCRResult


class IOCRModelRepository(ABC):
    """Port for OCR model inference.  Infrastructure adapters implement this."""

    @abstractmethod
    def predict(self, image: Image.Image) -> OCRResult:
        """Extract text from a PIL image."""
        ...

    @abstractmethod
    def load(self) -> None:
        """Load the model weights into memory."""
        ...

    @abstractmethod
    def unload(self) -> None:
        """Release model weights from memory."""
        ...

    @abstractmethod
    def is_loaded(self) -> bool:
        """Return True when the model is ready for inference."""
        ...

    @abstractmethod
    def set_confidence_threshold(self, threshold: float) -> None:
        """Configure the minimum confidence for accepted results."""
        ...
