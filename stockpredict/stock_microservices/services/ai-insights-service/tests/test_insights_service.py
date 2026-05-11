"""Tests for app.services.insights_service.InsightsService.

Targets the pure functions, the cache wrappers, the LLM dispatcher
fallback chain, and the simple wrap-LLM-response methods (generate_insight,
compare_stocks, analyze_news, answer_question, get_market_overview).

The Anthropic SDK + OpenAI HTTP API + Redis are all mocked at module
level — no real network or daemon required.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.models.schemas import InsightType
from app.services import insights_service as svc_mod
from app.services.insights_service import InsightsService


# ---------------------------------------------------------------------------
# Constructors / Redis init
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_anthropic_module_attr():
    """The module exposes `AsyncAnthropic` as a top-level symbol used in
    _resolve_provider / _get_anthropic_client. Tests that flip it have to
    restore the original so we don't leak into other tests."""
    original = svc_mod.AsyncAnthropic
    yield
    svc_mod.AsyncAnthropic = original


def _make_service(*, with_redis: bool = False, redis_client=None) -> InsightsService:
    """Build a service without actually opening a Redis connection.
    `_init_redis` swallows Exceptions, so the default path is "no redis"."""
    with patch.object(InsightsService, "_init_redis", lambda self: None):
        s = InsightsService()
    if with_redis:
        s.redis_client = redis_client or AsyncMock()
    return s


def test_init_redis_swallows_connection_error(monkeypatch):
    """If redis.Redis() blows up during construction, the service still
    initializes — just without a usable client."""
    class Boom:
        @staticmethod
        def Redis(**_kw):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(svc_mod, "redis", Boom())
    s = InsightsService()
    assert s.redis_client is None


# ---------------------------------------------------------------------------
# Provider resolution + Anthropic client lazy init
# ---------------------------------------------------------------------------

def test_resolve_provider_pinned_value_passes_through(monkeypatch):
    s = _make_service()
    monkeypatch.setattr(svc_mod.settings, "LLM_PROVIDER", "openai")
    assert s._resolve_provider() == "openai"


