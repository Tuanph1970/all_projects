"""
Fixtures for the intel service.

Replaces tests/ai/, which covered the listing optimizer. Those 33 tests went
with the feature; what is here covers the half of that service which survived
the removal of Ollama -- the flag, quota and hashing machinery that price
intelligence now depends on.

See the root conftest for why `load_service` exists: every service exposes a
top-level `app` package, so only one can be importable at a time.
"""
from pathlib import Path

import pytest


@pytest.fixture()
def intel(load_service):
    """Make `app` resolve to services/intel, then hand back the guardrails module."""
    load_service(Path(__file__).resolve().parents[2] / "services" / "intel")
    import app.services.guardrails as guardrails

    return guardrails


@pytest.fixture()
def fake_redis(monkeypatch):
    """
    Swap the Redis client behind the cache singleton.

    `RedisCache.client` is a read-only property, so patching the attribute
    fails. The backing `_client` is what has to move -- and it must be patched
    on the *instance*, not the class: `_initialize_pool` does `self._client =`,
    which shadows the class-level declaration, so a class-level patch is
    silently ignored and every quota test passes for the wrong reason.

    Pass None to simulate an outage. monkeypatch restores it afterwards, which
    matters because RedisCache is a singleton shared across the whole session.
    """
    from shared.cache import cache

    def _swap(client):
        monkeypatch.setattr(cache, "_client", client, raising=False)
        return client

    return _swap
