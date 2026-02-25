"""Domain service for orchestrating answer generation."""
from typing import AsyncIterator

from app.domain.ports.llm_port import LLMPort
from app.domain.value_objects.graph_context import GraphContext


class AnswerGenerationService:
    """Orchestrates LLM call with graph context to generate answers."""

    def __init__(self, llm_port: LLMPort):
        self._llm_port = llm_port

    async def generate_answer_stream(
        self, messages: list[dict]
    ) -> AsyncIterator[str]:
        """Stream answer tokens from the LLM."""
        async for token in self._llm_port.generate_stream(messages):
            yield token

    async def generate_answer(self, messages: list[dict]) -> str:
        """Generate a complete answer (non-streaming)."""
        return await self._llm_port.generate(messages)
