"""API routes for decision-helper-service.

F-010 bootstrap: health + risk-prefs + position-state stubs.
F-012..F-016: POST /signal-analysis — regime + signal + confirmation pipeline.
F-027:        POST /recommend      — full orchestrator (Phase C).
F-060..F-065: GET /discipline/summary, POST /discipline/validate-plan (Phase G).
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_current_user_optional, get_current_user_from_token, get_db
from app.models.schemas import (
    ActionBreakdownItem,
    AlertEvent,
    AlertsListResponse,
    AnalyticsResponse,
    BacktestRequest,
    BacktestResultSchema,
    BacktestStatsSchema,
    ConfidenceBucketItem,
    DailyActionablePoint,
    DisciplineSummaryResponse,
    DisciplineViolationSchema,
    EquityPointSchema,
    JournalSyncStatus,
    OutcomeRecord,
    OutcomeSummary,
    OutcomesResponse,
    PositionStateResponse,
    PositionsListResponse,
    RecommendRequest,
    RecommendationResponse,
    RegimeBreakdownItem,
    RuleAdvisorySchema,
    RawSignalSchema,
    ScanRequest,
    ScanResponse,
    ScanResultItem,
    ScheduledRunsResponse,
    ScheduledRunSummary,
    SignalAnalysisRequest,
    SignalAnalysisResponse,
    SignalBreakdownItem,
    SignalResultSchema,
    TopTickerItem,
    TradeRecordSchema,
    UserRiskPrefsRequest,
    UserRiskPrefsResponse,
    UpdateStopRequest,
    ValidatePlanRequest,
    ValidatePlanResponse,
    WalkForwardWindowSchema,
    WatchlistAddRequest,
    WatchlistEntryResponse,
)
from app.services.decision.orchestrator import run_recommendation
from app.services.discipline.checks import run_all_checks
from app.services.discipline.rules_engine import evaluate_rules
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
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the full decision pipeline for (ticker, bar_date).

    Returns a single recommendation (action + stop + target + size) with an
    auditable reason chain stored in decision_runs.  If the user has linked a
    journal account (F-170), the trade is auto-synced as a background task.
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

    # F-170..F-173 — Journal sync (fire-and-forget; never blocks the response)
    jwt_token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if jwt_token:
        import asyncio
        from app.models.domain import UserRiskPrefs, PositionState
        from app.services.journal_sync import (
            open_journal_trade, close_journal_trade,
        )
        from sqlalchemy import select as _select

        prefs_row = (await db.execute(
            _select(UserRiskPrefs).where(UserRiskPrefs.user_id == user_id)
        )).scalar_one_or_none()
        journal_account_id = prefs_row.journal_account_id if prefs_row else None

        if journal_account_id:
            pos_row = (await db.execute(
                _select(PositionState).where(
                    PositionState.user_id == user_id,
                    PositionState.ticker == ticker,
                )
            )).scalar_one_or_none()

            if result.action in ("BUY", "SELL_SHORT") and result.entry_price and result.stop_price:
                direction = "LONG" if result.action == "BUY" else "SHORT"

                async def _open():
                    tid = await open_journal_trade(
                        account_id=journal_account_id,
                        jwt_token=jwt_token,
                        ticker=ticker,
                        direction=direction,
                        entry_date=req.bar_date,
                        entry_price=result.entry_price,
                        initial_stop=result.stop_price,
                        position_size=result.position_size or 1,
                        signal_kind=result.signal_kind,
                    )
                    if tid and pos_row:
                        from app.api.dependencies import async_session_factory
                        async with async_session_factory() as sess:
                            from sqlalchemy import update as _update
                            await sess.execute(
                                _update(PositionState)
                                .where(PositionState.user_id == user_id, PositionState.ticker == ticker)
                                .values(journal_trade_id=tid)
                            )
                            await sess.commit()

                asyncio.create_task(_open())
                result.journal_sync = JournalSyncStatus(synced=False, action="open")

            elif result.action in ("SELL", "COVER", "REVERSE"):
                journal_trade_id = pos_row.journal_trade_id if pos_row else None
                if journal_trade_id and result.entry_price:
                    exit_price = result.entry_price  # entry_price holds exit close for exits

                    async def _close():
                        await close_journal_trade(
                            account_id=journal_account_id,
                            journal_trade_id=journal_trade_id,
                            jwt_token=jwt_token,
                            exit_price=exit_price,
                            exit_date=req.bar_date,
                        )

                    asyncio.create_task(_close())
                    result.journal_sync = JournalSyncStatus(
                        synced=False, journal_trade_id=journal_trade_id, action="close"
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


# ---------------------------------------------------------------------------
# F-060..F-065 — Discipline overlay (Phase G)
# ---------------------------------------------------------------------------

@router.get("/discipline/summary", response_model=DisciplineSummaryResponse)
async def get_discipline_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's discipline summary.

    Includes: loss streak, recent actions, and advisory rules.
    """
    from sqlalchemy import and_, desc, select
    from app.models.domain import DecisionRun, UserRiskPrefs

    user_id = current_user["user_id"]

    # Load risk prefs
    prefs_result = await db.execute(
        select(UserRiskPrefs).where(UserRiskPrefs.user_id == user_id)
    )
    prefs = prefs_result.scalar_one_or_none()
    loss_streak_threshold = prefs.loss_streak_threshold if prefs else 3
    account_equity = float(prefs.account_equity) if prefs and prefs.account_equity else None

    # Load last 10 exit actions to detect streak
    runs_result = await db.execute(
        select(DecisionRun.action)
        .where(
            and_(
                DecisionRun.user_id == user_id,
                DecisionRun.action.in_(["BUY", "SELL", "SELL_SHORT", "COVER", "REVERSE", "HOLD", "WAIT"]),
            )
        )
        .order_by(desc(DecisionRun.bar_date))
        .limit(10)
    )
    last_10_actions = list(runs_result.scalars().all())

    # Count consecutive exits (SELL/COVER/REVERSE) as losses (simplified)
    recent_losses = 0
    for act in last_10_actions:
        if act in ("SELL", "COVER", "REVERSE"):
            recent_losses += 1
        else:
            break

    streak_active = recent_losses >= loss_streak_threshold

    # Build rule advisories (no active trade context here — use generic state)
    rule_advisories = evaluate_rules(
        action="WAIT",
        stop_price=None,
        target_price=None,
        entry_price=None,
        direction=None,
        regime=None,
        recent_losses=recent_losses,
        loss_streak_threshold=loss_streak_threshold,
        violations=[],
    )

    return DisciplineSummaryResponse(
        user_id=user_id,
        recent_losses=recent_losses,
        loss_streak_threshold=loss_streak_threshold,
        streak_active=streak_active,
        current_equity=account_equity,
        last_10_actions=last_10_actions,
        rule_advisories=[
            RuleAdvisorySchema(
                rule_id=a.rule_id,
                rule_text=a.rule_text,
                chapter=a.chapter,
                triggered=a.triggered,
                severity=a.severity,
                detail=a.detail,
            )
            for a in rule_advisories
        ],
    )