def test_resolve_provider_auto_with_anthropic_key(monkeypatch):
    monkeypatch.setattr(svc_mod.settings, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(svc_mod.settings, "ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setattr(svc_mod, "AsyncAnthropic", object)
    assert _make_service()._resolve_provider() == "anthropic"


def test_resolve_provider_auto_falls_back_to_openai_when_no_anthropic(monkeypatch):
    monkeypatch.setattr(svc_mod.settings, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(svc_mod.settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(svc_mod.settings, "OPENAI_API_KEY", "sk-openai")
    monkeypatch.setattr(svc_mod, "AsyncAnthropic", None)
    assert _make_service()._resolve_provider() == "openai"


def test_resolve_provider_falls_back_to_template_when_no_keys(monkeypatch):
    monkeypatch.setattr(svc_mod.settings, "LLM_PROVIDER", "auto")
    monkeypatch.setattr(svc_mod.settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(svc_mod.settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(svc_mod, "AsyncAnthropic", None)
    assert _make_service()._resolve_provider() == "template"


def test_get_anthropic_client_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.setattr(svc_mod.settings, "ANTHROPIC_API_KEY", "")
    s = _make_service()
    assert s._get_anthropic_client() is None


def test_get_anthropic_client_caches_after_first_build(monkeypatch):
    """Lazy construction is cached; second call returns the same instance."""
    monkeypatch.setattr(svc_mod.settings, "ANTHROPIC_API_KEY", "sk-ant")

    class FakeClient:
        def __init__(self, **_kw):
            self.id = id(self)

    monkeypatch.setattr(svc_mod, "AsyncAnthropic", FakeClient)
    s = _make_service()
    first = s._get_anthropic_client()
    second = s._get_anthropic_client()
    assert first is second is not None


# ---------------------------------------------------------------------------
# Redis cache wrappers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_cached_returns_none_without_client():
    s = _make_service()
    assert await s._get_cached("k") is None


@pytest.mark.asyncio
async def test_get_cached_swallows_redis_errors():
    """A flaky Redis must not propagate to callers."""
    redis_client = AsyncMock()
    redis_client.get = AsyncMock(side_effect=RuntimeError("timeout"))
    s = _make_service(with_redis=True, redis_client=redis_client)
    assert await s._get_cached("k") is None


@pytest.mark.asyncio
async def test_get_cached_returns_value_when_redis_has_it():
    redis_client = AsyncMock()
    redis_client.get = AsyncMock(return_value="hello")
    s = _make_service(with_redis=True, redis_client=redis_client)
    assert await s._get_cached("k") == "hello"


@pytest.mark.asyncio
async def test_set_cached_swallows_redis_errors():
    redis_client = AsyncMock()
    redis_client.set = AsyncMock(side_effect=RuntimeError("timeout"))
    s = _make_service(with_redis=True, redis_client=redis_client)
    await s._set_cached("k", "v", ttl=60)  # must not raise


@pytest.mark.asyncio
async def test_set_cached_uses_default_ttl_when_unspecified(monkeypatch):
    monkeypatch.setattr(svc_mod.settings, "CACHE_TTL", 3600)
    redis_client = AsyncMock()
    s = _make_service(with_redis=True, redis_client=redis_client)
    await s._set_cached("k", "v")
    redis_client.set.assert_awaited_once_with("k", "v", ex=3600)


# ---------------------------------------------------------------------------
# Pure-function helpers
# ---------------------------------------------------------------------------

class TestExtractKeyPoints:
    def test_extracts_dash_bullets(self):
        out = _make_service()._extract_key_points(
            "Summary:\n- alpha\n- beta\n- gamma"
        )
        assert out == ["alpha", "beta", "gamma"]

    def test_extracts_unicode_bullet_and_asterisk(self):
        out = _make_service()._extract_key_points(
            "• unicode bullet\n* asterisk bullet\n- dash"
        )
        assert out == ["unicode bullet", "asterisk bullet", "dash"]

    def test_caps_at_five_points(self):
        text = "\n".join(f"- p{i}" for i in range(8))
        out = _make_service()._extract_key_points(text)
        assert len(out) == 5

    def test_fallback_when_no_bullets(self):
        out = _make_service()._extract_key_points("Plain paragraph text.")
        assert "Analysis completed" in out


class TestAnalyzeSentiment:
    def test_bullish_when_bullish_words_dominate(self):
        s = _make_service()
        # 'bullish', 'buy', 'positive', 'growth' -> bullish_count >> bearish
        text = "The outlook is bullish; we recommend a buy with positive growth."
        assert s._analyze_sentiment(text) == "bullish"

    def test_bearish_when_bearish_words_dominate(self):
        s = _make_service()
        text = "Bearish signal: sell. Negative sentiment, expecting decline and downside."
        assert s._analyze_sentiment(text) == "bearish"

    def test_neutral_when_neither_dominates(self):
        s = _make_service()
        # Even mix: one bullish, one bearish word.
        assert s._analyze_sentiment("positive but with some weakness") == "neutral"


class TestBuildInsightPrompt:
    def test_includes_quote_and_technical_blocks(self):
        s = _make_service()
        prompt = s._build_insight_prompt(
            "FPT",
            InsightType.ANALYSIS,
            data={
                "quote": {"price": 100, "change_percent": 1.5},
                "technical": {"overall_signal": "buy", "indicators": [{"value": 55}]},
                "prediction": {"predictions": [{"direction": "up"}]},
            },
            context="earnings tomorrow",
        )
        assert "FPT" in prompt
        assert "100" in prompt
        assert "buy" in prompt
        assert "up" in prompt
        assert "earnings tomorrow" in prompt
        # InsightType.ANALYSIS path adds the analysis instruction.
        assert "comprehensive analysis" in prompt

    def test_summary_and_recommendation_branches_produce_distinct_text(self):
        s = _make_service()
        p_summary = s._build_insight_prompt("FPT", InsightType.SUMMARY, {}, None)
        p_reco = s._build_insight_prompt("FPT", InsightType.RECOMMENDATION, {}, None)
        assert "summary" in p_summary.lower()
        assert "recommendation" in p_reco.lower()
        assert p_summary != p_reco


def test_generate_template_response_contains_known_sections():
    s = _make_service()
    out = s._generate_template_response("any prompt")
    assert "Analysis Summary" in out
    assert "Key Points" in out
    assert "Recommendation" in out


def test_get_available_indicators_lists_all_four_categories():
    s = _make_service()
    out = s.get_available_indicators()
    cats = {c.category for c in out.categories}
    assert cats == {"trend", "momentum", "volatility", "volume"}
    # 4 + 3 + 2 + 2 = 11
    assert out.total_indicators == 11


# ---------------------------------------------------------------------------
# _calculate_indicators — pandas indicator math
# ---------------------------------------------------------------------------

def _ohlcv_df(rows: int = 60) -> pd.DataFrame:
    """Deterministic OHLCV frame large enough to exercise rolling windows."""
    rng = np.random.default_rng(123)
    close = 100 + np.cumsum(rng.normal(0, 1, size=rows))
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "open": close + rng.normal(0, 0.2, size=rows),
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": rng.integers(1000, 5000, size=rows),
        }
    )


def test_calculate_indicators_trend_path_produces_macd_sma_wma():
    s = _make_service()
    df = s._calculate_indicators(_ohlcv_df(), {"trend": "MACD"})
    for col in ("ema_12", "ema_26", "macd", "macd_signal", "macd_histogram", "sma_20", "sma_50", "wma_20"):
        assert col in df.columns


def test_calculate_indicators_momentum_path_produces_rsi_stoch_mfi():
    s = _make_service()
    df = s._calculate_indicators(_ohlcv_df(), {"momentum": "RSI"})
    for col in ("rsi", "stoch_k", "stoch_d", "mfi"):
        assert col in df.columns


def test_calculate_indicators_volatility_path_produces_bb_atr():
    s = _make_service()
    df = s._calculate_indicators(_ohlcv_df(), {"volatility": "BB"})
    for col in ("bb_middle", "bb_upper", "bb_lower", "atr"):
        assert col in df.columns


def test_calculate_indicators_volume_path_produces_obv_vwap():
    s = _make_service()
    df = s._calculate_indicators(_ohlcv_df(), {"volume": "OBV"})
    assert "obv" in df.columns
    assert "vwap" in df.columns
    # OBV is monotonic in absolute terms — non-zero swings expected.
    assert df["obv"].abs().sum() > 0


def test_calculate_indicators_skips_categories_not_requested():
    s = _make_service()
    df = s._calculate_indicators(_ohlcv_df(), {})  # no category selected
    # None of the indicator columns should be added.
    assert "macd" not in df.columns
    assert "rsi" not in df.columns
    assert "bb_middle" not in df.columns


# ---------------------------------------------------------------------------
# LLM dispatcher fallback chain
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_llm_returns_anthropic_text_when_available():
    s = _make_service()
    with patch.object(s, "_resolve_provider", return_value="auto"), \
         patch.object(s, "_call_anthropic", AsyncMock(return_value="claude said hi")):
        out = await s._call_llm("hello")
    assert out == "claude said hi"


@pytest.mark.asyncio
async def test_call_llm_falls_back_to_openai_when_anthropic_returns_none(monkeypatch):
    monkeypatch.setattr(svc_mod.settings, "OPENAI_API_KEY", "sk-openai")
    s = _make_service()
    with patch.object(s, "_resolve_provider", return_value="auto"), \
         patch.object(s, "_call_anthropic", AsyncMock(return_value=None)), \
         patch.object(s, "_call_openai", AsyncMock(return_value="gpt fallback")):
        out = await s._call_llm("hello")
    assert out == "gpt fallback"


@pytest.mark.asyncio
async def test_call_llm_falls_back_to_template_when_both_providers_fail(monkeypatch):
    monkeypatch.setattr(svc_mod.settings, "OPENAI_API_KEY", "sk-openai")
    s = _make_service()
    with patch.object(s, "_resolve_provider", return_value="auto"), \
         patch.object(s, "_call_anthropic", AsyncMock(return_value=None)), \
         patch.object(s, "_call_openai", AsyncMock(return_value=None)):
        out = await s._call_llm("hello")
    assert "Analysis Summary" in out  # template content


# ---------------------------------------------------------------------------
# _call_anthropic / _call_openai
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_anthropic_returns_none_without_client():
    s = _make_service()
    with patch.object(s, "_get_anthropic_client", return_value=None):
        out = await s._call_anthropic("p", "sys")
    assert out is None


@pytest.mark.asyncio
async def test_call_anthropic_extracts_text_block():
    """Anthropic returns a `content` list of blocks; we pick the first
    text-typed block and return its `.text` value."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "claude response"
    message = MagicMock(content=[text_block])

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=message)

    s = _make_service()
    with patch.object(s, "_get_anthropic_client", return_value=fake_client):
        out = await s._call_anthropic("p", "sys")
    assert out == "claude response"


@pytest.mark.asyncio
async def test_call_anthropic_returns_none_on_exception():
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(side_effect=RuntimeError("rate limit"))
    s = _make_service()
    with patch.object(s, "_get_anthropic_client", return_value=fake_client):
        out = await s._call_anthropic("p", "sys")
    assert out is None


class _FakeHttpxClient:
    """async-with stub. Each call to .get/.post returns the prepared response."""
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=self._response)
        client.post = AsyncMock(return_value=self._response)
        return client

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_call_openai_returns_content_on_200():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"choices": [{"message": {"content": "gpt content"}}]}
    s = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=_FakeHttpxClient(resp)):
        out = await s._call_openai("p", "sys")
    assert out == "gpt content"


@pytest.mark.asyncio
async def test_call_openai_returns_none_on_non_200():
    resp = MagicMock()
    resp.status_code = 503
    resp.text = "service down"
    s = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=_FakeHttpxClient(resp)):
        out = await s._call_openai("p", "sys")
    assert out is None


@pytest.mark.asyncio
async def test_call_openai_returns_none_on_exception():
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    s = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=Boom()):
        out = await s._call_openai("p", "sys")
    assert out is None


# ---------------------------------------------------------------------------
# _fetch_stock_data / _fetch_historical_prices
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_stock_data_collects_from_three_services():
    """Returns a dict with quote/technical/prediction blocks when all
    three upstreams respond 200."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"value": 1}
    s = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=_FakeHttpxClient(resp)):
        data = await s._fetch_stock_data("FPT")
    assert data["symbol"] == "FPT"
    # Each block populated from the same canned response.
    assert "quote" in data
    assert "technical" in data
    assert "prediction" in data


@pytest.mark.asyncio
async def test_fetch_stock_data_returns_partial_on_exception():
    """Network failure mid-flight → return what we have so far."""
    class FailOnSecondGet:
        def __init__(self):
            self.calls = 0

        async def get(self, *_a, **_kw):
            self.calls += 1
            if self.calls == 1:
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {"price": 100}
                return resp
            raise ConnectionError("down")

    class FailCtx:
        async def __aenter__(self):
            return FailOnSecondGet()

        async def __aexit__(self, *_):
            return False

    s = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=FailCtx()):
        data = await s._fetch_stock_data("FPT")
    assert data["symbol"] == "FPT"
    assert "quote" in data
    # technical/prediction calls never completed.
    assert "technical" not in data


@pytest.mark.asyncio
async def test_fetch_historical_prices_returns_sorted_dataframe():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [
            {"date": "2026-05-02", "close": 110},
            {"date": "2026-05-01", "close": 105},
        ]
    }
    s = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=_FakeHttpxClient(resp)):
        df = await s._fetch_historical_prices("FPT", "2026-05-01", "2026-05-02")
    assert df is not None
    assert list(df["close"]) == [105, 110]  # sorted ascending


