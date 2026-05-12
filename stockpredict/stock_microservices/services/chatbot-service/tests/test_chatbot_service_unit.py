"""Unit tests for ChatbotService — pure functions, Redis session
round-trips, fetch helpers, generate_response branches, chat()
orchestration, history, clear_session, and JWT dependencies.

Redis + httpx are mocked at the module level; no real services are
contacted.
"""
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user, get_current_user_optional
from app.config import get_settings
from app.models.schemas import (
    ConversationHistory,
    DetectedIntent,
    IntentType,
    MessageRole,
)
from app.services import chatbot_service as svc_mod
from app.services.chatbot_service import ChatbotService


settings = get_settings()


def _make_service(*, with_redis: bool = False, redis_client=None) -> ChatbotService:
    """Build a ChatbotService without opening a real Redis connection."""
    with patch.object(ChatbotService, "_init_redis", lambda self: None):
        s = ChatbotService()
    if with_redis:
        s.redis_client = redis_client or AsyncMock()
    return s


# ---------------------------------------------------------------------------
# _init_redis — swallow connection failure
# ---------------------------------------------------------------------------

def test_init_redis_swallows_exception(monkeypatch):
    """If redis.Redis() raises during construction, the service still
    initializes — just without a usable client."""
    class Boom:
        @staticmethod
        def Redis(**_kw):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(svc_mod, "redis", Boom())
    s = ChatbotService()
    assert s.redis_client is None


# ---------------------------------------------------------------------------
# _get_session / _save_session — Redis JSON round-trip
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_session_returns_none_without_redis():
    s = _make_service()
    assert await s._get_session("sid") is None


@pytest.mark.asyncio
async def test_get_session_returns_parsed_dict_when_redis_has_value():
    redis_client = AsyncMock()
    redis_client.get = AsyncMock(return_value=json.dumps({"messages": [], "user_id": 7}))
    s = _make_service(with_redis=True, redis_client=redis_client)

    out = await s._get_session("sid")
    assert out == {"messages": [], "user_id": 7}
    redis_client.get.assert_awaited_once_with("chat:sid")


@pytest.mark.asyncio
async def test_get_session_returns_none_when_no_value():
    redis_client = AsyncMock()
    redis_client.get = AsyncMock(return_value=None)
    s = _make_service(with_redis=True, redis_client=redis_client)
    assert await s._get_session("sid") is None


@pytest.mark.asyncio
async def test_get_session_swallows_redis_errors():
    redis_client = AsyncMock()
    redis_client.get = AsyncMock(side_effect=RuntimeError("redis down"))
    s = _make_service(with_redis=True, redis_client=redis_client)
    assert await s._get_session("sid") is None


@pytest.mark.asyncio
async def test_save_session_swallows_redis_errors():
    redis_client = AsyncMock()
    redis_client.set = AsyncMock(side_effect=RuntimeError("redis down"))
    s = _make_service(with_redis=True, redis_client=redis_client)
    # Must not raise.
    await s._save_session("sid", {"messages": []})


@pytest.mark.asyncio
async def test_save_session_writes_with_ttl(monkeypatch):
    monkeypatch.setattr(svc_mod.settings, "SESSION_TIMEOUT_MINUTES", 30)
    redis_client = AsyncMock()
    s = _make_service(with_redis=True, redis_client=redis_client)
    await s._save_session("sid", {"a": 1})
    redis_client.set.assert_awaited_once()
    args, kwargs = redis_client.set.await_args
    assert args[0] == "chat:sid"
    # ttl = 30 minutes × 60 seconds.
    assert kwargs["ex"] == 1800


# ---------------------------------------------------------------------------
# _track_usage — Redis pipeline
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_track_usage_does_nothing_without_redis():
    s = _make_service()
    # Must not raise even though there's no redis_client.
    await s._track_usage(intent_name="stock_price", is_new_session=False, response_ms=50.0)


@pytest.mark.asyncio
async def test_track_usage_uses_pipeline_with_session_counter():
    """When is_new_session=True the pipeline includes session counters."""
    redis_client = MagicMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock()
    redis_client.pipeline.return_value = pipe
    s = _make_service(with_redis=True, redis_client=redis_client)

    await s._track_usage(intent_name="greeting", is_new_session=True, response_ms=12.3)

    # Pipeline used; the daily + total session counters got incremented.
    redis_client.pipeline.assert_called_once()
    session_incrs = [c for c in pipe.incr.call_args_list
                     if c.args and ":sessions" in c.args[0]]
    assert len(session_incrs) == 2
    pipe.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_track_usage_swallows_pipeline_failure():
    redis_client = MagicMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(side_effect=RuntimeError("pipeline down"))
    redis_client.pipeline.return_value = pipe
    s = _make_service(with_redis=True, redis_client=redis_client)
    # Must not raise even though execute fails.
    await s._track_usage(intent_name="x", is_new_session=False, response_ms=1.0)


