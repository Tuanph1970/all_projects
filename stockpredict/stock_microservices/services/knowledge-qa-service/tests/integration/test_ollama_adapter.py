"""Integration tests for OllamaLLMAdapter.

Requires a running Ollama instance with a model pulled.
Skip with: pytest -m "not integration"
"""
import pytest
from app.infrastructure.external.ollama_adapter import OllamaLLMAdapter

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1"


@pytest.fixture
def adapter():
    return OllamaLLMAdapter(base_url=OLLAMA_URL, model=OLLAMA_MODEL, timeout=30.0)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_check(adapter):
    result = await adapter.health_check()
    if not result:
        pytest.skip("Ollama not available")
    assert result is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generate(adapter):
    if not await adapter.health_check():
        pytest.skip("Ollama not available")

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be brief."},
        {"role": "user", "content": "Say hello in one word."},
    ]
    result = await adapter.generate(messages)
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generate_stream(adapter):
    if not await adapter.health_check():
        pytest.skip("Ollama not available")

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be brief."},
        {"role": "user", "content": "Say hello in one word."},
    ]
    tokens = []
    async for token in adapter.generate_stream(messages):
        tokens.append(token)

    assert len(tokens) > 0
    full_text = "".join(tokens)
    assert len(full_text) > 0
