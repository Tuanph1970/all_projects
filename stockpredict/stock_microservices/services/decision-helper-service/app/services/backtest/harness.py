"""F-050 — Backtest replay engine (Schwager Ch 15).

Runs the full signal → confirmation → stop/target/size pipeline across a
historical bar sequence.  No I/O during the replay: regime / ATR / S/R /
swings / RSI are computed inline from available bars at each step.

Public API
----------
run_backtest_on_bars(config, bars) -> BacktestResult
    Pure function; takes pre-fetched OHLCVBar list and returns a complete
    BacktestResult including trade ledger, equity curve, and summary stats.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from app.services.backtest.market_features import (
    compute_atr,
    compute_regime,
    compute_rsi,
    compute_sr_levels,
    compute_swings,
)
from app.services.backtest.slippage import apply_slippage, trade_cost
from app.services.confirmation.layer import ConfirmationResult, confirm
from app.services.risk.pyramiding import evaluate_pyramid
from app.services.risk.sizing_module import compute_size
from app.services.risk.basing_point import BasingPointTracker
from app.services.risk.stop_module import compute_initial_stop, update_trailing_stop
from app.services.risk.target_module import compute_target

#: EM-8 M3. See `BacktestConfig.target_mode`.
TARGET_MODES = frozenset({"TARGETS_ON", "TRAILING_ONLY"})
from app.services.signal.base import OHLCVBar, RawSignal
from app.services.signal.failed_signal import OVERRIDE_THRESHOLD, detect_failed_signals, highest_severity
from app.services.signal.range.sr_bounce_breakout import detect_sr_signal
from app.services.signal.trend.ma_cross import detect_ma_cross
from app.services.signal.trend.midtrend import detect_midtrend_entry
from app.services.signal.trend.n_day_breakout import detect_n_day_breakout


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class BacktestConfig:
    ticker: str
    start_date: date
    end_date: date
    initial_equity: float = 100_000.0
    risk_per_trade_pct: float = 1.0
    fast_ma: int = 10
    slow_ma: int = 50
    breakout_n: int = 20
    k_delay: int = 1
    slippage_bps: float = 5.0

    # Backlog #80 — transaction costs are PROPORTIONAL to turnover.
    #
    # `commission` was a flat fee per trade defaulting to 10.0, and on the
    # harness's own defaults that came to 1.8x the gross result it was meant
    # to measure: any A/B run through here was arbitrated by the cost model,
    # not by the thing under test. It is kept as a per-side flat fee so the
    # old model stays expressible, but it now defaults to zero.
    commission: float = 0.0            # flat fee per SIDE (was per trade)
    commission_pct: float = 0.15       # brokerage, % of turnover per side
    sell_tax_pct: float = 0.10         # VN transfer tax, % of proceeds, sells only

    # Backlog #80 — the churn guards. Measured on the default config before
    # these existed: the harness turned over a trade every 2.5 bars, 66% of
    # exits were FAILED_SIGNAL at a median holding period of ONE day, and 103
    # of 150 exits were followed by a new entry on the SAME bar.
    reentry_cooldown_bars: int = 1     # bars that must pass after a close
    failed_signal_grace_bars: int = 2  # failed-signal override is muted this long

    # Backlog #82 — whether the failed-signal override may close a position
    # at all. It may not, by default, and that is a MEASURED decision:
    #
    #   criterion, pre-registered: the override earns its place only if GROSS
    #   P&L PER TRADE is higher with it on. (Gross and per-trade, because at
    #   ~3x fees an arm wins on net by trading less, and turning the override
    #   off reduces turnover by construction — #80's lesson.)
    #
    #   measured, 12 real VN symbols:
    #                       trades  bars/trade  median hold  gross/trade
    #     override ON         2,581        4.64          2d       -20.46
    #     override OFF        1,345        8.91          6d       -11.81
    #                                          Welch t = -0.44 (ns)
    #
    # So it is no better and probably worse, while closing 64% of all
    # positions. The exit mix is the clinching secondary reading: with the
    # override off, 78% of positions end at their STOP and 22% at their
    # TARGET, so the ATR stop each trade was *sized* for finally decides the
    # outcome instead of being pre-empted.
    #
    # Only the BACKTEST default changes. The live recommendation path
    # (`decision/orchestrator.py`) still consults these verdicts; changing
    # that is user-visible and needs its own decision — see Backlog #83.
    failed_signal_enabled: bool = False

    # EM-3 — which trailing-stop rule the replay uses.
    #   "ATR"          the shipped 2xATR trail
    #   "BASING_POINT" E&M Ch 28: three days clear of a reaction low, then a
    #                  filter below it, never lowered
    # The A/B this exists for is the candidate's mandatory C4 benchmark.
    trailing_stop_mode: str = "ATR"
    # EM-8 M3. The plan asked for three arms (MEASURED_FIRST / NO_MEASURED /
    # TRAILING_ONLY) to answer "should a measured objective be a target at
    # all". Two of them turned out to be the same run: MEASURED_MOVE has
    # never fired, because no shipped signal detector puts
    # `measured_move_target` in evidence and the orchestrator routes
    # ai-insights patterns to the failed-signal detectors instead
    # (orchestrator.py:118-179). Measured: 4,193 of 4,193 target computations
    # over 12 symbols and 11 years carried no such key, and MEASURED_MOVE was
    # 0% of chosen targets. tests/test_target_mode.py keeps that dead path
    # dead-by-record rather than dead-by-accident.
    #
    # What remains is the measurable half, and it is E&M's actual Ch 32
    # claim -- the book "prefers nearby progressive stops for taking profits
    # over limit orders", and targets do fire here via S/R and fixed R:R.
    #   TARGETS_ON      today's behaviour: compute_target as shipped
    #   TRAILING_ONLY   no profit target; exit on the stop alone
    target_mode: str = "TARGETS_ON"
    basing_point_filter_pct: float = 6.0
    basing_point_new_high_rule: bool = False
    allow_pyramiding: bool = False         # F-043 — opt-in; default off keeps replay unchanged
    max_pyramid_fraction: float = 0.5


# ---------------------------------------------------------------------------
# Output data structures
# ---------------------------------------------------------------------------

@dataclass
class TradeRecord:
    ticker: str
    direction: str
    entry_date: date
    entry_price: float
    exit_date: Optional[date]
    exit_price: Optional[float]
    shares: int
    gross_pnl: Optional[float]
    commission: float
    net_pnl: Optional[float]
    exit_reason: str    # STOP_HIT | TARGET_HIT | FAILED_SIGNAL | END_OF_PERIOD | SIGNAL
    # Backlog #85: the regime at ENTRY, which the replay already computes on
    # every bar. Recorded so a result can be read conditionally — #84 found
    # EM-3's edge is magnitude-driven, and the open question is whether that
    # magnitude concentrates in trending markets. Causal by construction:
    # `compute_regime` reads only bars up to the entry bar.
    entry_regime: str = "UNDEFINED"


@dataclass
class EquityPoint:
    date: date
    equity: float
    drawdown_pct: float


@dataclass
class BacktestStats:
    num_trades: int
    num_wins: int
    win_rate: float
    total_gross_pnl: float
    total_commission: float
    total_net_pnl: float
    max_drawdown_pct: float
    expectancy: float
    sharpe_ratio: Optional[float]
    profit_factor: Optional[float]


@dataclass
class BacktestResult:
    ticker: str
    start_date: date
    end_date: date
    config: Dict[str, Any]
    trade_ledger: List[TradeRecord] = field(default_factory=list)
    equity_curve: List[EquityPoint] = field(default_factory=list)
    stats: BacktestStats = field(default_factory=lambda: _empty_stats())


# ---------------------------------------------------------------------------
# Internal position tracker
# ---------------------------------------------------------------------------

@dataclass
class _Position:
    state: str = "FLAT"                 # FLAT | LONG | SHORT
    entry_regime: str = "UNDEFINED"     # regime at entry (Backlog #85)
    entry_cost: float = 0.0             # money paid to open (Backlog #80)
    entry_index: Optional[int] = None   # bar index of entry, for the grace window
    direction: Optional[str] = None    # LONG | SHORT
    entry_date: Optional[date] = None
    entry_price: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    shares: int = 0
    initial_shares: int = 0            # F-043 — size of the original leg (pyramid cap base)
    pyramided_shares: int = 0          # F-043 — cumulative shares added via pyramids


# ---------------------------------------------------------------------------
# Main harness
# ---------------------------------------------------------------------------

def run_backtest_on_bars(
    config: BacktestConfig,
    bars: List[OHLCVBar],
) -> BacktestResult:
    """Replay the decision pipeline across bars and return a BacktestResult.

    ``bars`` must be sorted oldest → newest and should include warm-up bars
    (300 + bars) before config.start_date so that MAs and ATR are primed.
    """
    if config.target_mode not in TARGET_MODES:
        raise ValueError(
            f"target_mode {config.target_mode!r} is not one of {sorted(TARGET_MODES)}"
        )

    trade_ledger: List[TradeRecord] = []
    equity_curve: List[EquityPoint] = []

    equity = config.initial_equity
    peak_equity = equity
    pos = _Position()
    last_exit_index: Optional[int] = None
    basing: Optional[BasingPointTracker] = None

    for idx, bar in enumerate(bars):
        if bar.date < config.start_date:
            continue

        bars_so_far = bars[: idx + 1]

        # ── 0. Compute market features from available history ────────────
        regime = compute_regime(bars_so_far)
        atr = compute_atr(bars_so_far)
        sr_data = compute_sr_levels(bars_so_far)
        swings = compute_swings(bars_so_far)
        rsi = compute_rsi(bars_so_far)

        # ── 1. Update trailing stop ──────────────────────────────────────
        if pos.state != "FLAT" and pos.stop is not None:
            if config.trailing_stop_mode == "BASING_POINT" and basing is not None:
                # EM-3. The tracker is fed this bar and only this bar, so the
                # rule cannot see ahead; it returns None until three days have
                # cleared a reaction low, and the entry stop stands until then.
                candidate = basing.update(bar.high, bar.low, bar.close)
                if candidate is not None:
                    if pos.direction == "LONG" and candidate > pos.stop:
                        pos.stop = candidate
                    elif pos.direction == "SHORT" and candidate < pos.stop:
                        pos.stop = candidate
            elif atr:
                new_stop = update_trailing_stop(
                    direction=pos.direction,  # type: ignore[arg-type]
                    current_stop=pos.stop,
                    current_close=bar.close,
                    atr=atr,
                )
                if new_stop is not None:
                    pos.stop = new_stop

        # ── 2. Check intrabar stop / target hits ─────────────────────────
        exited, exit_price, exit_reason = _check_exit(bar, pos)
        if exited and exit_price is not None:
            fill = apply_slippage(
                exit_price,
                "SELL" if pos.direction == "LONG" else "COVER",
                config.slippage_bps,
            )
            exit_cost = _side_cost(fill, pos.shares, "SELL" if pos.direction == "LONG" else "COVER", config)
            trade_ledger.append(
                _close_trade(pos, config.ticker, bar.date, fill, exit_reason, exit_cost)
            )
            # The entry cost was already taken out of equity when the position
            # opened, so only the exit leg is charged here.
            equity += (trade_ledger[-1].gross_pnl or 0.0) - exit_cost
            last_exit_index = idx
            pos = _Position()

        # ── 3. Failed-signal check (overrides when position is open) ─────
        #
        # Backlog #80's grace window. This override closed 66% of all trades
        # at a MEDIAN HOLDING PERIOD OF ONE DAY — the confirmation layer
        # approved an entry on bar N and the failed-signal detector declared
        # it failed on bar N+1, which is not two components disagreeing about
        # the market so much as about each other. (Backlog #79 separately
        # found these verdicts predict nothing.) Muting it for the first few
        # bars lets the trade's own stop do the job it was sized for.
        in_grace = (
            pos.entry_index is not None
            and (idx - pos.entry_index) < max(0, config.failed_signal_grace_bars)
        )
        if config.failed_signal_enabled and pos.state != "FLAT" and not in_grace:
            # Backlog #83 caps unvalidated verdicts below the override
            # threshold to protect the LIVE path. Enabling the override here
            # is an explicit request to study it as it was, so the cap is
            # bypassed — otherwise the flag would be a silent no-op.
            failed = detect_failed_signals(
                bars_so_far, bar.date, sr_data, None,
                apply_validation_policy=False,
            )
            top = highest_severity(failed)
            if top and top.severity >= OVERRIDE_THRESHOLD:
                fill = apply_slippage(
                    bar.close,
                    "SELL" if pos.direction == "LONG" else "COVER",
                    config.slippage_bps,
                )
                exit_cost = _side_cost(fill, pos.shares, "SELL" if pos.direction == "LONG" else "COVER", config)
                trade_ledger.append(
                    _close_trade(pos, config.ticker, bar.date, fill, "FAILED_SIGNAL", exit_cost)
                )
                equity += (trade_ledger[-1].gross_pnl or 0.0) - exit_cost
                last_exit_index = idx
                pos = _Position()

        # ── 3b. Pyramiding (F-043, opt-in) — add to a winning position ───
        if config.allow_pyramiding and pos.state != "FLAT" and bar.date <= config.end_date:
            equity += _maybe_pyramid(
                pos, bars_so_far, bar, regime, atr, swings, sr_data, rsi, equity, config
            )

        # ── 4. Entry signals (only when FLAT and before end_date) ────────
        #
        # Backlog #80's cooldown. Without it, 103 of 150 exits were followed
        # by a new entry on the SAME bar: the position closes in step 2 or 3,
        # `pos` goes FLAT, and this block re-opens it immediately because the
        # signal that justified the first entry is level-triggered and still
        # true. That is the churn engine, and it is what made the cost model
        # the dominant term in every result.
        cooling = (
            last_exit_index is not None
            and (idx - last_exit_index) < max(0, config.reentry_cooldown_bars)
        )
        if pos.state == "FLAT" and not cooling and bar.date <= config.end_date:
            signals = _run_signals(regime, bars_so_far, bar.date, config)
            best = _best_confirmed(signals, bars_so_far, regime, rsi, config.k_delay)

            if best:
                direction = best.signal.direction
                entry_fill = apply_slippage(bar.close, direction, config.slippage_bps)
                stop_res = compute_initial_stop(
                    direction=direction,
                    entry_price=entry_fill,
                    atr=atr,
                    swings=swings,
                    sr_levels=sr_data,
                )
                tgt_res = compute_target(
                    direction=direction,
                    entry_price=entry_fill,
                    stop_price=stop_res.stop_price,
                    signal_kind=best.signal.kind,
                    signal_evidence=best.signal.evidence,
                    sr_levels=sr_data,
                )
                target_price = (None if config.target_mode == "TRAILING_ONLY"
                                else tgt_res.target_price)
                size_res = compute_size(
                    entry_price=entry_fill,
                    stop_price=stop_res.stop_price,
                    equity=equity,
                    risk_pct=config.risk_per_trade_pct,
                    atr=atr,
                    recent_losses=0,
                    loss_streak_threshold=3,
                    loss_streak_size_cut=0.5,
                )
                if size_res.shares > 0:
                    basing = BasingPointTracker(
                        direction=direction,
                        filter_pct=config.basing_point_filter_pct,
                        use_new_high_rule=config.basing_point_new_high_rule,
                    )
                    entry_cost = _side_cost(entry_fill, size_res.shares, direction, config)
                    equity -= entry_cost
                    pos = _Position(
                        entry_regime=regime,
                        entry_cost=entry_cost,
                        entry_index=idx,
                        state=direction,
                        direction=direction,
                        entry_date=bar.date,
                        entry_price=entry_fill,
                        stop=stop_res.stop_price,
                        target=target_price,
                        shares=size_res.shares,
                        initial_shares=size_res.shares,
                    )

        # ── 5. Mark-to-market equity ─────────────────────────────────────
        mtm = equity
        if pos.state != "FLAT" and pos.entry_price and pos.shares:
            if pos.direction == "LONG":
                mtm += (bar.close - pos.entry_price) * pos.shares
            else:
                mtm += (pos.entry_price - bar.close) * pos.shares

        dd_pct = max(0.0, (peak_equity - mtm) / peak_equity) if peak_equity else 0.0
        peak_equity = max(peak_equity, mtm)
        equity_curve.append(EquityPoint(date=bar.date, equity=round(mtm, 2), drawdown_pct=round(dd_pct, 4)))

        if bar.date >= config.end_date:
            break

    # ── 6. Force-close any open position at end of period ────────────────
    if pos.state != "FLAT" and bars:
        last_bar = bars[-1]
        fill = apply_slippage(
            last_bar.close,
            "SELL" if pos.direction == "LONG" else "COVER",
            config.slippage_bps,
        )
        exit_cost = _side_cost(
            fill, pos.shares, "SELL" if pos.direction == "LONG" else "COVER", config,
        )
        trade_ledger.append(
            _close_trade(pos, config.ticker, last_bar.date, fill, "END_OF_PERIOD", exit_cost)
        )
        # Only the exit leg: the entry leg left equity when the position
        # opened. Adding `net_pnl` here would charge it twice — which it did
        # until Backlog #80, and it is why the equity curve and the headline
        # net never reconciled.
        equity += (trade_ledger[-1].gross_pnl or 0.0) - exit_cost

    stats = _compute_stats(trade_ledger, equity_curve)

    return BacktestResult(
        ticker=config.ticker,
        start_date=config.start_date,
        end_date=config.end_date,
        config={
            "initial_equity": config.initial_equity,
            "risk_per_trade_pct": config.risk_per_trade_pct,
            "fast_ma": config.fast_ma,
            "slow_ma": config.slow_ma,
            "breakout_n": config.breakout_n,
            "k_delay": config.k_delay,
            "slippage_bps": config.slippage_bps,
            "commission": config.commission,
            "commission_pct": config.commission_pct,
            "sell_tax_pct": config.sell_tax_pct,
            "reentry_cooldown_bars": config.reentry_cooldown_bars,
            "failed_signal_grace_bars": config.failed_signal_grace_bars,
            "failed_signal_enabled": config.failed_signal_enabled,
            "trailing_stop_mode": config.trailing_stop_mode,
            "target_mode": config.target_mode,
            "basing_point_filter_pct": config.basing_point_filter_pct,
            "basing_point_new_high_rule": config.basing_point_new_high_rule,
            "allow_pyramiding": config.allow_pyramiding,
            "max_pyramid_fraction": config.max_pyramid_fraction,
        },
        trade_ledger=trade_ledger,
        equity_curve=equity_curve,
        stats=stats,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _run_signals(
    regime: str,
    bars: List[OHLCVBar],
    bar_date: date,
    config: BacktestConfig,
) -> List[RawSignal]:
    signals: List[RawSignal] = []
    sr_data = compute_sr_levels(bars) if regime == "RANGE" else None

    if regime in ("TREND_UP", "TREND_DOWN"):
        for fn_result in (
            detect_ma_cross(bars, bar_date, fast_period=config.fast_ma, slow_period=config.slow_ma),
            detect_n_day_breakout(bars, bar_date, n=config.breakout_n),
            detect_midtrend_entry(bars, bar_date, regime=regime, slow_ma_period=config.slow_ma),
        ):
            if fn_result:
                signals.append(fn_result)
    elif regime == "RANGE" and sr_data:
        sig = detect_sr_signal(bars, bar_date, sr_data)
        if sig:
            signals.append(sig)
    else:
        for fn_result in (
            detect_ma_cross(bars, bar_date, fast_period=config.fast_ma, slow_period=config.slow_ma),
            detect_n_day_breakout(bars, bar_date, n=config.breakout_n),
        ):
            if fn_result:
                signals.append(fn_result)

    return signals


def _best_confirmed(
    signals: List[RawSignal],
    bars: List[OHLCVBar],
    regime: str,
    rsi: Optional[float],
    k_delay: int,
) -> Optional[ConfirmationResult]:
    if not signals:
        return None
    results = [confirm(s, bars, regime, rsi, k_delay) for s in signals]
    accepted = [r for r in results if r.accepted]
    return max(accepted, key=lambda r: r.final_confidence) if accepted else None


def _maybe_pyramid(
    pos: _Position,
    bars_so_far: List[OHLCVBar],
    bar: OHLCVBar,
    regime: str,
    atr: Optional[float],
    swings: Any,
    sr_data: Any,
    rsi: Optional[float],
    equity: float,
    config: BacktestConfig,
) -> float:
    """F-043 — attempt a guarded pyramid add while holding a winner.

    Returns the equity delta (the add's commission, or 0.0 when no add is made)
    and mutates ``pos`` in place: shares grow, entry_price is re-blended to the
    weighted average, and the stop is tightened (never widened).
    """
    if pos.state == "FLAT" or pos.entry_price is None or pos.stop is None or not atr:
        return 0.0

    # Only same-direction, confirmed continuation signals justify an add.
    same_dir = [s for s in _run_signals(regime, bars_so_far, bar.date, config)
                if s.direction == pos.direction]
    best = _best_confirmed(same_dir, bars_so_far, regime, rsi, config.k_delay)
    if not best:
        return 0.0

    entry_fill = apply_slippage(bar.close, pos.direction, config.slippage_bps)
    stop_res = compute_initial_stop(
        direction=pos.direction, entry_price=entry_fill,
        atr=atr, swings=swings, sr_levels=sr_data,
    )
    size_res = compute_size(
        entry_price=entry_fill, stop_price=stop_res.stop_price,
        equity=equity, risk_pct=config.risk_per_trade_pct, atr=atr,
    )
    decision = evaluate_pyramid(
        direction=pos.direction,
        entry_price=pos.entry_price,
        current_close=bar.close,
        current_stop=pos.stop,
        initial_shares=pos.initial_shares,
        pyramided_shares=pos.pyramided_shares,
        proposed_add_shares=size_res.shares,
        proposed_add_stop=stop_res.stop_price,
        max_pyramid_fraction=config.max_pyramid_fraction,
    )
    if not decision.allowed or decision.add_shares <= 0:
        return 0.0

    total = pos.shares + decision.add_shares
    pos.entry_price = (pos.entry_price * pos.shares + entry_fill * decision.add_shares) / total
    pos.shares = total
    pos.pyramided_shares += decision.add_shares
    if decision.new_stop is not None:
        pos.stop = decision.new_stop

    # Backlog #80: the add pays the proportional cost too, and it joins the
    # position's entry cost so the round trip stays reconciled.
    add_cost = _side_cost(entry_fill, decision.add_shares, pos.direction, config)
    pos.entry_cost += add_cost
    return -add_cost


def _check_exit(
    bar: OHLCVBar,
    pos: _Position,
) -> tuple:
    """Return (exited: bool, exit_price: Optional[float], reason: str)."""
    if pos.state == "FLAT":
        return False, None, ""

    if pos.direction == "LONG":
        if pos.stop and bar.low <= pos.stop:
            return True, pos.stop, "STOP_HIT"
        if pos.target and bar.high >= pos.target:
            return True, pos.target, "TARGET_HIT"

    if pos.direction == "SHORT":
        if pos.stop and bar.high >= pos.stop:
            return True, pos.stop, "STOP_HIT"
        if pos.target and bar.low <= pos.target:
            return True, pos.target, "TARGET_HIT"

    return False, None, ""


def _side_cost(price: float, shares: int, side: str, config: "BacktestConfig") -> float:
    """Money cost of one side, from the config's proportional model."""
    return trade_cost(
        notional=price * shares,
        side=side,
        commission_pct=config.commission_pct,
        sell_tax_pct=config.sell_tax_pct,
        flat_fee=config.commission,
    )


def _close_trade(
    pos: _Position,
    ticker: str,
    exit_date: date,
    exit_price: float,
    exit_reason: str,
    exit_cost: float,
) -> TradeRecord:
    assert pos.entry_price is not None
    if pos.direction == "LONG":
        gross_pnl = (exit_price - pos.entry_price) * pos.shares
    else:
        gross_pnl = (pos.entry_price - exit_price) * pos.shares
    # Backlog #80: the ledger's `commission` is the ROUND TRIP cost.
    #
    # It used to be the exit leg only, while equity was separately charged
    # the entry leg — so `total_commission` reported half the fees actually
    # paid and `total_net_pnl` was overstated by one leg per trade. On the
    # default config that was a 1,490 gap between the equity curve and the
    # headline net on a 151-trade replay. The two now reconcile exactly.
    commission = pos.entry_cost + exit_cost
    net_pnl = gross_pnl - commission
    return TradeRecord(
        ticker=ticker,
        direction=pos.direction or "",
        entry_date=pos.entry_date or exit_date,
        entry_price=round(pos.entry_price, 4),
        exit_date=exit_date,
        exit_price=round(exit_price, 4),
        shares=pos.shares,
        gross_pnl=round(gross_pnl, 2),
        commission=commission,
        net_pnl=round(net_pnl, 2),
        exit_reason=exit_reason,
        entry_regime=pos.entry_regime,
    )


def _compute_stats(
    trades: List[TradeRecord],
    equity_curve: List[EquityPoint],
) -> BacktestStats:
    closed = [t for t in trades if t.net_pnl is not None]
    num_trades = len(closed)
    wins = [t for t in closed if (t.net_pnl or 0) > 0]
    losses = [t for t in closed if (t.net_pnl or 0) <= 0]

    win_rate = len(wins) / num_trades if num_trades else 0.0
    total_gross = sum(t.gross_pnl or 0 for t in closed)
    total_commission = sum(t.commission for t in closed)
    total_net = sum(t.net_pnl or 0 for t in closed)
    expectancy = total_net / num_trades if num_trades else 0.0

    max_dd = max((p.drawdown_pct for p in equity_curve), default=0.0)

    gross_wins = sum(t.gross_pnl or 0 for t in wins)
    gross_losses = abs(sum(t.gross_pnl or 0 for t in losses))
    profit_factor = round(gross_wins / gross_losses, 3) if gross_losses else None

    # Simplified Sharpe: mean daily return / std (equity curve changes)
    sharpe = None
    if len(equity_curve) > 2:
        daily_rets = [
            (equity_curve[i].equity - equity_curve[i - 1].equity) / equity_curve[i - 1].equity
            for i in range(1, len(equity_curve))
            if equity_curve[i - 1].equity > 0
        ]
        if len(daily_rets) > 1:
            mean_ret = statistics.mean(daily_rets)
            std_ret = statistics.stdev(daily_rets)
            if std_ret > 0:
                sharpe = round(mean_ret / std_ret * math.sqrt(252), 3)

    return BacktestStats(
        num_trades=num_trades,
        num_wins=len(wins),
        win_rate=round(win_rate, 4),
        total_gross_pnl=round(total_gross, 2),
        total_commission=round(total_commission, 2),
        total_net_pnl=round(total_net, 2),
        max_drawdown_pct=round(max_dd, 4),
        expectancy=round(expectancy, 2),
        sharpe_ratio=sharpe,
        profit_factor=profit_factor,
    )


def _empty_stats() -> BacktestStats:
    return BacktestStats(
        num_trades=0, num_wins=0, win_rate=0.0,
        total_gross_pnl=0.0, total_commission=0.0, total_net_pnl=0.0,
        max_drawdown_pct=0.0, expectancy=0.0, sharpe_ratio=None, profit_factor=None,
    )