@pytest.mark.asyncio
async def test_fetch_historical_prices_returns_none_on_non_200():
    resp = MagicMock()
    resp.status_code = 404
    s = _make_service()
    with patch("app.services.insights_service.httpx.AsyncClient", return_value=_FakeHttpxClient(resp)):
        assert await s._fetch_historical_prices("X", "a", "b") is None


# ---------------------------------------------------------------------------
# High-level wrappers: generate_insight / compare_stocks / analyze_news /
# answer_question / get_market_overview
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_insight_uses_cached_value_when_present():
    s = _make_service()
    canned = {
        "symbol": "FPT",
        "insight_type": "analysis",
        "content": "cached content with - alpha\n- beta",
        "summary": "cached content",
        "key_points": ["alpha", "beta"],
        "sentiment": "neutral",
        "confidence": 0.75,
        "sources": ["technical_analysis"],
        "generated_at": datetime.now().isoformat(),
    }
    import json
    with patch.object(s, "_get_cached", AsyncMock(return_value=json.dumps(canned))), \
         patch.object(s, "_fetch_stock_data", AsyncMock()) as fetch_mock:
        out = await s.generate_insight("FPT", InsightType.ANALYSIS)
    # Cache hit short-circuited the work — _fetch_stock_data never called.
    fetch_mock.assert_not_awaited()
    assert out.content == canned["content"]


