"""SQLAlchemy ORM models — ADR-001 §3."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DECIMAL, JSON, Boolean, Column, Date, DateTime, Enum, Integer,
    String, UniqueConstraint, BigInteger, func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class UserRiskPrefs(Base):
    """One row per user; created lazily on first preference write."""
    __tablename__ = "user_risk_prefs"

    user_id = Column(BigInteger, primary_key=True, comment="from JWT; no FK")
    account_equity = Column(DECIMAL(18, 2), nullable=False, default=0)
    risk_per_trade_pct = Column(DECIMAL(5, 3), nullable=False, default=1.0)
    max_concurrent_positions = Column(Integer, nullable=False, default=5)
    max_correlation = Column(DECIMAL(4, 3), nullable=False, default=0.7)
    loss_streak_size_cut = Column(DECIMAL(4, 3), nullable=False, default=0.5)
    loss_streak_threshold = Column(Integer, nullable=False, default=3)
    journal_account_id = Column(BigInteger, nullable=True)  # F-170: linked journal account
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class PositionState(Base):
    """One row per (user_id, ticker) — v1 single-leg limit."""
    __tablename__ = "position_states"
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_position_user_ticker"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    ticker = Column(String(16), nullable=False)
    state = Column(
        Enum("FLAT", "LONG", "SHORT", name="position_state_enum"),
        nullable=False,
        default="FLAT",
    )
    entry_bar_date = Column(Date, nullable=True)
    entry_price = Column(DECIMAL(18, 4), nullable=True)
    position_size = Column(Integer, nullable=False, default=0)
    current_stop = Column(DECIMAL(18, 4), nullable=True)
    current_target = Column(DECIMAL(18, 4), nullable=True)
    entry_signal_kind = Column(String(64), nullable=True)
    last_decision_run_id = Column(BigInteger, nullable=True)
    journal_trade_id = Column(BigInteger, nullable=True)  # F-170: journal-service trade id
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class SignalHistory(Base):
    """Append-only signal log for backtest replay."""
    __tablename__ = "signal_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(16), nullable=False, index=True)
    bar_date = Column(Date, nullable=False, index=True)
    signal_kind = Column(String(64), nullable=False)
    direction = Column(Enum("LONG", "SHORT", name="signal_direction_enum"), nullable=False)
    raw_confidence = Column(DECIMAL(4, 3), nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)
    confirmation_reason = Column(String(255), nullable=True)
    regime = Column(
        Enum("TREND_UP", "TREND_DOWN", "RANGE", "UNDEFINED", name="regime_enum"),
        nullable=False,
    )
    features_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class HelperWatchlist(Base):
    """Per-user tickers to run daily scheduled recommendations (F-070)."""
    __tablename__ = "helper_watchlists"
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_watchlist_user_ticker"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    ticker = Column(String(16), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class DecisionRun(Base):
    """One row per (user, ticker, bar, trigger) — persisted recommendation."""
    __tablename__ = "decision_runs"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "ticker", "bar_date", "trigger",
            name="uq_decision_run_key",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    ticker = Column(String(16), nullable=False, index=True)
    bar_date = Column(Date, nullable=False, index=True)
    trigger = Column(
        Enum("SCHEDULED", "ON_DEMAND", "BACKTEST", name="trigger_enum"),
        nullable=False,
    )
    regime = Column(
        Enum("TREND_UP", "TREND_DOWN", "RANGE", "UNDEFINED", name="regime_run_enum"),
        nullable=True,
    )
    signal_kind = Column(String(64), nullable=True)
    signal_confirmed = Column(Boolean, nullable=False, default=False)
    failed_signal_kind = Column(String(64), nullable=True)
    action = Column(
        Enum(
            "BUY", "SELL", "SELL_SHORT", "COVER", "HOLD", "WAIT", "REVERSE",
            name="action_enum",
        ),
        nullable=False,
    )
    state_before = Column(
        Enum("FLAT", "LONG", "SHORT", name="state_before_enum"), nullable=False
    )
    state_after = Column(
        Enum("FLAT", "LONG", "SHORT", name="state_after_enum"), nullable=False
    )
    entry_price = Column(DECIMAL(18, 4), nullable=True)
    stop_price = Column(DECIMAL(18, 4), nullable=True)
    target_price = Column(DECIMAL(18, 4), nullable=True)
    position_size = Column(Integer, nullable=True)
    reason_chain_json = Column(JSON, nullable=True)
    confidence = Column(DECIMAL(4, 3), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    # F-160..F-163 — outcome tagging (Phase Q)
    outcome = Column(String(12), nullable=True)           # WIN | LOSS | BREAKEVEN
    r_multiple = Column(DECIMAL(8, 3), nullable=True)     # signed R on entry runs
    exit_run_id = Column(BigInteger, nullable=True)       # closing run id (on entry run)
    exit_price = Column(DECIMAL(18, 4), nullable=True)    # actual exit price (on entry run)
    # F-190..F-193 — AI trade review (Phase T)
    ai_review = Column(String(2000), nullable=True)       # LLM post-mortem text


# ---------------------------------------------------------------------------
# FR-SCAN-SCHED / FR-SCAN-API — persisted momentum scans (S-3)
# ---------------------------------------------------------------------------

class ScannerRun(Base):
    """One momentum scan, persisted.

    WITHOUT THIS TABLE VT-5 IS UNFALSIFIABLE, which is the only reason it
    exists. The forward evaluation compares what the scanner said on an evening
    against what happened next; a scan that is recomputed later is a scan run
    with hindsight over a revised series. The row is the commitment.

    `scan_date` is unique: one authoritative scan per trading day. A re-run for
    the same day replaces it rather than accumulating variants, so "what did the
    scanner say on the 6th" has exactly one answer.
    """
    __tablename__ = "scanner_runs"
    __table_args__ = (UniqueConstraint("scan_date", name="uq_scanner_run_date"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    scan_date = Column(Date, nullable=False, index=True)
    trigger = Column(
        Enum("SCHEDULED", "ON_DEMAND", name="scanner_trigger_enum"), nullable=False
    )
    universe_total = Column(Integer, nullable=False, default=0)
    required_bars = Column(Integer, nullable=False, default=0)
    ranked_universe = Column(Integer, nullable=False, default=0)
    candidate_count = Column(Integer, nullable=False, default=0)
    #: The funnel buckets, as `accounting()` reports them. Stored so a later
    #: reader can see WHERE the universe went without re-running anything.
    accounting = Column(JSON, nullable=True)
    #: Every threshold in force. A candidate list means nothing without the
    #: settings that produced it, and the defaults will change (#135, #136).
    config = Column(JSON, nullable=True)
    #: The VT-4 random-walk false-positive rate for THIS run's thresholds.
    #:
    #: Stored on the run rather than recomputed per request because C4/EC-S5
    #: require the candidate list to be reported BESIDE it, and a reader who has
    #: to ask for it separately will not. Computed once nightly; null only when
    #: a cheap on-demand run skipped it, and then the API says so rather than
    #: omitting the field.
    null_fpr = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ScannerResult(Base):
    """One row per symbol EVALUATED, candidate or not.

    Rejections are persisted alongside passes on purpose. FR-SCAN-API's
    per-symbol diagnostic exists so a user who expected a name can learn which
    clause rejected it; storing only the winners would make that endpoint a
    404 for every question anyone actually asks.
    """
    __tablename__ = "scanner_results"
    __table_args__ = (
        UniqueConstraint("run_id", "symbol", name="uq_scanner_result_symbol"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, nullable=False, index=True)
    scan_date = Column(Date, nullable=False, index=True)
    symbol = Column(String(16), nullable=False, index=True)
    verdict = Column(
        Enum(
            "CANDIDATE", "QUALIFIED_BEYOND_CUT", "FAILED_BASE", "FAILED_TREND",
            "ILLIQUID", "PRICE_SEAM", "SHORT_HISTORY", "NO_BARS",
            name="scanner_verdict_enum",
        ),
        nullable=False,
        index=True,
    )
    rank = Column(Integer, nullable=True)
    composite = Column(DECIMAL(6, 4), nullable=True)
    #: Horizon returns, percentiles, trend clauses, base geometry, squeeze
    #: ratios, MA distances, pivot and liquidity — the whole evidence payload.
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
