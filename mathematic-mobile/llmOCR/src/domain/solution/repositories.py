"""
Solution domain repository interface.

Defines the contract for mathematical problem-solving model adapters.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Union

from ..shared.value_objects import SolutionResult


class ISolutionModelRepository(ABC):
    """Port for solution-generation model inference."""

    @abstractmethod
    def predict(self, input_data: Union[str, Dict[str, Any]]) -> SolutionResult:
        """Generate a solution for the supplied problem."""
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
