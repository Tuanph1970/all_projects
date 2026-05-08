"""Coverage for the Redis-backed usage tracking shipped this week
(Backlog #4). Validates that _track_usage writes the right counter
shape and that get_usage_stats aggregates the right keys per period.

Tests don't require a real Redis — we patch the client with an
AsyncMock and inspect the pipeline calls directly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.chatbot_service import ChatbotService


def _service_with_mock_redis():
    """Build a ChatbotService whose redis_client is a fresh AsyncMock."""
    service = ChatbotService()
    service.redis_client = AsyncMock()
    return service


def _mock_pipeline(service):
    """Replace `redis_client.pipeline()` with a controllable AsyncMock so
    tests can assert on individual pipeline operations.
    """
    pipe = AsyncMock()
    service.redis_client.pipeline = MagicMock(return_value=pipe)
    return pipe


# ---------------------------------------------------------------------------
# _track_usage — writes daily + all-time counters in a single pipeline
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_track_usage_increments_messages_and_intents():
    service = _service_with_mock_redis()
    pipe = _mock_pipeline(service)

    await service._track_usage(
        intent_name="stock_price",
        is_new_session=False,
        response_ms=120.0,
    )

    # Pipeline should have been used + executed exactly once.
    service.redis_client.pipeline.assert_called_once()
    pipe.execute.assert_awaited_once()

    # Verify message + intent counters got hit (daily + total).
    incr_calls = [c.args[0] for c in pipe.incr.call_args_list]
    assert any(":messages" in k and "total" in k for k in incr_calls)
    assert any(":messages" in k and "total" not in k for k in incr_calls)

    hincr_calls = [(c.args[0], c.args[1], c.args[2]) for c in pipe.hincrby.call_args_list]
    intent_keys = {(k, f, n) for (k, f, n) in hincr_calls if f == "stock_price"}
    # Two entries — one daily intents hash, one total intents hash.
    assert len(intent_keys) == 2


@pytest.mark.asyncio
async def test_track_usage_increments_session_counter_only_on_new_session():
    """Session counter must NOT bump on existing-session turns."""
    service = _service_with_mock_redis()
    pipe = _mock_pipeline(service)

    await service._track_usage(
        intent_name="general_question", is_new_session=False, response_ms=80.0,
    )

    incr_calls = [c.args[0] for c in pipe.incr.call_args_list]
    session_increments = [k for k in incr_calls if k.endswith(":sessions")]
    assert session_increments == [], (
        "Session counter should not increment on existing-session turns; "
        f"saw: {session_increments}"
    )


@pytest.mark.asyncio
async def test_track_usage_increments_session_counter_when_new():
    service = _service_with_mock_redis()
    pipe = _mock_pipeline(service)

    await service._track_usage(
        intent_name="greeting", is_new_session=True, response_ms=50.0,
    )

    incr_calls = [c.args[0] for c in pipe.incr.call_args_list]
    session_increments = [k for k in incr_calls if k.endswith(":sessions")]
    # One daily, one all-time.
    assert len(session_increments) == 2


@pytest.mark.asyncio
async def test_track_usage_handles_response_ms_int_truncation():
    """Redis incrby needs an int — verify we pass an int even when given a float."""
    service = _service_with_mock_redis()
    pipe = _mock_pipeline(service)

    await service._track_usage(
        intent_name="market_overview", is_new_session=False, response_ms=147.65,
    )

    incrby_calls = [c.args for c in pipe.incrby.call_args_list]
    # Two calls (daily + total), both with the same int value
    assert all(isinstance(args[1], int) for args in incrby_calls)
    assert all(args[1] == 147 for args in incrby_calls)


@pytest.mark.asyncio
async def test_track_usage_no_op_when_redis_missing():
    """Service without redis_client (init failure) → tracking is a no-op,
    not a hard error in the chat() path.
    """
    service = _service_with_mock_redis()
    service.redis_client = None  # simulate init failure

    # Should not raise
    await service._track_usage(
        intent_name="stock_price", is_new_session=False, response_ms=10.0,
    )


@pytest.mark.asyncio
async def test_track_usage_swallows_redis_errors():
    """A flaky Redis must not break /chat — tracking is best-effort."""
    service = _service_with_mock_redis()
    service.redis_client.pipeline = MagicMock(side_effect=RuntimeError("Redis down"))

    # Should not raise
    await service._track_usage(
        intent_name="stock_analysis", is_new_session=True, response_ms=200.0,
    )


# ---------------------------------------------------------------------------
# get_usage_stats — aggregate over the right key range per period
# ---------------------------------------------------------------------------

def _make_stats_pipeline(values):
    """Build a pipeline mock that returns `values` from execute().

    `values` is the per-key tuple expected by the production code:
    (sessions, messages, response_ms_sum, response_count, intents_dict).
    """
    pipe = AsyncMock()
    pipe.execute.return_value = values
    return pipe


@pytest.mark.asyncio
async def test_get_usage_stats_for_today_reads_only_today_keys():
    service = _service_with_mock_redis()
    # Production redis client uses decode_responses=True so Redis returns
    # str values, not bytes. Match that here.
    pipe = _make_stats_pipeline(
        ("5", "42", "6300", "42", {"stock_price": "30", "greeting": "12"})
    )
    service.redis_client.pipeline = MagicMock(return_value=pipe)

    stats = await service.get_usage_stats("today")

    # One pipeline run because today=1 day.
    assert service.redis_client.pipeline.call_count == 1
    assert stats["total_sessions"] == 5
    assert stats["total_messages"] == 42
    # avg_messages_per_session = 42 / 5 = 8.4
    assert stats["avg_messages_per_session"] == 8.4
    # avg_response_time_ms = 6300 / 42 = 150.0
    assert stats["avg_response_time_ms"] == 150.0
    # Top intents preserves count, sorted desc
    assert list(stats["top_intents"].keys())[0] == "stock_price"


@pytest.mark.asyncio
async def test_get_usage_stats_for_week_reads_seven_days():
    service = _service_with_mock_redis()
    pipe = _make_stats_pipeline(("1", "5", "500", "5", {}))
    service.redis_client.pipeline = MagicMock(return_value=pipe)

    await service.get_usage_stats("week")

    # 7 daily keys → 7 separate pipeline executions
    assert service.redis_client.pipeline.call_count == 7


@pytest.mark.asyncio
async def test_get_usage_stats_for_month_reads_thirty_days():
    service = _service_with_mock_redis()
    pipe = _make_stats_pipeline((None, None, None, None, {}))
    service.redis_client.pipeline = MagicMock(return_value=pipe)

    await service.get_usage_stats("month")

    assert service.redis_client.pipeline.call_count == 30


@pytest.mark.asyncio
async def test_get_usage_stats_for_all_reads_total_keys():
    service = _service_with_mock_redis()
    pipe = _make_stats_pipeline(
        ("1250", "8750", "2150125", "8750", {"stock_price": "3500"})
    )
    service.redis_client.pipeline = MagicMock(return_value=pipe)

    stats = await service.get_usage_stats("all")

    # "all" reads a single key range (chatbot:stats:total)
    assert service.redis_client.pipeline.call_count == 1
    assert stats["total_sessions"] == 1250
    assert stats["total_messages"] == 8750


@pytest.mark.asyncio
async def test_get_usage_stats_handles_missing_counters_as_zero():
    """Fresh deployment — Redis returns None for every counter. Stats
    should be all zeros, not raise on int(None)."""
    service = _service_with_mock_redis()
    pipe = _make_stats_pipeline((None, None, None, None, {}))
    service.redis_client.pipeline = MagicMock(return_value=pipe)

    stats = await service.get_usage_stats("today")

    assert stats["total_sessions"] == 0
    assert stats["total_messages"] == 0
    assert stats["avg_messages_per_session"] == 0.0
    assert stats["avg_response_time_ms"] == 0.0
    assert stats["top_intents"] == {}


@pytest.mark.asyncio
async def test_get_usage_stats_returns_zeros_when_redis_unavailable():
    """If Redis client failed to init, /stats degrades to zeros rather
    than 500-ing the admin dashboard."""
    service = ChatbotService()
    service.redis_client = None

    stats = await service.get_usage_stats("today")
    assert stats["total_sessions"] == 0
    assert stats["satisfaction_rate"] is None


@pytest.mark.asyncio
async def test_get_usage_stats_top_intents_capped_and_sorted():
    """Should return at most 10 intents, sorted descending by count."""
    service = _service_with_mock_redis()
    intents = {f"intent_{i}": str(100 - i) for i in range(15)}
    pipe = _make_stats_pipeline(("100", "500", "50000", "500", intents))
    service.redis_client.pipeline = MagicMock(return_value=pipe)

    stats = await service.get_usage_stats("today")

    assert len(stats["top_intents"]) == 10
    counts = list(stats["top_intents"].values())
    assert counts == sorted(counts, reverse=True)
    # Top entry should be the highest count
    assert counts[0] == 100


@pytest.mark.asyncio
async def test_get_usage_stats_swallows_redis_errors():
    """If Redis throws mid-aggregation, return zeros not 500."""
    service = _service_with_mock_redis()
    service.redis_client.pipeline = MagicMock(side_effect=RuntimeError("boom"))

    stats = await service.get_usage_stats("today")
    assert stats["total_sessions"] == 0