@router.post("/discipline/validate-plan", response_model=ValidatePlanResponse)
async def validate_plan(
    req: ValidatePlanRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate a proposed trade plan against discipline rules.

    Call this before saving a TradePlan to surface BLOCK/WARNING violations.
    Returns is_valid=False if any BLOCK violations exist.
    """
    from sqlalchemy import and_, desc, select
    from app.models.domain import DecisionRun, PositionState, UserRiskPrefs

    user_id = current_user["user_id"]

    prefs_result = await db.execute(
        select(UserRiskPrefs).where(UserRiskPrefs.user_id == user_id)
    )
    prefs = prefs_result.scalar_one_or_none()
    loss_streak_threshold = prefs.loss_streak_threshold if prefs else 3

    # Load current position for averaging-down check
    pos_result = await db.execute(
        select(PositionState).where(
            and_(
                PositionState.user_id == user_id,
                PositionState.ticker == req.ticker.upper(),
            )
        )
    )
    pos = pos_result.scalar_one_or_none()
    pos_state = pos.state if pos else "FLAT"
    existing_entry = float(pos.entry_price) if pos and pos.entry_price else None
    existing_stop = float(pos.current_stop) if pos and pos.current_stop else None

    # Count recent losses for streak check
    runs_result = await db.execute(
        select(DecisionRun.action)
        .where(
            and_(
                DecisionRun.user_id == user_id,
                DecisionRun.action.in_(["SELL", "COVER", "REVERSE"]),
            )
        )
        .order_by(desc(DecisionRun.bar_date))
        .limit(10)
    )
    recent_losses = len(list(runs_result.scalars().all()))

    violations = run_all_checks(
        action=req.action,
        stop_price=req.stop_price,
        target_price=req.target_price,
        pos_state=pos_state,
        entry_price=existing_entry,
        current_price=req.entry_price,
        proposed_stop=req.stop_price,
        prev_stop=existing_stop,
        direction=req.direction or (pos.state if pos and pos.state != "FLAT" else None),
        recent_losses=recent_losses,
        loss_streak_threshold=loss_streak_threshold,
    )

    rule_advisories = evaluate_rules(
        action=req.action,
        stop_price=req.stop_price,
        target_price=req.target_price,
        entry_price=req.entry_price,
        direction=req.direction,
        regime=req.regime,
        recent_losses=recent_losses,
        loss_streak_threshold=loss_streak_threshold,
        violations=violations,
    )

    is_valid = not any(v.severity == "BLOCK" for v in violations)

    return ValidatePlanResponse(
        is_valid=is_valid,
        violations=[
            DisciplineViolationSchema(
                rule_id=v.rule_id,
                severity=v.severity,
                message=v.message,
                evidence=v.evidence,
            )
            for v in violations
        ],
        rule_advisories=[
            RuleAdvisorySchema(
                rule_id=a.rule_id,
                rule_text=a.rule_text,
                chapter=a.chapter,
                triggered=a.triggered,
                severity=a.severity,
                detail=a.detail,
            )
            for a in rule_advisories
        ],
    )


# ---------------------------------------------------------------------------
# F-070 — HelperWatchlist CRUD
# ---------------------------------------------------------------------------

@router.get("/watchlist", response_model=List[WatchlistEntryResponse])
async def list_watchlist(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all active watchlist entries for the authenticated user."""
    from sqlalchemy import select
    from app.models.domain import HelperWatchlist

    user_id = current_user["user_id"]
    result = await db.execute(
        select(HelperWatchlist)
        .where(HelperWatchlist.user_id == user_id, HelperWatchlist.active.is_(True))
        .order_by(HelperWatchlist.created_at)
    )
    entries = result.scalars().all()
    return [
        WatchlistEntryResponse(
            id=e.id, user_id=e.user_id, ticker=e.ticker,
            active=e.active, note=e.note, created_at=e.created_at,
        )
        for e in entries
    ]


@router.post("/watchlist", response_model=WatchlistEntryResponse, status_code=201)
async def add_watchlist(
    req: WatchlistAddRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a ticker to the user's watchlist (idempotent — reactivates if soft-deleted)."""
    from sqlalchemy import select
    from app.models.domain import HelperWatchlist

    user_id = current_user["user_id"]
    ticker = req.ticker.upper()

    result = await db.execute(
        select(HelperWatchlist).where(
            HelperWatchlist.user_id == user_id, HelperWatchlist.ticker == ticker
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        entry = HelperWatchlist(user_id=user_id, ticker=ticker, note=req.note)
        db.add(entry)
    else:
        entry.active = True
        entry.note = req.note

    await db.commit()
    await db.refresh(entry)

    return WatchlistEntryResponse(
        id=entry.id, user_id=entry.user_id, ticker=entry.ticker,
        active=entry.active, note=entry.note, created_at=entry.created_at,
    )


@router.delete("/watchlist/{ticker}", status_code=204)
async def remove_watchlist(
    ticker: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a ticker from the user's watchlist."""
    from sqlalchemy import select
    from app.models.domain import HelperWatchlist

    user_id = current_user["user_id"]
    result = await db.execute(
        select(HelperWatchlist).where(
            HelperWatchlist.user_id == user_id,
            HelperWatchlist.ticker == ticker.upper(),
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Ticker not in watchlist")

    entry.active = False
    await db.commit()


# ---------------------------------------------------------------------------
# F-072 / F-073 — Scheduled runs log
# ---------------------------------------------------------------------------

@router.get("/scheduled-runs", response_model=ScheduledRunsResponse)
async def list_scheduled_runs(
    limit: int = 50,
    alerts_only: bool = False,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return recent SCHEDULED decision runs for the authenticated user.

    Set alerts_only=true to show only BUY/SELL_SHORT results.
    """
    from sqlalchemy import and_, desc, func as sqlfunc, select
    from app.models.domain import DecisionRun

    user_id = current_user["user_id"]
    alert_actions = ["BUY", "SELL_SHORT"]

    conditions = [
        DecisionRun.user_id == user_id,
        DecisionRun.trigger == "SCHEDULED",
    ]
    if alerts_only:
        conditions.append(DecisionRun.action.in_(alert_actions))

    count_result = await db.execute(
        select(sqlfunc.count()).select_from(DecisionRun).where(and_(*conditions))
    )
    total = count_result.scalar_one()

    runs_result = await db.execute(
        select(DecisionRun)
        .where(and_(*conditions))
        .order_by(desc(DecisionRun.created_at))
        .limit(min(limit, 200))
    )
    runs = runs_result.scalars().all()

    return ScheduledRunsResponse(
        total=total,
        runs=[
            ScheduledRunSummary(
                id=r.id,
                ticker=r.ticker,
                bar_date=r.bar_date,
                action=r.action,
                regime=r.regime,
                confidence=float(r.confidence) if r.confidence else None,
                latency_ms=r.latency_ms,
                created_at=r.created_at,
                is_alert=r.action in alert_actions,
            )
            for r in runs
        ],
    )


@router.post("/watchlist/run-all", status_code=202)
async def trigger_scheduled_run(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger the scheduled daily runner for the authenticated user (F-071).

    Runs recommendations for all active watchlist tickers in the background.
    """
    import asyncio
    from app.services.scheduler import run_for_user

    user_id = current_user["user_id"]
    asyncio.create_task(run_for_user(user_id))
    return {"status": "accepted", "message": "Scheduled run queued for your watchlist."}


# ---------------------------------------------------------------------------
# F-080..F-083 — Real-time alerts (Phase I)
# ---------------------------------------------------------------------------

@router.get("/alerts")
async def list_recent_alerts(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertsListResponse:
    """Return the last N BUY/SELL_SHORT scheduled runs as alerts (seed for AlertHistory)."""
    from sqlalchemy import and_, desc, select
    from app.models.domain import DecisionRun

    user_id = current_user["user_id"]
    result = await db.execute(
        select(DecisionRun)
        .where(
            and_(
                DecisionRun.user_id == user_id,
                DecisionRun.trigger == "SCHEDULED",
                DecisionRun.action.in_(["BUY", "SELL_SHORT"]),
            )
        )
        .order_by(desc(DecisionRun.created_at))
        .limit(min(limit, 100))
    )
    runs = result.scalars().all()
    alerts = [
        AlertEvent(
            ticker=r.ticker,
            action=r.action,
            bar_date=str(r.bar_date),
            regime=r.regime,
            confidence=float(r.confidence) if r.confidence else None,
            stop_price=float(r.stop_price) if r.stop_price else None,
            target_price=float(r.target_price) if r.target_price else None,
        )
        for r in runs
    ]
    return AlertsListResponse(alerts=alerts, total=len(alerts))


@router.get("/alerts/stream")
async def stream_alerts(token: str):
    """SSE endpoint — pushes real-time alert events to connected browsers.

    Browser EventSource cannot send custom headers, so the JWT is passed
    as ?token=<jwt> and validated here.  Emits keepalive comments every
    25 seconds to prevent proxy timeouts.
    """
    import asyncio
    import json
    from fastapi.responses import StreamingResponse
    from app.services.alert_broker import alert_broker

    current_user = await get_current_user_from_token(token)
    user_id = current_user["user_id"]

    async def event_generator():
        queue = alert_broker.subscribe(user_id)
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=25.0)
                    data = json.dumps(payload)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            alert_broker.unsubscribe(user_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# F-130..F-133 — Performance analytics (Phase N)
# ---------------------------------------------------------------------------

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    days: int = 90,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return decision-run performance analytics for the authenticated user.

    Covers the last `days` calendar days (default 90).  All aggregations run
    directly on decision_runs — no cross-service calls required.
    """
    from collections import defaultdict
    from datetime import datetime as dt, timedelta
    from sqlalchemy import and_, case, cast, func as sqlfunc, select, Float
    from app.models.domain import DecisionRun

    user_id = current_user["user_id"]
    cutoff = date.today() - timedelta(days=days)
    computed_at = dt.utcnow()

    base_where = and_(
        DecisionRun.user_id == user_id,
        DecisionRun.bar_date >= cutoff,
    )

    # ── 1. Action breakdown ──────────────────────────────────────────────────
    action_rows = (await db.execute(
        select(DecisionRun.action, sqlfunc.count().label("cnt"))
        .where(base_where)
        .group_by(DecisionRun.action)
    )).all()

    total_decisions = sum(r.cnt for r in action_rows)
    actionable_count = sum(r.cnt for r in action_rows if r.action in ("BUY", "SELL_SHORT"))

    action_breakdown = [
        ActionBreakdownItem(
            action=r.action,
            count=r.cnt,
            pct=round(r.cnt / total_decisions * 100, 1) if total_decisions else 0.0,
        )
        for r in sorted(action_rows, key=lambda x: -x.cnt)
    ]

    # ── 2. Regime breakdown ──────────────────────────────────────────────────
    regime_rows = (await db.execute(
        select(
            DecisionRun.regime,
            sqlfunc.count().label("total"),
            sqlfunc.sum(case((DecisionRun.action == "BUY", 1), else_=0)).label("buy_c"),
            sqlfunc.sum(case((DecisionRun.action == "SELL_SHORT", 1), else_=0)).label("ss_c"),
            sqlfunc.sum(case((DecisionRun.action.in_(["HOLD", "WAIT"]), 1), else_=0)).label("hw_c"),
        )
        .where(base_where)
        .group_by(DecisionRun.regime)
    )).all()

    regime_breakdown = [
        RegimeBreakdownItem(
            regime=r.regime or "UNDEFINED",
            total=r.total,
            buy_count=r.buy_c or 0,
            sell_short_count=r.ss_c or 0,
            hold_wait_count=r.hw_c or 0,
        )
        for r in sorted(regime_rows, key=lambda x: -x.total)
    ]

    # ── 3. Signal breakdown ──────────────────────────────────────────────────
    signal_rows = (await db.execute(
        select(
            DecisionRun.signal_kind,
            sqlfunc.count().label("fire_count"),
            sqlfunc.sum(case((DecisionRun.signal_confirmed.is_(True), 1), else_=0)).label("conf_c"),
            sqlfunc.avg(cast(DecisionRun.confidence, Float)).label("avg_conf"),
        )
        .where(and_(base_where, DecisionRun.signal_kind.isnot(None)))
        .group_by(DecisionRun.signal_kind)
    )).all()

    signal_breakdown = [
        SignalBreakdownItem(
            signal_kind=r.signal_kind,
            fire_count=r.fire_count,
            confirmed_count=r.conf_c or 0,
            confirmation_rate=round((r.conf_c or 0) / r.fire_count, 3) if r.fire_count else 0.0,
            avg_confidence=round(float(r.avg_conf or 0), 3),
        )
        for r in sorted(signal_rows, key=lambda x: -x.fire_count)
    ]

    # ── 4. Daily actionable trend (last `days`) ──────────────────────────────
    daily_rows = (await db.execute(
        select(DecisionRun.bar_date, sqlfunc.count().label("cnt"))
        .where(and_(
            base_where,
            DecisionRun.action.in_(["BUY", "SELL_SHORT"]),
        ))
        .group_by(DecisionRun.bar_date)
        .order_by(DecisionRun.bar_date)
    )).all()

    daily_actionable = [
        DailyActionablePoint(date=str(r.bar_date), count=r.cnt)
        for r in daily_rows
    ]

    # ── 5. Top tickers ───────────────────────────────────────────────────────
    ticker_rows = (await db.execute(
        select(
            DecisionRun.ticker,
            sqlfunc.count().label("total"),
            sqlfunc.sum(case((DecisionRun.action == "BUY", 1), else_=0)).label("buy_c"),
            sqlfunc.sum(case((DecisionRun.action == "SELL_SHORT", 1), else_=0)).label("ss_c"),
        )
        .where(base_where)
        .group_by(DecisionRun.ticker)
        .order_by(sqlfunc.count().desc())
        .limit(10)
    )).all()

    top_tickers = [
        TopTickerItem(
            ticker=r.ticker,
            decision_count=r.total,
            buy_count=r.buy_c or 0,
            sell_short_count=r.ss_c or 0,
        )
        for r in ticker_rows
    ]

    # ── 6. Confidence histogram (10% buckets) ────────────────────────────────
    bucket_map: dict[str, int] = defaultdict(int)
    conf_rows = (await db.execute(
        select(DecisionRun.confidence)
        .where(and_(base_where, DecisionRun.confidence.isnot(None)))
    )).scalars().all()

    for conf in conf_rows:
        pct = int(float(conf) * 10) * 10   # floor to nearest 10%
        pct = min(pct, 90)
        key = f"{pct}-{pct + 10}%"
        bucket_map[key] += 1

    confidence_histogram = [
        ConfidenceBucketItem(bucket=f"{p}-{p + 10}%", count=bucket_map.get(f"{p}-{p + 10}%", 0))
        for p in range(0, 100, 10)
    ]

    return AnalyticsResponse(
        user_id=user_id,
        computed_at=computed_at,
        days=days,
        total_decisions=total_decisions,
        actionable_count=actionable_count,
        action_breakdown=action_breakdown,
        regime_breakdown=regime_breakdown,
        signal_breakdown=signal_breakdown,
        daily_actionable=daily_actionable,
        top_tickers=top_tickers,
        confidence_histogram=confidence_histogram,
    )


# ---------------------------------------------------------------------------
# F-120..F-123 — Multi-ticker scanner (Phase M)
# ---------------------------------------------------------------------------

_ACTIONABLE_ACTIONS = {"BUY", "SELL_SHORT"}
_ACTION_RANK = {"BUY": 0, "SELL_SHORT": 1, "COVER": 2, "REVERSE": 3, "HOLD": 4, "WAIT": 5}


@router.post("/scan", response_model=ScanResponse)
async def scan_watchlist(
    req: ScanRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the decision engine across all active watchlist tickers for the user.

    Returns a ranked list (BUY/SELL_SHORT first, then by confidence desc).
    Each ticker runs independently; failures are captured in the error field
    rather than aborting the whole scan.
    """
    import asyncio
    from app.api.dependencies import async_session_factory
    from app.models.domain import HelperWatchlist

    user_id = current_user["user_id"]
    bar_date = req.bar_date or date.today()
    t0 = time.time()

    # Load watchlist
    wl_result = await db.execute(
        select(HelperWatchlist).where(
            HelperWatchlist.user_id == user_id,
            HelperWatchlist.active.is_(True),
        )
    )
    entries = wl_result.scalars().all()

    if not entries:
        return ScanResponse(
            bar_date=bar_date,
            ticker_count=0,
            actionable_count=0,
            results=[],
            latency_ms=int((time.time() - t0) * 1000),
        )

    client = get_market_client()
    semaphore = asyncio.Semaphore(5)   # cap concurrent OHLCV fetches

    async def _scan_one(ticker: str) -> ScanResultItem:
        async with semaphore:
            try:
                async with async_session_factory() as session:
                    rec = await run_recommendation(
                        user_id=user_id,
                        ticker=ticker,
                        bar_date=bar_date,
                        trigger="ON_DEMAND",
                        db=session,
                        client=client,
                    )
                return ScanResultItem(
                    ticker=rec.ticker,
                    action=rec.action,
                    regime=rec.regime,
                    confidence=rec.confidence,
                    entry_price=rec.entry_price,
                    stop_price=rec.stop_price,
                    target_price=rec.target_price,
                    position_size=rec.position_size,
                    signal_kind=rec.signal_kind,
                    signal_confirmed=rec.signal_confirmed,
                    is_actionable=rec.action in _ACTIONABLE_ACTIONS,
                )
            except Exception as exc:
                logger.warning("Scan failed for %s: %s", ticker, exc)
                return ScanResultItem(
                    ticker=ticker,
                    action="WAIT",
                    regime="UNDEFINED",
                    confidence=0.0,
                    is_actionable=False,
                    error=str(exc),
                )

    tickers = [e.ticker for e in entries]
    items = await asyncio.gather(*[_scan_one(t) for t in tickers])

    # Rank: actionable first, then by action rank, then by confidence desc
    ranked = sorted(
        items,
        key=lambda r: (_ACTION_RANK.get(r.action, 9), -r.confidence),
    )

    actionable = sum(1 for r in ranked if r.is_actionable)

    return ScanResponse(
        bar_date=bar_date,
        ticker_count=len(tickers),
        actionable_count=actionable,
        results=ranked,
        latency_ms=int((time.time() - t0) * 1000),
    )


# ---------------------------------------------------------------------------
# F-160..F-163 — Trade outcome tagging (Phase Q)
# ---------------------------------------------------------------------------

@router.get("/outcomes", response_model=OutcomesResponse)
async def get_outcomes(
    days: int = 90,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return tagged trade outcomes for the authenticated user.

    Only BUY/SELL_SHORT runs that have been closed (outcome IS NOT NULL) are
    included.  The summary computes win-rate, average R, and expectancy.
    Covers the last `days` calendar days (default 90).
    """
    from datetime import datetime as dt, timedelta
    from sqlalchemy import and_, select
    from app.models.domain import DecisionRun

    user_id = current_user["user_id"]
    cutoff = date.today() - timedelta(days=days)
    computed_at = dt.utcnow()

    result = await db.execute(
        select(DecisionRun)
        .where(
            and_(
                DecisionRun.user_id == user_id,
                DecisionRun.action.in_(["BUY", "SELL_SHORT"]),
                DecisionRun.outcome.isnot(None),
                DecisionRun.bar_date >= cutoff,
            )
        )
        .order_by(DecisionRun.bar_date.desc())
    )
    runs = result.scalars().all()

    records = [
        OutcomeRecord(
            run_id=r.id,
            ticker=r.ticker,
            bar_date=r.bar_date,
            action=r.action,
            entry_price=float(r.entry_price) if r.entry_price else None,
            stop_price=float(r.stop_price) if r.stop_price else None,
            exit_price=float(r.exit_price) if r.exit_price else None,
            outcome=r.outcome,
            r_multiple=float(r.r_multiple) if r.r_multiple else None,
            exit_run_id=r.exit_run_id,
            signal_kind=r.signal_kind,
            regime=r.regime,
            created_at=r.created_at,
        )
        for r in runs
    ]

    tagged = [rec for rec in records if rec.outcome is not None]
    wins = sum(1 for r in tagged if r.outcome == "WIN")
    losses = sum(1 for r in tagged if r.outcome == "LOSS")
    breakevens = sum(1 for r in tagged if r.outcome == "BREAKEVEN")
    total_tagged = len(tagged)
    win_rate = wins / total_tagged if total_tagged else 0.0

    r_values = [r.r_multiple for r in tagged if r.r_multiple is not None]
    avg_r = round(sum(r_values) / len(r_values), 3) if r_values else None
    expectancy = round(avg_r * win_rate - abs(avg_r) * (1 - win_rate), 3) if avg_r is not None else None

    summary = OutcomeSummary(
        total_tagged=total_tagged,
        wins=wins,
        losses=losses,
        breakevens=breakevens,
        win_rate=round(win_rate, 3),
        avg_r=avg_r,
        expectancy=expectancy,
    )

    return OutcomesResponse(
        user_id=user_id,
        days=days,
        computed_at=computed_at,
        summary=summary,
        records=records,
    )


@router.get("/capabilities")
async def get_capabilities():
    return {
        "service": "decision-helper-service",
        "version": "1.4.0",
        "phase": "R — journal sync",
        "features": [
            "user_risk_prefs",
            "position_state",
            "signal_analysis",          # F-012..F-016
            "recommend",                # F-027
            "failed_signal_detector",   # F-040..F-041
            "midtrend_entries",         # F-042
            "backtest",                 # F-050..F-052
            "walk_forward",             # F-051
            "discipline_checks",        # F-060..F-063
            "rules_engine",             # F-065
            "watchlist",                # F-070
            "scheduler",                # F-071
            "action_alerts",            # F-072
            "scheduled_runs_log",       # F-073
            "alert_broker",             # F-080
            "sse_stream",               # F-081
            "real_time_alerts",         # F-082..F-083
            "scanner",                  # F-120..F-123
            "analytics",                # F-130..F-133
            "positions_list",           # F-150
            "position_stop_update",     # F-151
            "outcome_tagging",          # F-160..F-163
            "journal_sync",             # F-170..F-173
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
        journal_account_id=prefs.journal_account_id,
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
    if data.journal_account_id is not None:
        prefs.journal_account_id = data.journal_account_id

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
        journal_account_id=prefs.journal_account_id,
        updated_at=prefs.updated_at,
    )


# ---------------------------------------------------------------------------
# Position state (read-only view; writes come from the decision engine)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# F-150..F-153 — Open positions dashboard (Phase P)
# ---------------------------------------------------------------------------

@router.get("/positions", response_model=PositionsListResponse)
async def list_open_positions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all non-FLAT positions for the authenticated user."""
    from sqlalchemy import select
    from app.models.domain import PositionState

    user_id = current_user["user_id"]
    result = await db.execute(
        select(PositionState).where(
            PositionState.user_id == user_id,
            PositionState.state.in_(["LONG", "SHORT"]),
        ).order_by(PositionState.entry_bar_date)
    )
    rows = result.scalars().all()

    positions = [
        PositionStateResponse(
            user_id=p.user_id,
            ticker=p.ticker,
            state=p.state,
            entry_bar_date=p.entry_bar_date,
            entry_price=float(p.entry_price) if p.entry_price else None,
            position_size=p.position_size,
            current_stop=float(p.current_stop) if p.current_stop else None,
            current_target=float(p.current_target) if p.current_target else None,
            entry_signal_kind=p.entry_signal_kind,
        )
        for p in rows
    ]
    return PositionsListResponse(positions=positions, total=len(positions))


@router.put("/positions/{ticker}/stop", response_model=PositionStateResponse)
async def update_position_stop(
    ticker: str,
    req: UpdateStopRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current_stop on an open position (trailing-stop management).

    Only allowed on LONG or SHORT positions — raises 404 if the position
    is FLAT or does not exist.
    """
    from sqlalchemy import select
    from app.models.domain import PositionState

    user_id = current_user["user_id"]
    result = await db.execute(
        select(PositionState).where(
            PositionState.user_id == user_id,
            PositionState.ticker == ticker.upper(),
            PositionState.state.in_(["LONG", "SHORT"]),
        )
    )
    pos = result.scalar_one_or_none()
    if pos is None:
        raise HTTPException(
            status_code=404,
            detail=f"No open position for {ticker.upper()}",
        )

    pos.current_stop = req.current_stop
    await db.commit()
    await db.refresh(pos)

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
