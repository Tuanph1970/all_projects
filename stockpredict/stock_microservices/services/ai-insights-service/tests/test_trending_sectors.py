"""Tests for the /trending and /sectors endpoints shipped in Sprint B.

The endpoints depend on httpx calls into stock-data-service. We patch
those at the InsightsService level rather than running a real upstream,
so the tests stay fast and verify both the success path and the
degrade-gracefully path.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.services.insights_service import InsightsService


# ---------------------------------------------------------------------------
# /trending — derives topics + hot_stocks from top-mover signals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trending_with_real_movers_synthesizes_topics(client: AsyncClient):
    """Mock stock-data top-movers returning gainers + losers + actives.
    Expect 3 topics (bull/bear/volume) and bullish-leaning mood."""
    fake_movers = {
        "gainers": [
            {"symbol": "FPT", "change_percent": 5.2},
            {"symbol": "VNM", "change_percent": 4.1},
            {"symbol": "VCB", "change_percent": 3.0},
            {"symbol": "VIC", "change_percent": 2.5},
            {"symbol": "HPG", "change_percent": 2.0},
        ],
        "losers": [
            {"symbol": "MSN", "change_percent": -3.0},
            {"symbol": "VHM", "change_percent": -1.8},
        ],
        "actives": [
            {"symbol": "FPT"},
            {"symbol": "HPG"},
            {"symbol": "VCB"},
        ],
    }

    with patch.object(
        InsightsService, "_fetch_top_movers", AsyncMock(return_value=fake_movers)
    ):
        r = await client.get("/stock_helper/api/v2/ai/trending")

    assert r.status_code == 200, r.text
    body = r.json()
    # Three topics: gainers led + losers + active volume
    assert len(body["topics"]) == 3
    topic_categories = {t["category"] for t in body["topics"]}
    assert topic_categories == {"market", "volume"}

    # Hot stocks should mirror the top-actives list (in order).
    assert body["hot_stocks"] == ["FPT", "HPG", "VCB"]

    # 5 gainers vs 2 losers is bullish-leaning by enough margin (>2)
    assert body["market_mood"] == "bullish"


@pytest.mark.asyncio
async def test_trending_market_mood_bearish_when_losers_dominate(client: AsyncClient):
    fake_movers = {
        "gainers": [{"symbol": "FPT", "change_percent": 1.0}],
        "losers": [
            {"symbol": s, "change_percent": -2.0}
            for s in ["VNM", "VCB", "VIC", "HPG", "MSN"]
        ],
        "actives": [{"symbol": "MSN"}],
    }
    with patch.object(
        InsightsService, "_fetch_top_movers", AsyncMock(return_value=fake_movers)
    ):
        r = await client.get("/stock_helper/api/v2/ai/trending")
    assert r.status_code == 200
    assert r.json()["market_mood"] == "bearish"


@pytest.mark.asyncio
async def test_trending_market_mood_unknown_when_no_data(client: AsyncClient):
    """Stock-data unreachable → degrade gracefully, mood='unknown'."""
    fake_movers = {"gainers": [], "losers": [], "actives": []}
    with patch.object(
        InsightsService, "_fetch_top_movers", AsyncMock(return_value=fake_movers)
    ):
        r = await client.get("/stock_helper/api/v2/ai/trending")
    assert r.status_code == 200
    body = r.json()
    assert body["market_mood"] == "unknown"
    assert body["hot_stocks"] == []
    assert body["topics"] == []


@pytest.mark.asyncio
async def test_trending_handles_missing_symbol_fields(client: AsyncClient):
    """Upstream gives back records without symbol → those entries are skipped,
    response still well-formed."""
    fake_movers = {
        "gainers": [{"change_percent": 5.0}, {"symbol": "VNM"}],
        "losers": [],
        "actives": [{"symbol": "FPT"}, {}],
    }
    with patch.object(
        InsightsService, "_fetch_top_movers", AsyncMock(return_value=fake_movers)
    ):
        r = await client.get("/stock_helper/api/v2/ai/trending")
    assert r.status_code == 200
    body = r.json()
    # Topics should only include the symbol-bearing entries
    market_topic = next(t for t in body["topics"] if t["category"] == "market")
    assert "VNM" in market_topic["related_symbols"]
    assert None not in market_topic["related_symbols"]


# ---------------------------------------------------------------------------
# /sectors — sector sentiment from average constituent change_percent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sectors_uses_real_industry_data(client: AsyncClient):
    """Mock /industries/<code>/companies returning real-shaped data;
    expect SectorInsight with computed sentiment per sector."""
    # All 5 sectors return the same shape — bullish for the ones with
    # positive avg, bearish for negative, neutral for ~0.
    sector_data = {
        "8300": [  # Banking — strong bullish
            {"symbol": "VCB", "change_percent": 2.0},
            {"symbol": "TCB", "change_percent": 1.5},
            {"symbol": "BID", "change_percent": 1.2},
        ],
        "8770": [  # Real Estate — bearish
            {"symbol": "VHM", "change_percent": -2.5},
            {"symbol": "VIC", "change_percent": -1.8},
            {"symbol": "NVL", "change_percent": -1.0},
        ],
        "9530": [  # Tech — neutral
            {"symbol": "FPT", "change_percent": 0.3},
            {"symbol": "CMG", "change_percent": 0.1},
        ],
        "1750": [],  # Materials — empty (no data)
        "3500": [  # Food&Bev — slight bullish but below threshold
            {"symbol": "VNM", "change_percent": 0.5},
        ],
    }

    async def fake_fetch(self, code):
        return sector_data.get(code, [])

    with patch.object(InsightsService, "_fetch_industry_companies", fake_fetch):
        r = await client.get("/stock_helper/api/v2/ai/sectors")

    assert r.status_code == 200, r.text
    body = r.json()
    # Materials had no data → not included; the other 4 should be.
    sector_names = {s["sector_name"] for s in body["sectors"]}
    assert "Banking" in sector_names
    assert "Real Estate" in sector_names
    assert "Industrial Materials" not in sector_names

    by_name = {s["sector_name"]: s for s in body["sectors"]}
    assert by_name["Banking"]["sentiment"] == "bullish"
    assert by_name["Real Estate"]["sentiment"] == "bearish"
    assert by_name["Technology"]["sentiment"] == "neutral"
    # Top picks for Banking should be the highest-change names first
    assert by_name["Banking"]["top_picks"][0] == "VCB"

    # best_sector and worst_sector are populated
    assert body["best_sector"] == "Banking"
    assert body["worst_sector"] == "Real Estate"


@pytest.mark.asyncio
async def test_sectors_empty_when_industry_feed_unreachable(client: AsyncClient):
    """All industry calls fail → sectors=[], best/worst='—'."""
    async def fake_fetch(self, code):
        return []

    with patch.object(InsightsService, "_fetch_industry_companies", fake_fetch):
        r = await client.get("/stock_helper/api/v2/ai/sectors")

    assert r.status_code == 200
    body = r.json()
    assert body["sectors"] == []
    assert body["best_sector"] == "—"
    assert body["worst_sector"] == "—"


@pytest.mark.asyncio
async def test_sectors_market_rotation_reflects_breadth(client: AsyncClient):
    """3 bullish + 0 bearish should report risk-on rotation."""
    async def fake_fetch(self, code):
        # Every sector queried gets bullish data
        return [
            {"symbol": f"X{code}", "change_percent": 2.0},
            {"symbol": f"Y{code}", "change_percent": 1.5},
        ]

    with patch.object(InsightsService, "_fetch_industry_companies", fake_fetch):
        r = await client.get("/stock_helper/api/v2/ai/sectors")

    assert r.status_code == 200
    body = r.json()
    assert "Risk-on" in body["market_rotation"]


# ---------------------------------------------------------------------------
# _fetch_top_movers / _fetch_industry_companies — verify the upstream
# request shape without going to the network
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_top_movers_returns_empty_lists_on_upstream_error():
    """When stock-data is unreachable, _fetch_top_movers returns empty
    lists rather than raising. Important for /trending degrade path."""
    service = InsightsService()

    class BoomClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, *args, **kwargs):
            raise RuntimeError("connection refused")

    with patch("app.services.insights_service.httpx.AsyncClient", BoomClient):
        result = await service._fetch_top_movers()

    assert result == {"gainers": [], "losers": [], "actives": []}