@pytest.mark.asyncio
async def test_generate_insight_fresh_path_calls_llm_and_caches():
    s = _make_service()
    with patch.object(s, "_get_cached", AsyncMock(return_value=None)), \
         patch.object(s, "_fetch_stock_data", AsyncMock(return_value={"symbol": "FPT"})), \
         patch.object(s, "_call_llm", AsyncMock(return_value="Bullish positive growth\n- alpha\n- beta")), \
         patch.object(s, "_set_cached", AsyncMock()) as set_mock:
        out = await s.generate_insight("FPT", InsightType.ANALYSIS)
    assert out.symbol == "FPT"
    assert out.sentiment == "bullish"
    assert out.key_points == ["alpha", "beta"]
    set_mock.assert_awaited()


@pytest.mark.asyncio
async def test_compare_stocks_returns_ranked_response():
    s = _make_service()
    with patch.object(s, "_fetch_stock_data", AsyncMock(return_value={"symbol": "FPT", "quote": {"price": 100}})), \
         patch.object(s, "_call_llm", AsyncMock(return_value="FPT outperforms")):
        out = await s.compare_stocks(["FPT", "VNM"], focus="growth")
    assert out.symbols == ["FPT", "VNM"]
    assert out.rankings == {"FPT": 1, "VNM": 2}
    assert out.recommendation == "FPT"


