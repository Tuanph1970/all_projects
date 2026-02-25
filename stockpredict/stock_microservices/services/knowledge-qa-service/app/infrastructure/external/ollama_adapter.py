"""Ollama LLM adapter - implements LLMPort (Strategy pattern)."""
import json
import logging
from typing import AsyncIterator

import httpx

from app.domain.ports.llm_port import LLMPort

logger = logging.getLogger(__name__)


class OllamaLLMAdapter(LLMPort):
    """Adapter for Ollama API - implements LLMPort interface.

    Can be swapped for OpenAI, Anthropic, etc. via Strategy pattern.
    """

    def __init__(self, base_url: str, model: str = "llama3.1", timeout: float = 120.0):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def generate_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream generated text token by token from Ollama."""
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            content = data["message"]["content"]
                            if content:
                                yield content
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

    async def generate(self, messages: list[dict]) -> str:
        """Generate a complete response (non-streaming)."""
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    async def health_check(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
