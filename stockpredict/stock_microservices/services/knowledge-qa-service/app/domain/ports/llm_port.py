"""Abstract interface for LLM providers (Strategy pattern)."""
from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.domain.value_objects.graph_context import GraphContext
from app.domain.entities.chat_message import ChatMessage


class LLMPort(ABC):
    """Port for LLM text generation - enables swapping providers."""

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """Stream generated text token by token."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
    ) -> str:
        """Generate a complete response (non-streaming)."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM service is reachable."""
        ...
