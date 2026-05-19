"""F-027 — Decision orchestrator (Schwager Ch 12, 14).

Runs the full pipeline for one (user_id, ticker, bar_date):

    regime → OHLCV/ATR/swings/S/R fetch
           → signal engines (regime-routed)
           → confirmation layer
           → position state (DB)
           → trailing-stop update
           → state-machine transition
           → stop / target / size (new entries only)
           → persist (decision_runs + position_states)
           → return RecommendationResponse

Success criteria (roadmap Phase C):
    Replay on 5 tickers × 1 year of bars completes in < 30 s total.
    Every new entry includes a stop, a target, and a position size.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import DecisionRun, PositionState, UserRiskPrefs
from app.models.schemas import ReasonStep, RecommendationResponse
from app.services.confirmation.layer import ConfirmationResult, confirm
from app.services.market.client import MarketClient
from app.services.position.state_machine import StateTransition, next_state
from app.services.regime.classifier import classify_regime
from app.services.risk.sizing_module import compute_size
from app.services.risk.stop_module import compute_initial_stop, update_trailing_stop
from app.services.risk.target_module import compute_target
from app.services.signal.base import OHLCVBar, RawSignal
from app.services.signal.range.sr_bounce_breakout import detect_sr_signal
from app.services.signal.trend.ma_cross import detect_ma_cross
from app.services.signal.trend.n_day_breakout import detect_n_day_breakout

logger = logging.getLogger(__name__)

# Default parameters (can be overridden per request)
DEFAULT_FAST_MA = 10
DEFAULT_SLOW_MA = 50
DEFAULT_BREAKOUT_N = 20
DEFAULT_K_DELAY = 1
DEFAULT_EQUITY = 100_000.0
DEFAULT_RISK_PCT = 1.0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_recommendation(
    user_id: int,
    ticker: str,
    bar_date: date,
    trigger: str,
    db: AsyncSession,
    client: MarketClient,
    fast_ma: int = DEFAULT_FAST_MA,
    slow_ma: int = DEFAULT_SLOW_MA,
    breakout_n: int = DEFAULT_BREAKOUT_N,
    k_delay: int = DEFAULT_K_DELAY,
) -> RecommendationResponse:
    """Run one bar of one ticker through the full decision pipeline."""
    t0 = time.time()
    reason_chain: List[Dict[str, Any]] = []

    # ── 1. Regime ────────────────────────────────────────────────────────
    regime_result = await classify_regime(ticker, client)
    reason_chain.append({
        "stage": "regime",
        "message": (
            f"Regime: {regime_result.regime} "
            f"(confidence={regime_result.confidence:.2f})"
        ),
        "evidence": regime_result.features,
    })

    # ── 2. Market data ───────────────────────────────────────────────────
    raw_bars = await client.fetch_ohlcv(ticker, days=300, end_date=bar_date)
    if not raw_bars:
        return _abort_response(
            user_id, ticker, bar_date, trigger, regime_result.regime,
            reason_chain, "No OHLCV data available", t0,
        )

    bars = [OHLCVBar.from_dict(b) for b in raw_bars]
    current_bar = next(
        (b for b in reversed(bars) if b.date <= bar_date),
        bars[-1],
    )

    atr_data = await client.fetch_atr(ticker)
    atr: Optional[float] = float(atr_data["latest"]) if atr_data else None

    swings_data = await client.fetch_swings(ticker)
    swings: List[Dict[str, Any]] = (
        swings_data.get("pivots", []) if swings_data else []
    )

    sr_data: Optional[Dict[str, Any]] = await client.fetch_sr_levels(ticker)

    rsi: Optional[float] = None
    technical = await client.fetch_technical(ticker)
    if technical:
        for ind in technical.get("indicators", []):
            if ind.get("name") == "RSI":
                rsi = float(ind["value"])
                break

    # ── 3. Signal engines ─────────────────────────────────────────────────
    raw_signals: List[RawSignal] = _run_signal_engines(
        regime=regime_result.regime,
        bars=bars,
        bar_date=bar_date,
        fast_ma=fast_ma,
        slow_ma=slow_ma,
        breakout_n=breakout_n,
        sr_data=sr_data,
    )
    reason_chain.append({
        "stage": "signal_engine",
        "message": f"{len(raw_signals)} raw signal(s) generated",
        "evidence": {
            "signals": [
                {"kind": s.kind, "direction": s.direction, "confidence": s.confidence}
                for s in raw_signals
            ]
        },
    })

    # ── 4. Confirmation layer ─────────────────────────────────────────────
    confirmed_results: List[ConfirmationResult] = [
        confirm(signal=raw, bars=bars, regime=regime_result.regime, rsi=rsi, k_delay=k_delay)
        for raw in raw_signals
    ]

    best_confirmed: Optional[ConfirmationResult] = max(
        (r for r in confirmed_results if r.accepted),
        key=lambda r: r.final_confidence,
        default=None,
    )
    best_signal: Optional[RawSignal] = best_confirmed.signal if best_confirmed else None
    signal_direction: Optional[str] = best_signal.direction if best_signal else None

    reason_chain.append({
        "stage": "confirmation",
        "message": (
            f"Best confirmed: {best_signal.kind if best_signal else 'none'} "
            f"direction={signal_direction or 'n/a'} "
            f"confidence={best_confirmed.final_confidence:.3f if best_confirmed else 0:.3f}"
        ),
        "evidence": {},
    })

    # ── 5. Position state from DB ──────────────────────────────────────────
    pos_row = await _load_position(db, user_id, ticker)
    state_before = pos_row.state if pos_row else "FLAT"
    current_stop: Optional[float] = (
        float(pos_row.current_stop) if pos_row and pos_row.current_stop else None
    )
    current_target: Optional[float] = (
        float(pos_row.current_target) if pos_row and pos_row.current_target else None
    )

    # ── 6. Trailing stop update ────────────────────────────────────────────
    if state_before in ("LONG", "SHORT") and current_stop is not None and atr:
        improved = update_trailing_stop(
            direction=state_before,
            current_stop=current_stop,
            current_close=current_bar.close,
            atr=atr,
        )
        if improved is not None:
            current_stop = improved
            reason_chain.append({
                "stage": "trailing_stop",
                "message": f"Trailing stop improved to {improved:.4f}",
                "evidence": {"new_stop": improved, "atr": atr},
            })

    # ── 7. State machine ───────────────────────────────────────────────────
    transition: StateTransition = next_state(
        current_state=state_before,
        signal_direction=signal_direction,
        current_close=current_bar.close,
        current_stop=current_stop,
        current_target=current_target,
        signal_confirmed=best_confirmed is not None,
    )
    reason_chain.append({
        "stage": "state_machine",
        "message": transition.reason,
        "evidence": {
            "state_before": transition.state_before,
            "action": transition.action,
            "state_after": transition.state_after,
        },
    })

    # ── 8. Risk overlay ────────────────────────────────────────────────────
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    position_size: Optional[int] = None

    if transition.action in ("BUY", "SELL_SHORT") and best_signal:
        entry_price = current_bar.close
        prefs = await _load_prefs(db, user_id)
        equity = float(prefs.account_equity) if prefs and prefs.account_equity else DEFAULT_EQUITY
        risk_pct = float(prefs.risk_per_trade_pct) if prefs else DEFAULT_RISK_PCT
        loss_streak_threshold = prefs.loss_streak_threshold if prefs else 3
        loss_streak_size_cut = float(prefs.loss_streak_size_cut) if prefs else 0.5

        recent_losses = await _count_recent_losses(db, user_id, ticker)

        stop_result = compute_initial_stop(
            direction=signal_direction,  # type: ignore[arg-type]
            entry_price=entry_price,
            atr=atr,
            swings=swings,
            sr_levels=sr_data,
        )
        stop_price = stop_result.stop_price
        reason_chain.append({
            "stage": "stop_module",
            "message": stop_result.reason,
            "evidence": {
                "stop_price": stop_price,
                "stop_kind": stop_result.stop_kind,
            },
        })

        target_result = compute_target(
            direction=signal_direction,  # type: ignore[arg-type]
            entry_price=entry_price,
            stop_price=stop_price,
            signal_kind=best_signal.kind,
            signal_evidence=best_signal.evidence,
            sr_levels=sr_data,
        )
        target_price = target_result.target_price
        reason_chain.append({
            "stage": "target_module",
            "message": target_result.reason,
            "evidence": {
                "target_price": target_price,
                "target_kind": target_result.target_kind,
                "partial_target": target_result.partial_target,
            },
        })

        size_result = compute_size(
            entry_price=entry_price,
            stop_price=stop_price,
            equity=equity,
            risk_pct=risk_pct,
            atr=atr,
            recent_losses=recent_losses,
            loss_streak_threshold=loss_streak_threshold,
            loss_streak_size_cut=loss_streak_size_cut,
        )
        position_size = size_result.shares
        reason_chain.append({
            "stage": "sizing_module",
            "message": (
                f"Size: {position_size} shares "
                f"(risk {size_result.risk_pct_actual:.2f}% of equity "
                f"= {size_result.risk_amount:.2f})"
            ),
            "evidence": {
                "shares": position_size,
                "risk_amount": size_result.risk_amount,
                "adjustments": size_result.adjustments,
            },
        })

    elif transition.action in ("SELL", "COVER", "REVERSE") and pos_row:
        entry_price = float(pos_row.entry_price) if pos_row.entry_price else None

    elif transition.action == "HOLD" and pos_row:
        entry_price = float(pos_row.entry_price) if pos_row.entry_price else None
        stop_price = current_stop
        target_price = current_target
        position_size = pos_row.position_size or None

    # ── 9. Persist ─────────────────────────────────────────────────────────
    overall_confidence = (
        best_confirmed.final_confidence if best_confirmed else 0.0
    )
    latency_ms = int((time.time() - t0) * 1000)

    await _persist(
        db=db,
        user_id=user_id,
        ticker=ticker,
        bar_date=bar_date,
        trigger=trigger,
        regime=regime_result.regime,
        best_signal=best_signal,
        best_confirmed=best_confirmed,
        transition=transition,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        position_size=position_size,
        current_stop=current_stop,
        reason_chain=reason_chain,
        confidence=overall_confidence,
        latency_ms=latency_ms,
        pos_row=pos_row,
        bar_date_val=bar_date,
    )

    return RecommendationResponse(
        user_id=user_id,
        ticker=ticker,
        bar_date=bar_date,
        trigger=trigger,
        regime=regime_result.regime,
        action=transition.action,
        state_before=state_before,
        state_after=transition.state_after,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        position_size=position_size,
        signal_kind=best_signal.kind if best_signal else None,
        signal_confirmed=best_confirmed is not None,
        confidence=overall_confidence,
        reason_chain=[
            ReasonStep(
                stage=r["stage"],
                message=r["message"],
                evidence=r.get("evidence", {}),
            )
            for r in reason_chain
        ],
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _run_signal_engines(
    regime: str,
    bars: List[OHLCVBar],
    bar_date: date,
    fast_ma: int,
    slow_ma: int,
    breakout_n: int,
    sr_data: Optional[Dict[str, Any]],
) -> List[RawSignal]:
    signals: List[RawSignal] = []

    if regime in ("TREND_UP", "TREND_DOWN"):
        sig = detect_ma_cross(bars, bar_date, fast_period=fast_ma, slow_period=slow_ma)
        if sig:
            signals.append(sig)
        bo = detect_n_day_breakout(bars, bar_date, n=breakout_n)
        if bo:
            signals.append(bo)

    elif regime == "RANGE":
        if sr_data:
            sr_sig = detect_sr_signal(bars, bar_date, sr_data)
            if sr_sig:
                signals.append(sr_sig)

    else:  # UNDEFINED — run trend engines; confirmation applies stricter filter
        sig = detect_ma_cross(bars, bar_date, fast_period=fast_ma, slow_period=slow_ma)
        if sig:
            signals.append(sig)
        bo = detect_n_day_breakout(bars, bar_date, n=breakout_n)
        if bo:
            signals.append(bo)

    return signals


async def _load_position(
    db: AsyncSession, user_id: int, ticker: str
) -> Optional[PositionState]:
    result = await db.execute(
        select(PositionState).where(
            PositionState.user_id == user_id,
            PositionState.ticker == ticker,
        )
    )
    return result.scalar_one_or_none()


async def _load_prefs(
    db: AsyncSession, user_id: int
) -> Optional[UserRiskPrefs]:
    result = await db.execute(
        select(UserRiskPrefs).where(UserRiskPrefs.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _count_recent_losses(
    db: AsyncSession, user_id: int, ticker: str, window: int = 10
) -> int:
    """Count consecutive closed-position losses (SELL/COVER/REVERSE) in recent runs."""
    from sqlalchemy import and_, desc
    result = await db.execute(
        select(DecisionRun.action)
        .where(
            and_(
                DecisionRun.user_id == user_id,
                DecisionRun.ticker == ticker,
                DecisionRun.action.in_(["SELL", "COVER", "REVERSE"]),
            )
        )
        .order_by(desc(DecisionRun.bar_date))
        .limit(window)
    )
    rows = result.scalars().all()
    # For simplicity count all recent exit actions as losses
    # (real P&L tracking is deferred to Phase D/E when journal is wired)
    return len(rows)


async def _persist(
    db: AsyncSession,
    user_id: int,
    ticker: str,
    bar_date: date,
    trigger: str,
    regime: str,
    best_signal: Optional[RawSignal],
    best_confirmed: Optional[ConfirmationResult],
    transition: StateTransition,
    entry_price: Optional[float],
    stop_price: Optional[float],
    target_price: Optional[float],
    position_size: Optional[int],
    current_stop: Optional[float],
    reason_chain: List[Dict[str, Any]],
    confidence: float,
    latency_ms: int,
    pos_row: Optional[PositionState],
    bar_date_val: date,
) -> None:
    try:
        run = DecisionRun(
            user_id=user_id,
            ticker=ticker,
            bar_date=bar_date,
            trigger=trigger,
            regime=regime,
            signal_kind=best_signal.kind if best_signal else None,
            signal_confirmed=best_confirmed is not None,
            action=transition.action,
            state_before=transition.state_before,
            state_after=transition.state_after,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            position_size=position_size,
            reason_chain_json=reason_chain,
            confidence=confidence,
            latency_ms=latency_ms,
        )
        db.add(run)

        # Update position state row
        if pos_row is None and transition.state_after != "FLAT":
            pos_row = PositionState(user_id=user_id, ticker=ticker)
            db.add(pos_row)

        if pos_row is not None:
            pos_row.state = transition.state_after
            pos_row.last_decision_run_id = None  # will be set after flush if needed

            if transition.action in ("BUY", "SELL_SHORT"):
                pos_row.entry_bar_date = bar_date_val
                pos_row.entry_price = entry_price
                pos_row.position_size = position_size or 0
                pos_row.current_stop = stop_price
                pos_row.current_target = target_price
                pos_row.entry_signal_kind = best_signal.kind if best_signal else None

            elif transition.action in ("SELL", "COVER", "REVERSE"):
                pos_row.entry_bar_date = None
                pos_row.entry_price = None
                pos_row.position_size = 0
                pos_row.current_stop = None
                pos_row.current_target = None
                pos_row.entry_signal_kind = None

            elif transition.action == "HOLD":
                pos_row.current_stop = current_stop  # may have been improved by trailing

        await db.commit()

    except Exception as exc:
        await db.rollback()
        logger.error(
            "Failed to persist decision run for %s/%s: %s", ticker, bar_date, exc
        )


def _abort_response(
    user_id: int,
    ticker: str,
    bar_date: date,
    trigger: str,
    regime: str,
    reason_chain: List[Dict[str, Any]],
    reason: str,
    t0: float,
) -> RecommendationResponse:
    reason_chain.append({"stage": "abort", "message": reason, "evidence": {}})
    return RecommendationResponse(
        user_id=user_id,
        ticker=ticker,
        bar_date=bar_date,
        trigger=trigger,
        regime=regime,
        action="WAIT",
        state_before="FLAT",
        state_after="FLAT",
        confidence=0.0,
        reason_chain=[
            ReasonStep(stage=r["stage"], message=r["message"], evidence=r.get("evidence", {}))
            for r in reason_chain
        ],
        latency_ms=int((time.time() - t0) * 1000),
    )
