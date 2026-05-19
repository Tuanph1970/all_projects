"""API routes for decision-helper-service.

F-010 bootstrap: health + risk-prefs + position-state stubs.
F-012..F-016: POST /signal-analysis — regime + signal + confirmation pipeline.
F-027:        POST /recommend      — full orchestrator (Phase C).
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_current_user_optional, get_db
from app.models.schemas import (
    BacktestRequest,
    BacktestResultSchema,
    BacktestStatsSchema,
    EquityPointSchema,
    TradeRecordSchema,
    WalkForwardWindowSchema,
    PositionStateResponse,
    RecommendRequest,
    RecommendationResponse,
    SignalAnalysisRequest,
    SignalAnalysisResponse,
    SignalResultSchema,
    RawSignalSchema,
    UserRiskPrefsRequest,
    UserRiskPrefsResponse,
)
from app.services.decision.orchestrator import run_recommendation
from app.services.market.client import get_market_client
from app.services.regime.classifier import classify_regime
from app.services.signal.base import OHLCVBar, RawSignal
from app.services.signal.trend.ma_cross import detect_ma_cross
from app.services.signal.trend.n_day_breakout import detect_n_day_breakout
from app.services.signal.range.sr_bounce_breakout import detect_sr_signal
from app.services.confirmation.layer import confirm

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# F-012..F-016 — Signal analysis pipeline
# ---------------------------------------------------------------------------

def _to_signal_result(raw: RawSignal, conf_result) -> SignalResultSchema:
    return SignalResultSchema(
        signal=RawSignalSchema(
            kind=raw.kind,
            direction=raw.direction,
            confidence=raw.confidence,
            trigger_price=raw.trigger_price,
            evidence=raw.evidence,
        ),
        confirmed=conf_result.accepted,
        final_confidence=conf_result.final_confidence,
        confirmation_steps=conf_result.reason_steps,
        rejection_reason=conf_result.rejection_reason,
    )


@router.post("/signal-analysis", response_model=SignalAnalysisResponse)
async def signal_analysis(
    req: SignalAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    """Phase-B pipeline: regime → signals → confirmation.

    Returns regime classification and all signal results for the given
    (ticker, bar_date).  Stop / target / size are added in Phase C.
    """
    t0 = time.time()
    client = get_market_client()
    ticker = req.ticker.upper()

    # 1. Classify regime
    regime_result = await classify_regime(ticker, client)

    # 2. Fetch OHLCV (300 bars gives enough history for slow MA + N-day breakout)
    raw_bars = await client.fetch_ohlcv(ticker, days=300, end_date=req.bar_date)
    if not raw_bars:
        raise HTTPException(status_code=404, detail=f"No OHLCV data for {ticker}")

    bars = [OHLCVBar.from_dict(b) for b in raw_bars]

    # Validate bar_date exists in the series
    if not any(b.date == req.bar_date for b in bars):
        raise HTTPException(
            status_code=422,
            detail=f"bar_date {req.bar_date} not found in price series for {ticker}",
        )

    # 3. Fetch RSI for oscillator rule (best-effort)
    rsi: Optional[float] = None
    technical = await client.fetch_technical(ticker)
    if technical:
        indicators = technical.get("indicators", [])
        rsi_item = next((i for i in indicators if i.get("name") == "RSI"), None)
        if rsi_item:
            rsi = rsi_item.get("value")

    # 4. Run signal engines based on regime
    raw_signals: List[RawSignal] = []

    if regime_result.regime in ("TREND_UP", "TREND_DOWN"):
        sig = detect_ma_cross(bars, req.bar_date, fast_period=req.fast_ma, slow_period=req.slow_ma)
        if sig:
            raw_signals.append(sig)
        bo = detect_n_day_breakout(bars, req.bar_date, n=req.breakout_n)
        if bo:
            raw_signals.append(bo)

    elif regime_result.regime == "RANGE":
        sr_data = await client.fetch_sr_levels(ticker)
        if sr_data:
            sr_sig = detect_sr_signal(bars, req.bar_date, sr_data)
            if sr_sig:
                raw_signals.append(sr_sig)

    else:
        # UNDEFINED regime: run all engines; confirmation will apply stricter filters
        sig = detect_ma_cross(bars, req.bar_date, fast_period=req.fast_ma, slow_period=req.slow_ma)
        if sig:
            raw_signals.append(sig)
        bo = detect_n_day_breakout(bars, req.bar_date, n=req.breakout_n)
        if bo:
            raw_signals.append(bo)

    # 5. Run confirmation layer on each raw signal
    signal_results: List[SignalResultSchema] = []
    for raw in raw_signals:
        conf_result = confirm(
            signal=raw,
            bars=bars,
            regime=regime_result.regime,
            rsi=rsi,
            k_delay=req.k_delay,
        )
        signal_results.append(_to_signal_result(raw, conf_result))

    # Best signal = highest confirmed confidence, else highest raw confidence
    confirmed = [s for s in signal_results if s.confirmed]
    best = (
        max(confirmed, key=lambda s: s.final_confidence)
        if confirmed
        else (max(signal_results, key=lambda s: s.signal.confidence) if signal_results else None)
    )

    latency_ms = int((time.time() - t0) * 1000)

    return SignalAnalysisResponse(
        ticker=ticker,
        bar_date=req.bar_date,
        regime=regime_result.regime,
        regime_confidence=regime_result.confidence,
        regime_features=regime_result.features,
        signals=signal_results,
        best_signal=best,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# F-027 — Full recommendation (Phase C orchestrator)
# ---------------------------------------------------------------------------

@router.post("/recommend", response_model=RecommendationResponse)
async def recommend(
    req: RecommendRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the full decision pipeline for (ticker, bar_date).

    Returns a single recommendation (action + stop + target + size) with an
    auditable reason chain stored in decision_runs.
    """
    user_id: int = current_user["user_id"]
    ticker = req.ticker.upper()
    client = get_market_client()

    result = await run_recommendation(
        user_id=user_id,
        ticker=ticker,
        bar_date=req.bar_date,
        trigger=req.trigger,
        db=db,
        client=client,
    )
    return result


