"""
Shared pytest fixtures for the Mercai backend.

Tests run against in-memory SQLite rather than MySQL so they need no running
container. That is only possible because the models avoid dialect-specific
types; if a future model needs one, give it a `.with_variant()` rather than
pinning these tests to MySQL.

IMPORTANT -- the `app` package collides across services
-------------------------------------------------------
Every microservice exposes its code under the same top-level package name
(`app`), and so does the legacy monolith at back_end/app/. Only one can be
importable at a time: whichever path lands first on sys.path wins, and the
loser resolves to the wrong module *silently*, with no import error.

`load_service()` below makes that switchable. Any fixture that imports from
`app` must call it first -- not just once at collection time, because an
earlier test may have already cached a different service's modules.
"""
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Makes `shared` importable. Per-service conftests insert their own path in
# front of this one so that `app` resolves to the service under test.
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _load_service(service_dir):
    """
    Make `app` resolve to the given service directory.

    Drops any cached `app` modules belonging to another service, then puts this
    service at the front of sys.path. Call it before importing anything from
    `app`; see the module docstring for why once-per-session is not enough.
    """
    for name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[name]

    path = str(service_dir)
    while path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)


@pytest.fixture()
def load_service():
    """Exposed as a fixture so per-service conftests need no cross-imports."""
    return _load_service


@pytest.fixture()
def engine():
    """A fresh in-memory database per test, with the full schema created."""
    from shared.database import Base
    import shared.models  # noqa: F401 - registers every model on the metadata

    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection, so ":memory:" persists
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    """Session factory bound to the test database."""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db(session_factory):
    """A session for arranging fixtures and asserting on results."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
