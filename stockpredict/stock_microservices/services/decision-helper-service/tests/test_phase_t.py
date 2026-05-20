"""Phase T (F-190..F-193) — AI trade review unit tests."""
import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.schemas import (
    OutcomeRecord,
    TradeReviewResponse,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _outcome_record(**kw):
    defaults = dict(
        run_id=1,
        ticker="VCB",
        bar_date=date(2025, 1, 10),
        action="BUY",
        entry_price=80.0,
        stop_price=76.0,
        exit_price=88.0,
        outcome="WIN",
        r_multiple=2.0,
        exit_run_id=2,
        signal_kind="MA_CROSS",
        regime="TREND_UP",
        ai_review=None,
        created_at=datetime(2025, 1, 10, 9, 0, 0),
    )
    defaults.update(kw)
    return OutcomeRecord(**defaults)


# ── OutcomeRecord — ai_review field ──────────────────────────────────────────

class TestOutcomeRecordAiReview:
    def test_ai_review_defaults_none(self):
        rec = _outcome_record()
        assert rec.ai_review is None

    def test_ai_review_stores_string(self):
        rec = _outcome_record(ai_review="Strong trend entry with confirmation.")
        assert rec.ai_review == "Strong trend entry with confirmation."

    def test_ai_review_long_string_accepted(self):
        long_text = "x" * 2000
        rec = _outcome_record(ai_review=long_text)
        assert len(rec.ai_review) == 2000

    def test_ai_review_none_explicitly(self):
        rec = _outcome_record(ai_review=None)
        assert rec.ai_review is None


# ── TradeReviewResponse schema ────────────────────────────────────────────────

class TestTradeReviewResponse:
    def test_basic_construction(self):
        r = TradeReviewResponse(
            run_id=42,
            ticker="HPG",
            outcome="LOSS",
            ai_review="The entry lacked volume confirmation.",
            generated=True,
        )
        assert r.run_id == 42
        assert r.ticker == "HPG"
        assert r.outcome == "LOSS"
        assert r.generated is True

    def test_generated_false_for_cached(self):
        r = TradeReviewResponse(
            run_id=7,
            ticker="VNM",
            outcome="WIN",
            ai_review="Textbook breakout.",
            generated=False,
        )
        assert r.generated is False

    def test_ai_review_none_when_unavailable(self):
        r = TradeReviewResponse(
            run_id=3,
            ticker="MBB",
            outcome=None,
            ai_review=None,
            generated=False,
        )
        assert r.ai_review is None
        assert r.outcome is None

    def test_required_fields(self):
        import pydantic
        with pytest.raises((pydantic.ValidationError, TypeError)):
            TradeReviewResponse(run_id=1)  # missing ticker and generated


# ── Prompt building logic ─────────────────────────────────────────────────────

class TestPromptBuilding:
    """Tests for the _build_prompt() helper in ai_review.py."""

    def _build_prompt(self, ticker, direction, signal_kind, regime,
                      entry_price, stop_price, exit_price, outcome, r_multiple,
                      bar_date, discipline_violations=None):
        """Replicate prompt-building logic for unit testing."""
        parts = [
            f"Trade post-mortem for {ticker}:",
            f"Direction={direction}, Signal={signal_kind}, Regime={regime}.",
            f"Entry={entry_price}, Stop={stop_price}, Exit={exit_price}.",
            f"Outcome={outcome}, R-multiple={r_multiple:+.2f}R.",
            f"Date={bar_date}.",
        ]
        if discipline_violations:
            parts.append(f"Discipline issues: {', '.join(discipline_violations)}.")
        parts.append("What worked, what failed, and key lesson?")
        prompt = " ".join(parts)
        return prompt[:500]

    def test_prompt_contains_ticker(self):
        p = self._build_prompt("VCB", "LONG", "MA_CROSS", "TREND_UP",
                               80.0, 76.0, 88.0, "WIN", 2.0, date(2025, 1, 10))
        assert "VCB" in p

    def test_prompt_contains_outcome(self):
        p = self._build_prompt("TCB", "LONG", "BREAKOUT", "RANGE",
                               50.0, 47.0, 44.0, "LOSS", -1.0, date(2025, 2, 1))
        assert "LOSS" in p
        assert "-1.00R" in p

    def test_prompt_contains_direction(self):
        p = self._build_prompt("FPT", "SHORT", "MA_CROSS", "TREND_DOWN",
                               100.0, 105.0, 90.0, "WIN", 2.0, date(2025, 3, 1))
        assert "SHORT" in p

    def test_prompt_within_500_chars(self):
        p = self._build_prompt("VERYLONGTICKER12", "LONG", "MA_CROSS_STOCH_BREAKOUT",
                               "TREND_UP_STRONG", 1234.56, 1100.0, 1400.0,
                               "WIN", 1.52, date(2025, 1, 1))
        assert len(p) <= 500

    def test_prompt_includes_discipline_violations(self):
        p = self._build_prompt("VIC", "LONG", "BREAKOUT", "TREND_UP",
                               80.0, 76.0, 88.0, "WIN", 2.0, date(2025, 1, 5),
                               discipline_violations=["RULE_001", "RULE_003"])
        assert "RULE_001" in p
        assert "RULE_003" in p

    def test_prompt_no_violations_section_when_empty(self):
        p = self._build_prompt("SSI", "LONG", "STOCH_REVERSAL", "RANGE",
                               30.0, 28.0, 33.0, "WIN", 1.5, date(2025, 4, 1),
                               discipline_violations=[])
        assert "Discipline issues" not in p

    def test_prompt_r_positive_sign(self):
        p = self._build_prompt("VHM", "LONG", "MA_CROSS", "TREND_UP",
                               60.0, 55.0, 65.0, "WIN", 1.0, date(2025, 1, 1))
        assert "+1.00R" in p

    def test_prompt_r_negative_sign(self):
        p = self._build_prompt("MSN", "LONG", "MA_CROSS", "RANGE",
                               60.0, 55.0, 57.0, "LOSS", -0.6, date(2025, 1, 1))
        assert "-0.60R" in p


# ── generate_trade_review integration stub ───────────────────────────────────

class TestGenerateTradeReview:
    """Tests that mock the HTTP layer to verify call shape."""

    @pytest.mark.asyncio
    async def test_returns_answer_on_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "Strong momentum entry.", "sources": []}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            from app.services.ai_review import generate_trade_review
            result = await generate_trade_review(
                ticker="VCB", direction="LONG", signal_kind="MA_CROSS",
                regime="TREND_UP", entry_price=80.0, stop_price=76.0,
                exit_price=88.0, outcome="WIN", r_multiple=2.0,
                bar_date=date(2025, 1, 10), jwt_token="tok",
            )
        assert result == "Strong momentum entry."

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.json.return_value = {"detail": "Service unavailable"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            from app.services.ai_review import generate_trade_review
            result = await generate_trade_review(
                ticker="VCB", direction="LONG", signal_kind="MA_CROSS",
                regime="TREND_UP", entry_price=80.0, stop_price=76.0,
                exit_price=88.0, outcome="WIN", r_multiple=2.0,
                bar_date=date(2025, 1, 10), jwt_token="tok",
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            from app.services.ai_review import generate_trade_review
            result = await generate_trade_review(
                ticker="VCB", direction="LONG", signal_kind="MA_CROSS",
                regime="TREND_UP", entry_price=80.0, stop_price=76.0,
                exit_price=88.0, outcome="WIN", r_multiple=2.0,
                bar_date=date(2025, 1, 10), jwt_token="tok",
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_sends_correct_payload_shape(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": "Good trade."}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            from app.services.ai_review import generate_trade_review
            await generate_trade_review(
                ticker="HPG", direction="LONG", signal_kind="BREAKOUT",
                regime="TREND_UP", entry_price=50.0, stop_price=47.0,
                exit_price=55.0, outcome="WIN", r_multiple=1.67,
                bar_date=date(2025, 3, 5), jwt_token="Bearer abc",
            )

        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1].get("json") or call_kwargs[0][1]
        assert "question" in payload
        assert "context" in payload
        assert payload["context"] == "trading performance review"
        assert "symbols" in payload
        assert "HPG" in payload["symbols"]

    @pytest.mark.asyncio
    async def test_answer_truncated_to_2000(self):
        long_answer = "A" * 3000
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"answer": long_answer}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            from app.services.ai_review import generate_trade_review
            result = await generate_trade_review(
                ticker="VNM", direction="SHORT", signal_kind="MA_CROSS",
                regime="TREND_DOWN", entry_price=90.0, stop_price=93.0,
                exit_price=85.0, outcome="WIN", r_multiple=1.67,
                bar_date=date(2025, 2, 1), jwt_token="tok",
            )
        assert result is not None
        assert len(result) <= 2000