@router.post("/backtest", response_model=BacktestResultSchema)
async def run_backtest(
    req: BacktestRequest,
    current_user: dict = Depends(get_current_user),
):
    """F-050 / F-051 — Replay the decision pipeline over historical bars.

    Fetches OHLCV data from stock-data-service once, then runs bar-by-bar
    simulation with inline regime / ATR / S/R computations (no per-bar HTTP).
    Returns trade ledger, equity curve, and summary stats.
    Set walk_forward=true to also run OOS windows and get aggregated variance.
    """
    import time as _time
    from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars
    from app.services.backtest.walk_forward import WalkForwardConfig, run_walk_forward
    from app.services.signal.base import OHLCVBar

    t0 = _time.time()
    ticker = req.ticker.upper()
    client = get_market_client()

    # Fetch bars — include 300 extra warmup days before start_date
    from datetime import timedelta
    warmup_start = req.start_date - timedelta(days=400)
    raw_bars = await client.fetch_ohlcv(
        ticker, days=(req.end_date - warmup_start).days + 10, end_date=req.end_date
    )
    if not raw_bars:
        raise HTTPException(status_code=404, detail=f"No OHLCV data for {ticker}")

    bars = [OHLCVBar.from_dict(b) for b in raw_bars]

    config = BacktestConfig(
        ticker=ticker,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_equity=req.initial_equity,
        risk_per_trade_pct=req.risk_per_trade_pct,
        fast_ma=req.fast_ma,
        slow_ma=req.slow_ma,
        breakout_n=req.breakout_n,
        k_delay=req.k_delay,
        slippage_bps=req.slippage_bps,
        commission=req.commission,
    )

    result = run_backtest_on_bars(config, bars)

    # Optionally run walk-forward
    wf_windows: List[WalkForwardWindowSchema] = []
    wf_aggregate: Optional[Dict[str, Any]] = None
    if req.walk_forward:
        wf_config = WalkForwardConfig(wf_window_days=req.wf_window_days)
        wf_result = run_walk_forward(config, bars, wf_config)
        wf_windows = [
            WalkForwardWindowSchema(
                window_index=w.window_index,
                start_date=w.start_date,
                end_date=w.end_date,
                stats=BacktestStatsSchema(**vars(w.stats)),
                num_trades=w.num_trades,
            )
            for w in wf_result.windows
        ]
        wf_aggregate = wf_result.aggregate_stats

    latency_ms = int((_time.time() - t0) * 1000)

    return BacktestResultSchema(
        ticker=result.ticker,
        start_date=result.start_date,
        end_date=result.end_date,
        config=result.config,
        trade_ledger=[TradeRecordSchema(**vars(t)) for t in result.trade_ledger],
        equity_curve=[EquityPointSchema(**vars(p)) for p in result.equity_curve],
        stats=BacktestStatsSchema(**vars(result.stats)),
        walk_forward_windows=wf_windows,
        walk_forward_aggregate=wf_aggregate,
        latency_ms=latency_ms,
    )


