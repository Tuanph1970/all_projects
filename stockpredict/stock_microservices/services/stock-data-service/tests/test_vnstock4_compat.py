"""vnstock 4.x compatibility.

vnstock 4.0.x changed two things the service depends on:

1. company.overview() returns `issue_share` several times (duplicate
   columns) and renamed fields (sector / foreigner_percentage /
   free_float_percentage); the old code raised "truth value of a Series is
   ambiguous" on every symbol, so the nightly sync stored 0 profiles.
2. Its `vnai` dependency enforces a client-side quota (20 req/min guest,
   60 with a free key). `vnstock_call()` spaces calls to stay under it and
   honours `retry_after` once when the quota is hit anyway.
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.services import stock_service as svc_mod
from app.services.stock_service import StockService


def _patch_vnstock(svc, fake_vnstock):
    return patch.object(
        type(svc), "vnstock", new_callable=lambda: property(lambda self: fake_vnstock)
    )


def _vnstock_with(fake_stock):
    v = MagicMock()
    v.stock.return_value = fake_stock
    return v


def _overview_v4() -> pd.DataFrame:
    """Shape of vnstock 4.0.7 / VCI overview() for FPT (trimmed)."""
    df = pd.DataFrame([[
        "FPT", 1_714_326_422.0, 1_714_326_422.0, 1_714_326_422.0, 1_714_326_422.0,
        "Technology", 0.28088507, 0.85, "FPT profile text",
    ]])
    df.columns = [
        "symbol", "issue_share", "issue_share", "issue_share", "issue_share",
        "sector", "foreigner_percentage", "free_float_percentage", "company_profile",
    ]
    return df


def _trading_stats_v4() -> pd.DataFrame:
    return pd.DataFrame({
        "symbol": ["FPT"],
        "number_of_shares_mkt_cap": [1_714_326_422.0],
        "issue_share": [1_714_326_422],
        "foreigner_percentage": [0.28088507],
    })


# ---------------------------------------------------------------------------
# overview() column layout
# ---------------------------------------------------------------------------

def test_dedupe_columns_keeps_first_of_repeated_issue_share():
    df = StockService._dedupe_columns(_overview_v4())
    assert list(df.columns).count("issue_share") == 1
    assert df.iloc[0]["issue_share"] == 1_714_326_422.0


def test_first_value_tolerates_missing_keys_nan_and_series():
    row = pd.Series({"a": float("nan"), "b": None, "c": 3})
    assert StockService._first_value(row, "zzz", "a", "b", "c") == 3
    assert StockService._first_value(row, "zzz", default="d") == "d"


@pytest.mark.asyncio
async def test_sync_company_profile_handles_vnstock4_overview():
    fake_stock = MagicMock()
    fake_stock.company.overview = lambda: _overview_v4()
    fake_stock.company.trading_stats = lambda: _trading_stats_v4()
    fake_stock.company.shareholders = lambda: pd.DataFrame({"share_holder": ["A", "B"]})

    repo = MagicMock()
    repo.upsert_company_profile = AsyncMock()
    svc = StockService(repo)

    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        ok = await svc.sync_company_profile("FPT")

    assert ok is True
    kwargs = repo.upsert_company_profile.await_args.kwargs
    assert kwargs["company_profile"] == "FPT profile text"
    assert kwargs["industry"] == "Technology"
    assert kwargs["issue_share"] == pytest.approx(1_714_326_422.0)
    assert kwargs["foreign_percent"] == pytest.approx(0.28088507)
    assert kwargs["outstanding_share"] == 1_714_326_422
    assert kwargs["free_float_rate"] == pytest.approx(0.85)
    assert kwargs["no_shareholders"] == 2
    # fields vnstock 4.x no longer provides stay None rather than raising
    assert kwargs["history"] is None
    assert kwargs["charter_capital"] is None


@pytest.mark.asyncio
async def test_sync_company_profile_v4_without_trading_stats_falls_back_to_issue_share():
    fake_stock = MagicMock()
    fake_stock.company.overview = lambda: _overview_v4()
    fake_stock.company.trading_stats.side_effect = RuntimeError("down")
    fake_stock.company.shareholders.side_effect = RuntimeError("down")

    repo = MagicMock()
    repo.upsert_company_profile = AsyncMock()
    svc = StockService(repo)

    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        ok = await svc.sync_company_profile("FPT")

    assert ok is True
    kwargs = repo.upsert_company_profile.await_args.kwargs
    # overview() itself carries foreigner_percentage in 4.x
    assert kwargs["foreign_percent"] == pytest.approx(0.28088507)
    assert "outstanding_share" not in kwargs


@pytest.mark.asyncio
async def test_get_company_profile_data_handles_vnstock4_overview():
    fake_stock = MagicMock()
    fake_stock.company.overview = lambda: _overview_v4()
    fake_stock.company.trading_stats = lambda: _trading_stats_v4()
    fake_stock.company.shareholders = lambda: pd.DataFrame({"share_holder": ["A"]})
    svc = StockService(MagicMock())

    with _patch_vnstock(svc, _vnstock_with(fake_stock)):
        records = await svc.get_company_profile_data("FPT")

    assert len(records) == 1
    rec = records[0]
    assert rec["industry"] == "Technology"
    assert rec["issueShare"] == pytest.approx(1_714_326_422.0)
    assert rec["foreignPercent"] == pytest.approx(0.28088507)
    assert rec["outstandingShare"] == 1_714_326_422
    assert rec["noShareholders"] == 1


def test_foreign_ownership_prefers_legacy_room_over_ratio_derivation():
    """vnstock 3.x path still derives outstanding shares from room / ratio."""
    ts_row = pd.Series({"current_holding_ratio": 0.4, "foreign_holding_room": 400_000})
    fp, outstanding = StockService._foreign_ownership(ts_row, pd.Series({"issueShare": 1.0}))
    assert fp == pytest.approx(0.4)
    assert outstanding == 1_000_000


# ---------------------------------------------------------------------------
# vnstock_call: quota spacing + retry
# ---------------------------------------------------------------------------

class _FakeRateLimit(Exception):
    def __init__(self, retry_after):
        super().__init__("rate limited")
        self.retry_after = retry_after
        self.tier = "guest"


@pytest.fixture
def quota_settings(monkeypatch):
    """Drive vnstock_call with explicit settings and a fresh timestamp."""
    monkeypatch.setattr(svc_mod, "_vnstock_last_call", 0.0)
    monkeypatch.setattr(svc_mod, "_vnstock_call_lock", None)
    monkeypatch.setattr(svc_mod, "_VnaiRateLimitExceeded", _FakeRateLimit)
    monkeypatch.setattr(svc_mod.settings, "VNSTOCK_RATE_LIMIT_RETRY", True)
    monkeypatch.setattr(svc_mod.settings, "VNSTOCK_RATE_LIMIT_MAX_WAIT_SECONDS", 90.0)
    return monkeypatch


@pytest.mark.asyncio
async def test_vnstock_call_spaces_consecutive_calls(quota_settings):
    quota_settings.setattr(svc_mod.settings, "VNSTOCK_MIN_INTERVAL_SECONDS", 0.05)
    calls = []
    t0 = time.monotonic()
    for _ in range(3):
        await svc_mod.vnstock_call(lambda: calls.append(time.monotonic() - t0))
    assert len(calls) == 3
    # second and third calls are each at least ~min_interval after the previous
    assert calls[1] - calls[0] >= 0.04
    assert calls[2] - calls[1] >= 0.04


@pytest.mark.asyncio
async def test_vnstock_call_serialises_concurrent_callers(quota_settings):
    quota_settings.setattr(svc_mod.settings, "VNSTOCK_MIN_INTERVAL_SECONDS", 0.03)
    stamps = []
    await asyncio.gather(*[
        svc_mod.vnstock_call(lambda: stamps.append(time.monotonic())) for _ in range(4)
    ])
    stamps.sort()
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    assert all(g >= 0.02 for g in gaps), gaps


@pytest.mark.asyncio
async def test_vnstock_call_retries_once_after_rate_limit(quota_settings):
    quota_settings.setattr(svc_mod.settings, "VNSTOCK_MIN_INTERVAL_SECONDS", 0.0)
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise _FakeRateLimit(retry_after=0.01)
        return "ok"

    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    with patch.object(svc_mod.asyncio, "sleep", fake_sleep):
        result = await svc_mod.vnstock_call(flaky)

    assert result == "ok"
    assert attempts["n"] == 2
    assert 0.01 in slept


@pytest.mark.asyncio
async def test_vnstock_call_gives_up_after_second_rate_limit(quota_settings):
    quota_settings.setattr(svc_mod.settings, "VNSTOCK_MIN_INTERVAL_SECONDS", 0.0)

    def always_limited():
        raise _FakeRateLimit(retry_after=0.0)

    with pytest.raises(_FakeRateLimit):
        await svc_mod.vnstock_call(always_limited)


@pytest.mark.asyncio
async def test_vnstock_call_does_not_retry_when_disabled(quota_settings):
    quota_settings.setattr(svc_mod.settings, "VNSTOCK_MIN_INTERVAL_SECONDS", 0.0)
    quota_settings.setattr(svc_mod.settings, "VNSTOCK_RATE_LIMIT_RETRY", False)
    attempts = {"n": 0}

    def limited():
        attempts["n"] += 1
        raise _FakeRateLimit(retry_after=0.0)

    with pytest.raises(_FakeRateLimit):
        await svc_mod.vnstock_call(limited)
    assert attempts["n"] == 1


@pytest.mark.asyncio
async def test_vnstock_call_caps_retry_wait(quota_settings):
    quota_settings.setattr(svc_mod.settings, "VNSTOCK_MIN_INTERVAL_SECONDS", 0.0)
    quota_settings.setattr(svc_mod.settings, "VNSTOCK_RATE_LIMIT_MAX_WAIT_SECONDS", 1.5)
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise _FakeRateLimit(retry_after=3600)
        return "ok"

    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    with patch.object(svc_mod.asyncio, "sleep", fake_sleep):
        assert await svc_mod.vnstock_call(flaky) == "ok"
    assert max(slept) == 1.5


def test_settings_default_interval_depends_on_api_key():
    from app.config import Settings
    assert Settings(VNSTOCK_API_KEY=None, VNSTOCK_MIN_INTERVAL_SECONDS=None).vnstock_min_interval == pytest.approx(3.1)
    assert Settings(VNSTOCK_API_KEY="abcdefghijkl", VNSTOCK_MIN_INTERVAL_SECONDS=None).vnstock_min_interval == pytest.approx(1.05)
    assert Settings(VNSTOCK_API_KEY=None, VNSTOCK_MIN_INTERVAL_SECONDS=0.5).vnstock_min_interval == 0.5


def test_settings_blank_env_values_are_treated_as_unset(monkeypatch):
    """docker-compose passes `${VAR:-}` through as an empty string."""
    from app.config import Settings
    monkeypatch.setenv("VNSTOCK_API_KEY", "")
    monkeypatch.setenv("VNSTOCK_MIN_INTERVAL_SECONDS", "")
    s = Settings()
    assert s.VNSTOCK_API_KEY is None
    assert s.VNSTOCK_MIN_INTERVAL_SECONDS is None
    assert s.vnstock_min_interval == pytest.approx(3.1)


@pytest.mark.asyncio
async def test_background_calls_yield_the_slot_to_interactive_callers(quota_settings):
    """A sync-task call (vnstock_background=True) sleeps one interval after
    releasing the lock, so an interactive call issued meanwhile runs before
    the sync's next call instead of queuing behind it."""
    quota_settings.setattr(svc_mod.settings, "VNSTOCK_MIN_INTERVAL_SECONDS", 0.05)
    order = []

    async def background():
        svc_mod.vnstock_background.set(True)
        for i in range(3):
            await svc_mod.vnstock_call(lambda i=i: order.append(f"bg{i}"))

    async def interactive():
        await asyncio.sleep(0.02)  # arrive while bg0 is done and bg is yielding
        await svc_mod.vnstock_call(lambda: order.append("ui"))

    await asyncio.gather(asyncio.create_task(background()), asyncio.create_task(interactive()))
    assert order.index("ui") < order.index("bg2"), order


@pytest.mark.asyncio
async def test_sync_all_company_data_marks_its_calls_background():
    svc = StockService(MagicMock())
    svc.STOCK_GROUPS = {"VN30": []}
    seen = {}

    async def run():
        await svc.sync_all_company_data()
        seen["flag"] = svc_mod.vnstock_background.get()

    await asyncio.create_task(run())
    assert seen["flag"] is True
    assert svc_mod.vnstock_background.get() is False  # did not leak out of the task
