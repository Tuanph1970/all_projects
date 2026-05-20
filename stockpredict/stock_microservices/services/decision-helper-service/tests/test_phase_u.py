"""Phase U (F-200..F-203) — Correlation engine unit tests."""
import math
from typing import Dict, List, Optional
from datetime import datetime

import pytest

from app.models.schemas import CorrelationPairItem, CorrelationMatrixResponse
from app.services.correlation import (
    _log_returns,
    _pearson,
    compute_correlation_matrix,
    would_breach_max_correlation,
)


# ── CorrelationPairItem schema ────────────────────────────────────────────────

class TestCorrelationPairItem:
    def test_basic(self):
        p = CorrelationPairItem(ticker_a="VCB", ticker_b="TCB", correlation=0.72, breaches_limit=True)
        assert p.ticker_a == "VCB"
        assert p.correlation == 0.72
        assert p.breaches_limit is True

    def test_none_correlation_ok(self):
        p = CorrelationPairItem(ticker_a="A", ticker_b="B", correlation=None)
        assert p.correlation is None
        assert p.breaches_limit is False

    def test_negative_correlation(self):
        p = CorrelationPairItem(ticker_a="VNM", ticker_b="HPG", correlation=-0.45)
        assert p.correlation == -0.45


class TestCorrelationMatrixResponse:
    def _make(self, **kw):
        defaults = dict(
            user_id=1,
            computed_at=datetime.utcnow(),
            tickers=["VCB", "TCB"],
            pairs=[CorrelationPairItem(ticker_a="VCB", ticker_b="TCB", correlation=0.55)],
            max_correlation=0.7,
            any_breach=False,
        )
        defaults.update(kw)
        return CorrelationMatrixResponse(**defaults)

    def test_construction(self):
        r = self._make()
        assert r.tickers == ["VCB", "TCB"]
        assert r.max_correlation == 0.7
        assert r.any_breach is False
        assert r.lookback_days == 60

    def test_any_breach_true(self):
        r = self._make(
            pairs=[CorrelationPairItem(ticker_a="VCB", ticker_b="TCB", correlation=0.85, breaches_limit=True)],
            any_breach=True,
        )
        assert r.any_breach is True

    def test_empty_tickers(self):
        r = self._make(tickers=[], pairs=[])
        assert r.tickers == []
        assert r.pairs == []


# ── _log_returns ─────────────────────────────────────────────────────────────

class TestLogReturns:
    def test_length(self):
        prices = [10.0, 11.0, 10.5, 12.0]
        returns = _log_returns(prices)
        assert len(returns) == 4

    def test_first_element_is_none(self):
        returns = _log_returns([100.0, 101.0])
        assert returns[0] is None

    def test_positive_return(self):
        returns = _log_returns([100.0, 110.0])
        expected = math.log(110.0 / 100.0)
        assert returns[1] is not None
        assert abs(returns[1] - expected) < 1e-10

    def test_negative_return(self):
        returns = _log_returns([100.0, 90.0])
        assert returns[1] is not None
        assert returns[1] < 0

    def test_zero_price_gives_none(self):
        returns = _log_returns([100.0, 0.0, 110.0])
        assert returns[1] is None  # zero price → skip

    def test_negative_price_gives_none(self):
        returns = _log_returns([100.0, -5.0])
        assert returns[1] is None

    def test_flat_series_gives_zeros(self):
        returns = _log_returns([50.0, 50.0, 50.0])
        for r in returns[1:]:
            assert r is not None
            assert abs(r) < 1e-12


# ── _pearson ──────────────────────────────────────────────────────────────────

class TestPearson:
    def _series(self, n: int, noise: float = 0.0) -> List[Optional[float]]:
        """Monotonically increasing series with optional noise."""
        import random
        rng = random.Random(42)
        return [None] + [float(i) + rng.uniform(-noise, noise) for i in range(n)]

    def test_perfect_positive_correlation(self):
        x = [None] + [float(i) for i in range(25)]
        y = [None] + [float(i) for i in range(25)]
        r = _pearson(x, y)
        assert r is not None
        assert abs(r - 1.0) < 1e-6

    def test_perfect_negative_correlation(self):
        x = [None] + [float(i) for i in range(25)]
        y = [None] + [float(-i) for i in range(25)]
        r = _pearson(x, y)
        assert r is not None
        assert abs(r + 1.0) < 1e-6

    def test_zero_correlation_on_constant(self):
        x = [None] + [1.0] * 25
        y = [None] + [float(i) for i in range(25)]
        r = _pearson(x, y)
        assert r is None  # constant series → variance 0 → no correlation defined

    def test_returns_none_when_too_few_obs(self):
        x = [None] + [1.0, 2.0, 3.0]   # only 3 valid
        y = [None] + [1.0, 2.0, 3.0]
        r = _pearson(x, y)
        assert r is None  # below _CORRELATION_MIN_OBS = 20

    def test_handles_none_in_middle(self):
        x = [None, 1.0, None, 3.0] + [float(i) for i in range(20)]
        y = [None, 1.0, None, 3.0] + [float(i) for i in range(20)]
        r = _pearson(x, y)
        assert r is not None  # enough valid pairs

    def test_range_bounded(self):
        x = [None] + [float(i) for i in range(30)]
        y = [None] + [float(i) * 0.5 + 1.0 for i in range(30)]
        r = _pearson(x, y)
        assert r is not None
        assert -1.0 <= r <= 1.0