@router.get("/capabilities")
async def get_capabilities():
    return {
        "service": "decision-helper-service",
        "version": "0.6.0",
        "phase": "F — backtest / walk-forward harness",
        "features": [
            "user_risk_prefs",
            "position_state",
            "signal_analysis",          # F-012..F-016
            "recommend",                # F-027
            "failed_signal_detector",   # F-040..F-041
            "midtrend_entries",         # F-042
            "backtest",                 # F-050..F-052
            "walk_forward",             # F-051
        ],
    }


# ---------------------------------------------------------------------------
# User risk preferences (F-011 prerequisite)
# ---------------------------------------------------------------------------

@router.get("/risk-prefs", response_model=UserRiskPrefsResponse)
async def get_risk_prefs(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's risk preferences (or 404 if not set)."""
    from sqlalchemy import select
    from app.models.domain import UserRiskPrefs

    user_id = current_user["user_id"]
    result = await db.execute(
        select(UserRiskPrefs).where(UserRiskPrefs.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        raise HTTPException(status_code=404, detail="Risk preferences not set")
    return UserRiskPrefsResponse(
        user_id=prefs.user_id,
        account_equity=float(prefs.account_equity),
        risk_per_trade_pct=float(prefs.risk_per_trade_pct),
        max_concurrent_positions=prefs.max_concurrent_positions,
        max_correlation=float(prefs.max_correlation),
        loss_streak_size_cut=float(prefs.loss_streak_size_cut),
        loss_streak_threshold=prefs.loss_streak_threshold,
        updated_at=prefs.updated_at,
    )


@router.put("/risk-prefs", response_model=UserRiskPrefsResponse)
async def upsert_risk_prefs(
    data: UserRiskPrefsRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update the authenticated user's risk preferences."""
    from sqlalchemy import select
    from app.models.domain import UserRiskPrefs

    user_id = current_user["user_id"]
    result = await db.execute(
        select(UserRiskPrefs).where(UserRiskPrefs.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()

    if prefs is None:
        prefs = UserRiskPrefs(user_id=user_id)
        db.add(prefs)

    prefs.account_equity = data.account_equity
    prefs.risk_per_trade_pct = data.risk_per_trade_pct
    prefs.max_concurrent_positions = data.max_concurrent_positions
    prefs.max_correlation = data.max_correlation
    prefs.loss_streak_size_cut = data.loss_streak_size_cut
    prefs.loss_streak_threshold = data.loss_streak_threshold

    await db.commit()
    await db.refresh(prefs)

    return UserRiskPrefsResponse(
        user_id=prefs.user_id,
        account_equity=float(prefs.account_equity),
        risk_per_trade_pct=float(prefs.risk_per_trade_pct),
        max_concurrent_positions=prefs.max_concurrent_positions,
        max_correlation=float(prefs.max_correlation),
        loss_streak_size_cut=float(prefs.loss_streak_size_cut),
        loss_streak_threshold=prefs.loss_streak_threshold,
        updated_at=prefs.updated_at,
    )


# ---------------------------------------------------------------------------
# Position state (read-only view; writes come from the decision engine)
# ---------------------------------------------------------------------------

@router.get("/positions/{ticker}", response_model=PositionStateResponse)
async def get_position(
    ticker: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current position state for (user, ticker).  FLAT if none."""
    from sqlalchemy import select
    from app.models.domain import PositionState

    user_id = current_user["user_id"]
    result = await db.execute(
        select(PositionState).where(
            PositionState.user_id == user_id,
            PositionState.ticker == ticker.upper(),
        )
    )
    pos = result.scalar_one_or_none()
    if pos is None:
        return PositionStateResponse(
            user_id=user_id, ticker=ticker.upper(), state="FLAT"
        )
    return PositionStateResponse(
        user_id=pos.user_id,
        ticker=pos.ticker,
        state=pos.state,
        entry_bar_date=pos.entry_bar_date,
        entry_price=float(pos.entry_price) if pos.entry_price else None,
        position_size=pos.position_size,
        current_stop=float(pos.current_stop) if pos.current_stop else None,
        current_target=float(pos.current_target) if pos.current_target else None,
        entry_signal_kind=pos.entry_signal_kind,
    )