# ---------------------------------------------------------------------------
# _detect_intent — rule-based intent detection
# ---------------------------------------------------------------------------

class TestDetectIntent:
    def _detect(self, message: str) -> DetectedIntent:
        return _make_service()._detect_intent(message)

    def test_extracts_uppercase_three_letter_symbols(self):
        out = self._detect("Cho tôi xem VNM và FPT")
        assert "VNM" in out.entities["symbols"]
        assert "FPT" in out.entities["symbols"]

    def test_price_keyword_classifies_as_stock_price(self):
        out = self._detect("Giá VNM bao nhiêu?")
        assert out.intent == IntentType.STOCK_PRICE

    def test_english_price_keyword_classifies_as_stock_price(self):
        out = self._detect("how much is FPT")
        assert out.intent == IntentType.STOCK_PRICE

    def test_analysis_keyword(self):
        assert self._detect("Phân tích VNM").intent == IntentType.STOCK_ANALYSIS
        assert self._detect("analyze the chart").intent == IntentType.STOCK_ANALYSIS

    def test_prediction_keyword(self):
        assert self._detect("dự đoán VNM").intent == IntentType.STOCK_PREDICTION
        assert self._detect("forecast FPT").intent == IntentType.STOCK_PREDICTION

    def test_comparison_keyword(self):
        assert self._detect("so sánh VNM vs FPT").intent == IntentType.STOCK_COMPARISON

    def test_market_keyword(self):
        assert self._detect("thị trường hôm nay").intent == IntentType.MARKET_OVERVIEW
        assert self._detect("VNINDEX summary").intent == IntentType.MARKET_OVERVIEW

    def test_portfolio_keyword(self):
        assert self._detect("danh mục của tôi").intent == IntentType.PORTFOLIO_QUERY

    def test_greeting(self):
        assert self._detect("Xin chào").intent == IntentType.GREETING
        assert self._detect("hello there").intent == IntentType.GREETING

    def test_fallback_to_stock_price_when_only_symbol(self):
        """A bare 3-letter symbol with no recognized keyword still gets
        the STOCK_PRICE intent (lower confidence)."""
        out = self._detect("VNM")
        assert out.intent == IntentType.STOCK_PRICE
        assert out.confidence == 0.7

    def test_fallback_to_general_question(self):
        """No recognized keyword + no 3-letter uppercase sequence → general."""
        # "trời đẹp quá" — no 3-letter ASCII run, no keyword.
        out = self._detect("trời đẹp quá")
        assert out.intent == IntentType.GENERAL_QUESTION


# ---------------------------------------------------------------------------
# _fetch_stock_data / _get_analysis / _get_prediction (httpx)
# ---------------------------------------------------------------------------