# ── compute_correlation_matrix ───────────────────────────────────────────────

class TestComputeCorrelationMatrix:
    @pytest.mark.asyncio
    async def test_single_ticker_diagonal_only(self):
        from unittest.mock import patch, AsyncMock
        mock_closes = list(range(1, 70))  # 69 bars
        with patch(
            "app.services.correlation._fetch_closes",
            new=AsyncMock(return_value=[float(x) for x in mock_closes]),
        ):
            matrix = await compute_correlation_matrix(["VCB"], "tok")
        assert matrix["VCB"]["VCB"] == 1.0

    @pytest.mark.asyncio
    async def test_identical_series_gives_one(self):
        from unittest.mock import patch, AsyncMock
        prices = [100.0 + i for i in range(65)]

        async def _mock_fetch(ticker, jwt_token):
            return prices

        with patch("app.services.correlation._fetch_closes", side_effect=_mock_fetch):
            matrix = await compute_correlation_matrix(["VCB", "TCB"], "tok")
        r = matrix["VCB"]["TCB"]
        assert r is not None
        assert abs(r - 1.0) < 1e-4

    @pytest.mark.asyncio
    async def test_symmetric(self):
        from unittest.mock import patch, AsyncMock
        prices_a = [100.0 + i * 0.5 for i in range(65)]
        prices_b = [200.0 + i * 0.3 for i in range(65)]

        async def _mock_fetch(ticker, jwt_token):
            return prices_a if ticker == "VCB" else prices_b

        with patch("app.services.correlation._fetch_closes", side_effect=_mock_fetch):
            matrix = await compute_correlation_matrix(["VCB", "TCB"], "tok")
        assert matrix["VCB"]["TCB"] == matrix["TCB"]["VCB"]

    @pytest.mark.asyncio
    async def test_none_when_fetch_fails(self):
        from unittest.mock import patch, AsyncMock
        async def _mock_fetch(ticker, jwt_token):
            return None

        with patch("app.services.correlation._fetch_closes", side_effect=_mock_fetch):
            matrix = await compute_correlation_matrix(["VCB", "TCB"], "tok")
        assert matrix["VCB"]["TCB"] is None

    @pytest.mark.asyncio
    async def test_three_tickers(self):
        from unittest.mock import patch
        prices = {
            "VCB": [100.0 + i for i in range(65)],
            "TCB": [50.0 + i * 0.8 for i in range(65)],
            "HPG": [30.0 + i * 1.2 for i in range(65)],
        }

        async def _mock_fetch(ticker, jwt_token):
            return prices.get(ticker)

        with patch("app.services.correlation._fetch_closes", side_effect=_mock_fetch):
            matrix = await compute_correlation_matrix(["VCB", "TCB", "HPG"], "tok")
        assert "VCB" in matrix
        assert "TCB" in matrix["VCB"]
        assert "HPG" in matrix["VCB"]


# ── would_breach_max_correlation ─────────────────────────────────────────────

class TestWouldBreachMaxCorrelation:
    def _matrix(self, corr: float) -> Dict:
        return {
            "VCB": {"VCB": 1.0, "TCB": corr},
            "TCB": {"TCB": 1.0, "VCB": corr},
        }

    def test_no_breach_below_limit(self):
        matrix = self._matrix(0.65)
        result = would_breach_max_correlation(matrix, "VCB", max_correlation=0.7)
        assert result is None

    def test_breach_above_limit(self):
        matrix = self._matrix(0.85)
        result = would_breach_max_correlation(matrix, "VCB", max_correlation=0.7)
        assert result is not None
        other, corr = result
        assert other == "TCB"
        assert abs(corr - 0.85) < 1e-9

    def test_exact_limit_is_not_breach(self):
        matrix = self._matrix(0.70)
        result = would_breach_max_correlation(matrix, "VCB", max_correlation=0.7)
        assert result is None  # > not >=

    def test_just_over_limit_is_breach(self):
        matrix = self._matrix(0.701)
        result = would_breach_max_correlation(matrix, "VCB", max_correlation=0.7)
        assert result is not None

    def test_none_correlation_not_breach(self):
        matrix = {
            "VCB": {"VCB": 1.0, "TCB": None},
            "TCB": {"TCB": 1.0, "VCB": None},
        }
        result = would_breach_max_correlation(matrix, "VCB", max_correlation=0.7)
        assert result is None

    def test_ticker_not_in_matrix(self):
        matrix = {"VCB": {"VCB": 1.0}}
        result = would_breach_max_correlation(matrix, "HPG", max_correlation=0.7)
        assert result is None

    def test_returns_first_breach(self):
        matrix = {
            "NEW": {"NEW": 1.0, "VCB": 0.9, "TCB": 0.8},
            "VCB": {"VCB": 1.0, "NEW": 0.9, "TCB": 0.6},
            "TCB": {"TCB": 1.0, "NEW": 0.8, "VCB": 0.6},
        }
        result = would_breach_max_correlation(matrix, "NEW", max_correlation=0.7)
        assert result is not None
        _, corr = result
        assert corr > 0.7
