"""
Ollama client.

The only place in the codebase that talks to a language model. Everything it
exposes is synchronous, because the rest of the backend is synchronous
(endpoints are `def`, not `async def`, and run in FastAPI's threadpool).

Failure policy: this client raises typed errors and never retries more than
once. Callers are responsible for turning those into a 503 -- an AI feature
being down must never break the action it is attached to.
"""
import json
import logging
import threading
from typing import Any, Dict, Optional

import httpx

from shared.config import settings

logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    """Base class for model-call failures."""


class OllamaUnavailable(OllamaError):
    """Could not reach the model host, or it timed out."""


class OllamaInvalidResponse(OllamaError):
    """The model replied, but not with usable JSON."""


class OllamaBusy(OllamaError):
    """Too many generations already in flight; shed rather than queue."""


# A single Ollama instance serialises requests. Bounding in-flight work here
# means excess load fails fast with a 429 instead of piling up behind a long
# timeout and exhausting the threadpool.
_semaphore = threading.BoundedSemaphore(settings.AI_MAX_CONCURRENT_GENERATIONS)


class OllamaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    def is_available(self) -> bool:
        """Cheap reachability probe for the health endpoint. Never raises."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.4,
        max_tokens: int = 900,
        retry_on_invalid: bool = True,
    ) -> Dict[str, Any]:
        """
        Run a prompt in Ollama's JSON mode and return the parsed object.

        A response that does not parse is retried once at temperature 0, which
        is the setting most likely to produce well-formed output. After that it
        is a hard failure -- free text is never handed back to a caller that
        asked for structure.
        """
        acquired = _semaphore.acquire(blocking=False)
        if not acquired:
            raise OllamaBusy("Too many generations in flight")

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            raw = self._post(payload)

            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                if not retry_on_invalid:
                    raise OllamaInvalidResponse("Model did not return valid JSON")

            logger.warning("Ollama returned invalid JSON; retrying at temperature 0")
            payload["options"]["temperature"] = 0.0
            raw = self._post(payload)
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raise OllamaInvalidResponse("Model did not return valid JSON after retry")
        finally:
            _semaphore.release()

    def _post(self, payload: Dict[str, Any]) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise OllamaUnavailable(f"Model timed out after {self.timeout}s") from exc
        except httpx.HTTPError as exc:
            raise OllamaUnavailable(f"Could not reach model host: {exc}") from exc

        if response.status_code != 200:
            raise OllamaUnavailable(
                f"Model host returned {response.status_code}: {response.text[:200]}"
            )

        return response.json().get("response", "")


ollama_client = OllamaClient()