class _FakeHttpxClient:
    """async-with stub; .get() returns the prepared response."""
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        c = MagicMock()
        c.get = AsyncMock(return_value=self._response)
        return c

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_fetch_stock_data_returns_quote_block_on_200():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"price": 100.0, "change_percent": 1.5}

    s = _make_service()
    with patch("app.services.chatbot_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await s._fetch_stock_data("FPT")
    assert out["quote"]["price"] == 100.0


@pytest.mark.asyncio
async def test_fetch_stock_data_returns_empty_dict_on_non_200():
    resp = MagicMock()
    resp.status_code = 503
    s = _make_service()
    with patch("app.services.chatbot_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await s._fetch_stock_data("FPT")
    assert out == {}


@pytest.mark.asyncio
async def test_fetch_stock_data_swallows_exception():
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    s = _make_service()
    with patch("app.services.chatbot_service.httpx.AsyncClient", return_value=Boom()):
        out = await s._fetch_stock_data("FPT")
    assert out == {}


@pytest.mark.asyncio
async def test_get_analysis_returns_json_on_200():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"overall_signal": "BUY"}
    s = _make_service()
    with patch("app.services.chatbot_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await s._get_analysis("FPT")
    assert out == {"overall_signal": "BUY"}


@pytest.mark.asyncio
async def test_get_analysis_returns_none_on_non_200():
    resp = MagicMock()
    resp.status_code = 404
    s = _make_service()
    with patch("app.services.chatbot_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        assert await s._get_analysis("FPT") is None


@pytest.mark.asyncio
async def test_get_analysis_swallows_exception_to_none():
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    s = _make_service()
    with patch("app.services.chatbot_service.httpx.AsyncClient", return_value=Boom()):
        assert await s._get_analysis("FPT") is None


@pytest.mark.asyncio
async def test_get_prediction_returns_json_on_200():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"predictions": [{"predicted_price": 110.0}]}
    s = _make_service()
    with patch("app.services.chatbot_service.httpx.AsyncClient",
               return_value=_FakeHttpxClient(resp)):
        out = await s._get_prediction("FPT")
    assert out["predictions"][0]["predicted_price"] == 110.0


@pytest.mark.asyncio
async def test_get_prediction_returns_none_on_exception():
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    s = _make_service()
    with patch("app.services.chatbot_service.httpx.AsyncClient", return_value=Boom()):
        assert await s._get_prediction("FPT") is None


# ---------------------------------------------------------------------------
# _generate_response — branch coverage per intent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_response_greeting():
    s = _make_service()
    intent = DetectedIntent(intent=IntentType.GREETING, confidence=0.95, entities={})
    out = await s._generate_response(intent, "xin chào", {})
    assert "Xin chào" in out


@pytest.mark.asyncio
async def test_generate_response_stock_price_with_quote():
    s = _make_service()
    intent = DetectedIntent(
        intent=IntentType.STOCK_PRICE, confidence=0.9,
        entities={"symbols": ["FPT"]},
    )
    with patch.object(s, "_fetch_stock_data",
                      AsyncMock(return_value={"quote": {
                          "price": 100.0, "change_percent": 1.5, "volume": 1000,
                      }})):
        out = await s._generate_response(intent, "giá FPT", {})
    assert "FPT" in out and "100" in out


@pytest.mark.asyncio
async def test_generate_response_stock_price_no_quote_returns_not_found():
    s = _make_service()
    intent = DetectedIntent(
        intent=IntentType.STOCK_PRICE, confidence=0.9,
        entities={"symbols": ["FPT"]},
    )
    with patch.object(s, "_fetch_stock_data", AsyncMock(return_value={})):
        out = await s._generate_response(intent, "giá FPT", {})
    assert "Không tìm thấy" in out


@pytest.mark.asyncio
async def test_generate_response_stock_analysis_with_result():
    s = _make_service()
    intent = DetectedIntent(
        intent=IntentType.STOCK_ANALYSIS, confidence=0.85,
        entities={"symbols": ["FPT"]},
    )
    canned = {
        "overall_signal": "BUY",
        "indicators": [{"value": 65.0}],
        "trend": "Uptrend",
    }
    with patch.object(s, "_get_analysis", AsyncMock(return_value=canned)):
        out = await s._generate_response(intent, "phân tích FPT", {})
    assert "BUY" in out
    assert "Uptrend" in out


@pytest.mark.asyncio
async def test_generate_response_stock_analysis_no_result():
    s = _make_service()
    intent = DetectedIntent(
        intent=IntentType.STOCK_ANALYSIS, confidence=0.85,
        entities={"symbols": ["FPT"]},
    )
    with patch.object(s, "_get_analysis", AsyncMock(return_value=None)):
        out = await s._generate_response(intent, "phân tích FPT", {})
    assert "Đang phân tích" in out


@pytest.mark.asyncio
async def test_generate_response_stock_prediction_with_predictions():
    s = _make_service()
    intent = DetectedIntent(
        intent=IntentType.STOCK_PREDICTION, confidence=0.85,
        entities={"symbols": ["FPT"]},
    )
    canned = {
        "predictions": [
            {"date": "2026-05-13", "predicted_price": 110.0, "direction": "up"},
            {"date": "2026-05-14", "predicted_price": 112.0, "direction": "up"},
        ],
    }
    with patch.object(s, "_get_prediction", AsyncMock(return_value=canned)):
        out = await s._generate_response(intent, "dự đoán FPT", {})
    assert "Dự đoán" in out and "FPT" in out
    assert "2026-05-13" in out


@pytest.mark.asyncio
async def test_generate_response_prediction_pending_when_no_predictions():
    s = _make_service()
    intent = DetectedIntent(
        intent=IntentType.STOCK_PREDICTION, confidence=0.85,
        entities={"symbols": ["FPT"]},
    )
    with patch.object(s, "_get_prediction", AsyncMock(return_value=None)):
        out = await s._generate_response(intent, "dự đoán FPT", {})
    assert "Đang tạo dự đoán" in out


@pytest.mark.asyncio
async def test_generate_response_comparison_renders_each_symbol():
    s = _make_service()
    intent = DetectedIntent(
        intent=IntentType.STOCK_COMPARISON, confidence=0.85,
        entities={"symbols": ["FPT", "VNM"]},
    )
    quotes = {
        "FPT": {"quote": {"price": 100.0, "change_percent": 1.5}},
        "VNM": {"quote": {"price": 70.0, "change_percent": -0.5}},
    }
    async def fake_fetch(sym):
        return quotes.get(sym, {})

    with patch.object(s, "_fetch_stock_data", side_effect=fake_fetch):
        out = await s._generate_response(intent, "so sánh FPT vs VNM", {})
    assert "FPT" in out and "VNM" in out
    assert "So sánh" in out


@pytest.mark.asyncio
async def test_generate_response_market_overview_returns_canned_summary():
    s = _make_service()
    intent = DetectedIntent(intent=IntentType.MARKET_OVERVIEW, confidence=0.8, entities={})
    out = await s._generate_response(intent, "thị trường", {})
    assert "Thị trường" in out


@pytest.mark.asyncio
async def test_generate_response_general_with_symbols_prompts_for_more():
    s = _make_service()
    intent = DetectedIntent(
        intent=IntentType.GENERAL_QUESTION, confidence=0.5,
        entities={"symbols": ["FPT"]},
    )
    out = await s._generate_response(intent, "FPT?", {})
    assert "FPT" in out


@pytest.mark.asyncio
async def test_generate_response_general_no_symbols_returns_help_text():
    s = _make_service()
    intent = DetectedIntent(intent=IntentType.GENERAL_QUESTION, confidence=0.5, entities={})
    out = await s._generate_response(intent, "hôm nay?", {})
    assert "cổ phiếu" in out.lower() or "stock" in out.lower()


# ---------------------------------------------------------------------------
# _generate_suggestions
# ---------------------------------------------------------------------------

class TestGenerateSuggestions:
    def test_price_intent_with_symbol_offers_followups(self):
        s = _make_service()
        intent = DetectedIntent(
            intent=IntentType.STOCK_PRICE, confidence=0.9,
            entities={"symbols": ["FPT"]},
        )
        out = s._generate_suggestions(intent)
        assert any("FPT" in x for x in out)

    def test_greeting_suggestions_show_quick_links(self):
        s = _make_service()
        intent = DetectedIntent(intent=IntentType.GREETING, confidence=0.95, entities={})
        assert s._generate_suggestions(intent) == [
            "Giá VNM", "Phân tích FPT", "Thị trường hôm nay",
        ]

    def test_default_suggestions_when_nothing_matches(self):
        s = _make_service()
        intent = DetectedIntent(
            intent=IntentType.GENERAL_QUESTION, confidence=0.5, entities={},
        )
        out = s._generate_suggestions(intent)
        assert "Tra giá cổ phiếu" in out


# ---------------------------------------------------------------------------
# chat() — orchestration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_creates_new_session_when_none_provided():
    s = _make_service()
    # Stub the heavy helpers so chat() exercises only the orchestration.
    with patch.object(s, "_get_session", AsyncMock(return_value=None)), \
         patch.object(s, "_save_session", AsyncMock()), \
         patch.object(s, "_track_usage", AsyncMock()), \
         patch.object(s, "_generate_response", AsyncMock(return_value="hi")):
        resp = await s.chat("Xin chào", session_id=None, user_id=7)
    assert resp.session_id  # uuid was generated
    assert resp.message == "hi"
    assert resp.intent == IntentType.GREETING.value


@pytest.mark.asyncio
async def test_chat_reuses_existing_session_messages():
    s = _make_service()
    existing = {
        "messages": [{"role": "user", "content": "earlier", "timestamp": "2026-01-01T00:00:00"}],
        "context": {},
        "user_id": 7,
        "created_at": "2026-01-01T00:00:00",
    }
    save_mock = AsyncMock()
    with patch.object(s, "_get_session", AsyncMock(return_value=existing)), \
         patch.object(s, "_save_session", save_mock), \
         patch.object(s, "_track_usage", AsyncMock()), \
         patch.object(s, "_generate_response", AsyncMock(return_value="ok")):
        resp = await s.chat("phân tích VNM", session_id="sid", user_id=7)
    # 1 prior + user + assistant = 3 messages saved.
    saved = save_mock.await_args.args[1]
    assert len(saved["messages"]) == 3
    assert resp.intent == IntentType.STOCK_ANALYSIS.value


@pytest.mark.asyncio
async def test_chat_truncates_history_to_max_conversation_history(monkeypatch):
    """When the running session exceeds MAX × 2 messages, the prefix is
    trimmed so memory stays bounded."""
    monkeypatch.setattr(svc_mod.settings, "MAX_CONVERSATION_HISTORY", 2)
    s = _make_service()
    # 5 prior messages → 5+2 = 7 > 4 = max*2 → trimmed to 4.
    existing = {
        "messages": [
            {"role": "user", "content": f"m{i}", "timestamp": "2026-01-01"}
            for i in range(5)
        ],
        "context": {},
        "user_id": 7,
        "created_at": "2026-01-01",
    }
    save_mock = AsyncMock()
    with patch.object(s, "_get_session", AsyncMock(return_value=existing)), \
         patch.object(s, "_save_session", save_mock), \
         patch.object(s, "_track_usage", AsyncMock()), \
         patch.object(s, "_generate_response", AsyncMock(return_value="r")):
        await s.chat("hi", session_id="sid")
    saved = save_mock.await_args.args[1]
    assert len(saved["messages"]) == 4


# ---------------------------------------------------------------------------
# get_history / clear_session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_history_returns_none_when_no_session():
    s = _make_service()
    with patch.object(s, "_get_session", AsyncMock(return_value=None)):
        out = await s.get_history("sid")
    assert out is None


@pytest.mark.asyncio
async def test_get_history_parses_messages_into_history_object():
    s = _make_service()
    now = datetime.now().isoformat()
    existing = {
        "messages": [
            {"role": "user", "content": "q", "timestamp": now},
            {"role": "assistant", "content": "a", "timestamp": now},
        ],
        "created_at": now,
        "last_activity": now,
    }
    with patch.object(s, "_get_session", AsyncMock(return_value=existing)):
        history = await s.get_history("sid")
    assert isinstance(history, ConversationHistory)
    assert history.session_id == "sid"
    assert len(history.messages) == 2
    assert history.messages[0].role == MessageRole.USER


@pytest.mark.asyncio
async def test_clear_session_returns_false_without_redis():
    s = _make_service()
    assert await s.clear_session("sid") is False


@pytest.mark.asyncio
async def test_clear_session_returns_true_on_successful_delete():
    redis_client = AsyncMock()
    redis_client.delete = AsyncMock(return_value=1)
    s = _make_service(with_redis=True, redis_client=redis_client)
    assert await s.clear_session("sid") is True
    redis_client.delete.assert_awaited_once_with("chat:sid")


@pytest.mark.asyncio
async def test_clear_session_returns_false_when_redis_raises():
    redis_client = AsyncMock()
    redis_client.delete = AsyncMock(side_effect=RuntimeError("redis down"))
    s = _make_service(with_redis=True, redis_client=redis_client)
    assert await s.clear_session("sid") is False


# ---------------------------------------------------------------------------
# Dependencies — JWT helpers
# ---------------------------------------------------------------------------

def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _make_token(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_without_credentials():
    assert await get_current_user_optional(credentials=None) is None


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_on_invalid_token():
    assert await get_current_user_optional(credentials=_creds("not.a.jwt")) is None


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_user_on_valid_token():
    token = _make_token({"sub": "42", "email": "alice@example.com"})
    user = await get_current_user_optional(credentials=_creds(token))
    assert user == {"user_id": 42, "email": "alice@example.com"}


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds("not.a.jwt"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_sub_missing():
    """The dependency rejects a token whose `sub` claim is empty even if
    everything else is well-formed."""
    token = _make_token({"email": "x@y.com"})
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=_creds(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_returns_dict_on_valid_token():
    token = _make_token({"sub": "7", "email": "alice@example.com"})
    user = await get_current_user(credentials=_creds(token))
    assert user == {"user_id": 7, "email": "alice@example.com"}
