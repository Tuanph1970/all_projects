"""Offline service-test fixtures: in-memory price source + sqlite event store."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENVIRONMENT", "test")

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from event_reaction.ingest import InMemoryPriceSource

from app.deps import get_service
from app.main import app
from app.repositories.event_repository import MySqlEventRepository
from app.services.event_reaction_service import EventReactionService


@pytest.fixture
def price_index():
    return pd.date_range("2022-01-03", periods=300, freq="B", tz="UTC")


@pytest.fixture
def price_map(price_index):
    rng = np.random.default_rng(0)
    rm = rng.normal(0.0, 0.01, len(price_index) - 1)
    ra = 1.0 * rm + rng.normal(0.0, 0.002, len(price_index) - 1)
    market = pd.Series(100 * np.exp(np.concatenate([[0.0], np.cumsum(rm)])), index=price_index)
    asset = pd.Series(100 * np.exp(np.concatenate([[0.0], np.cumsum(ra)])), index=price_index)
    return {"AAA": asset, "IDX": market}


@pytest.fixture
def sqlite_repo():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    repo = MySqlEventRepository(engine)
    repo.ensure_schema()
    return repo


@pytest.fixture
def service(price_map, sqlite_repo):
    return EventReactionService(InMemoryPriceSource(price_map), sqlite_repo)


@pytest.fixture
def client(service):
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