@pytest.mark.asyncio
async def test_analyze_news_returns_sentiment_and_key_events():
    s = _make_service()
    with patch.object(s, "_call_llm", AsyncMock(return_value="Bullish news, strong growth")):
        out = await s.analyze_news(
            "FPT",
            [
                {"title": "FPT signs deal", "content": "Large partnership"},
                {"title": "Q1 earnings beat", "content": "Strong revenue"},
            ],
        )
    assert out.symbol == "FPT"
    assert out.overall_sentiment == "bullish"
    assert out.sentiment_score == 0.8
    assert "FPT signs deal" in out.key_events


@pytest.mark.asyncio
async def test_analyze_news_neutral_when_no_sentiment_signal():
    s = _make_service()
    with patch.object(s, "_call_llm", AsyncMock(return_value="Plain summary text without signal words")):
        out = await s.analyze_news("FPT", [{"title": "Routine update", "content": ""}])
    assert out.overall_sentiment == "neutral"
    assert out.sentiment_score == 0.5


@pytest.mark.asyncio
async def test_answer_question_without_symbols_skips_fetch():
    s = _make_service()
    fetch_mock = AsyncMock()
    with patch.object(s, "_fetch_stock_data", fetch_mock), \
         patch.object(s, "_call_llm", AsyncMock(return_value="answer text")):
        out = await s.answer_question("What is RSI?")
    fetch_mock.assert_not_awaited()
    assert out.question == "What is RSI?"
    assert out.answer == "answer text"
    assert out.relevant_data == {}


@pytest.mark.asyncio
async def test_answer_question_with_symbols_caps_fetch_at_three():
    s = _make_service()
    with patch.object(s, "_fetch_stock_data", AsyncMock(return_value={"symbol": "X"})) as fetch_mock, \
         patch.object(s, "_call_llm", AsyncMock(return_value="answer")):
        await s.answer_question("compare", symbols=["A", "B", "C", "D", "E"])
    # The method caps at symbols[:3].
    assert fetch_mock.await_count == 3


@pytest.mark.asyncio
async def test_get_market_overview_returns_summary():
    s = _make_service()
    with patch.object(s, "_call_llm", AsyncMock(return_value="Market summary today")):
        out = await s.get_market_overview(focus="banks")
    assert out.summary == "Market summary today"
    assert out.outlook == "neutral"
