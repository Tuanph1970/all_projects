"""Offline service-test fixtures for news-service (N1 scaffold)."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.repositories.news_repository import NewsRepository


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def news_repo():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    repo = NewsRepository(engine)
    repo.ensure_schema()
    return repo
