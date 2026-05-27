"""Shared test fixtures."""
from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def brownian(rng):
    """500-day random-walk price series."""
    returns = rng.normal(0, 0.01, 500)
    return np.cumsum(returns)


@pytest.fixture
def ar1_series(rng):
    """AR(1) with φ=0.8, length 1024."""
    N = 1024
    x = np.zeros(N)
    noise = rng.normal(0, 1.0, N)
    for t in range(1, N):
        x[t] = 0.8 * x[t - 1] + noise[t]
    return x


@pytest.fixture
def sinusoidal(rng):
    """Sum of three sine waves + noise, length 256."""
    t = np.arange(256)
    signal = (
        np.sin(2 * np.pi * t / 32)
        + 0.5 * np.sin(2 * np.pi * t / 8)
        + 0.25 * np.sin(2 * np.pi * t / 4)
    )
    return signal + rng.normal(0, 0.05, 256)
