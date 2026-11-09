"""S-3 — load the universe, run the scan, persist the result.

FR-SCAN-SCHED and the write half of FR-SCAN-API. The pure funnel in `screen.py`
knows nothing about HTTP or the database; this module is the only place the two
meet, which is what keeps the determinism harness (VT-2) able to run offline.

WHY EVERY EVALUATED SYMBOL IS PERSISTED, NOT ONLY THE WINNERS. The per-symbol
diagnostic in FR-SCAN-API exists so a user who expected a name can learn which
clause rejected it. Storing passes alone would make that endpoint a 404 for
every question anyone actually asks, and would also lose the funnel counts that
make an empty list legible rather than alarming (#135).
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, replace
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import ScannerResult, ScannerRun
from app.services.scanner.null_model import estimate_null_fpr
from app.services.scanner.screen import ScanCandidate, ScanConfig, ScanReport, run_scan
from app.services.signal.base import OHLCVBar

logger = logging.getLogger(__name__)

#: Calendar days of history pulled per symbol. The funnel needs 200 BARS
#: (SMA200), and VN trades ~250 sessions a year, so 600 calendar days leaves
#: roughly 410 bars — enough for the longest base to sit entirely inside the
#: window with room over the SMA200 warm-up.
HISTORY_DAYS = 600

#: Concurrent OHLCV fetches. stock-data-service reads MySQL for these (no
#: vnstock quota), but 93 simultaneous requests would still queue behind its
#: connection pool and time out under `MARKET_GATEWAY_TIMEOUT_MS`.
FETCH_CONCURRENCY = 8


async def load_universe_bars(
    client,
    symbols: Sequence[str],
    as_of: date,
    *,
    days: int = HISTORY_DAYS,
    concurrency: int = FETCH_CONCURRENCY,
) -> Dict[str, List[OHLCVBar]]:
    """Fetch bars for every symbol, tolerating per-symbol failure.

    A symbol whose fetch fails lands in the result as an EMPTY list rather than
    being dropped, so the funnel counts it under `excluded_no_bars` and the
    accounting still balances. Silently omitting it would make a fetch outage
    look like a small universe.
    """
    sem = asyncio.Semaphore(concurrency)

    async def one(symbol: str) -> tuple[str, List[OHLCVBar]]:
        async with sem:
            try:
                raw = await client.fetch_ohlcv(symbol, days=days, end_date=as_of)
            except Exception as exc:                      # noqa: BLE001
                logger.warning("scanner: fetch_ohlcv %s failed: %s", symbol, exc)
                return symbol, []
        bars: List[OHLCVBar] = []
        for row in raw:
            try:
                bars.append(OHLCVBar.from_dict(row))
            except (KeyError, TypeError, ValueError):
                continue
        return symbol, bars

    pairs = await asyncio.gather(*[one(s) for s in symbols])
    return {sym: bars for sym, bars in pairs}


# ---------------------------------------------------------------------------
# Serialisation — the evidence payload stored per symbol
# ---------------------------------------------------------------------------

def _clauses(obj: Any) -> List[Dict[str, Any]]:
    return [
        {"name": c.name, "passed": c.passed, "detail": c.detail}
        for c in getattr(obj, "clauses", ())
    ]


def candidate_detail(c: ScanCandidate) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "momentum": {
            "returns": {str(k): v for k, v in c.momentum.returns.items()},
            "percentiles": {str(k): v for k, v in c.momentum.percentiles.items()},
            "composite": c.momentum.composite,
            # Travels with the percentiles on purpose: 0.95 over 93 names and
            # over 1,600 are different claims (FR-SCAN-MOM).
            "ranked_universe": c.momentum.ranked_universe,
        },
        "trend": {
            "passed": c.trend.passed,
            "close": c.trend.close,
            "sma50": c.trend.sma_fast,
            "sma200": c.trend.sma_slow,
            "prior_advance_pct": c.trend.prior_advance_pct,
            "clauses": _clauses(c.trend),
        },
        "liquidity": {
            "avg_daily_value": c.liquidity.avg_daily_value,
            "avg_daily_volume": c.liquidity.avg_daily_volume,
            "lookback": c.liquidity.lookback,
            "reason": c.liquidity.reason,
        },
    }
    if c.base is not None:
        out["base"] = {
            "passed": c.base.passed,
            "clauses": _clauses(c.base),
            "window": asdict(c.base.window) if c.base.window else None,
            "squeeze": asdict(c.base.squeeze) if c.base.squeeze else None,
            "moving_averages": asdict(c.base.moving_averages) if c.base.moving_averages else None,
            "pivot": asdict(c.base.pivot) if c.base.pivot else None,
        }
    return out


def _rows(report: ScanReport) -> List[Dict[str, Any]]:
    """Every evaluated symbol as a persistable row, one verdict each."""
    rows: List[Dict[str, Any]] = []
    for c in report.candidates:
        rows.append({"symbol": c.symbol, "verdict": "CANDIDATE", "rank": c.rank,
                     "composite": c.momentum.composite, "detail": candidate_detail(c)})
    for sym in report.excess_qualified:
        rows.append({"symbol": sym, "verdict": "QUALIFIED_BEYOND_CUT", "rank": None,
                     "composite": None,
                     "detail": {"note": "passed every stage but fell outside max_candidates"}})
    for b in report.failed_base:
        rows.append({"symbol": b.symbol, "verdict": "FAILED_BASE", "rank": None,
                     "composite": None,
                     "detail": {"base": {"passed": False, "clauses": _clauses(b),
                                         "window": asdict(b.window) if b.window else None,
                                         "squeeze": asdict(b.squeeze) if b.squeeze else None,
                                         "moving_averages": asdict(b.moving_averages) if b.moving_averages else None,
                                         "pivot": asdict(b.pivot) if b.pivot else None},
                                "failed_clauses": list(b.failed_clauses())}})
    for t in report.failed_trend:
        rows.append({"symbol": t.symbol, "verdict": "FAILED_TREND", "rank": None,
                     "composite": None,
                     "detail": {"trend": {"passed": False, "close": t.close,
                                          "sma50": t.sma_fast, "sma200": t.sma_slow,
                                          "prior_advance_pct": t.prior_advance_pct,
                                          "clauses": _clauses(t)},
                                "failed_clauses": list(t.failed_clauses())}})
    for l in report.excluded_illiquid:
        rows.append({"symbol": l.ticker, "verdict": "ILLIQUID", "rank": None,
                     "composite": None,
                     "detail": {"liquidity": {"avg_daily_value": l.avg_daily_value,
                                              "avg_daily_volume": l.avg_daily_volume,
                                              "lookback": l.lookback, "reason": l.reason}}})
    for s in report.excluded_price_seam:
        rows.append({"symbol": s.symbol, "verdict": "PRICE_SEAM", "rank": None,
                     "composite": None,
                     "detail": {"seam": asdict(s),
                                "remedy": "POST /stocks/{symbol}/repair-history"}})
    for sym in report.excluded_insufficient_history:
        rows.append({"symbol": sym, "verdict": "SHORT_HISTORY", "rank": None,
                     "composite": None,
                     "detail": {"required_bars": report.required_bars}})
    for sym in report.excluded_no_bars:
        rows.append({"symbol": sym, "verdict": "NO_BARS", "rank": None,
                     "composite": None,
                     "detail": {"note": "no bars at or before the scan date"}})
    return rows


def config_payload(cfg: ScanConfig) -> Dict[str, Any]:
    """Every threshold in force. A candidate list is uninterpretable without
    them, and the defaults are expected to move (#135, #136)."""
    return {
        "horizons": list(cfg.horizons),
        "horizon_weights": ({str(k): v for k, v in cfg.horizon_weights.items()}
                            if cfg.horizon_weights else None),
        "min_bars": cfg.min_bars,
        "liquidity_lookback": cfg.liquidity_lookback,
        "min_avg_daily_value": cfg.min_avg_daily_value,
        "min_avg_daily_volume": cfg.min_avg_daily_volume,
        "price_unit_vnd": cfg.price_unit_vnd,
        "min_prior_advance_pct": cfg.min_prior_advance_pct,
        "advance_lookback": cfg.advance_lookback,
        "max_candidates": cfg.max_candidates,
        "seam_max_move_pct": cfg.seam_max_move_pct,
        "seam_allowlist": sorted(cfg.seam_allowlist),
        "require_base": cfg.require_base,
        "base_min_bars": cfg.base_min_bars,
        "base_max_bars": cfg.base_max_bars,
        "base_max_depth_pct": cfg.base_max_depth_pct,
        "base_max_drift_pct": cfg.base_max_drift_pct,
        "base_max_drift_over_depth": cfg.base_max_drift_over_depth,
        "squeeze_max_ratio": cfg.squeeze_max_ratio,
        "dryup_max_ratio": cfg.dryup_max_ratio,
        "ma_proximity_pct": cfg.ma_proximity_pct,
    }


# ---------------------------------------------------------------------------
# Run + persist
# ---------------------------------------------------------------------------

async def persist_scan(
    db: AsyncSession,
    report: ScanReport,
    cfg: ScanConfig,
    *,
    trigger: str,
    latency_ms: Optional[int] = None,
    null_fpr: Optional[Dict[str, Any]] = None,
) -> ScannerRun:
    """Write one authoritative scan for `report.as_of`, replacing any earlier one.

    Replace rather than append: "what did the scanner say on the 6th" must have
    exactly one answer, or VT-5 gets to choose which variant supports it.
    """
    existing = (await db.execute(
        select(ScannerRun).where(ScannerRun.scan_date == report.as_of)
    )).scalar_one_or_none()
    if existing is not None:
        await db.execute(delete(ScannerResult).where(ScannerResult.run_id == existing.id))
        await db.delete(existing)
        await db.flush()

    run = ScannerRun(
        scan_date=report.as_of,
        trigger=trigger,
        universe_total=report.universe_total,
        required_bars=report.required_bars,
        ranked_universe=report.ranked_universe,
        candidate_count=len(report.candidates),
        accounting=report.accounting(),
        config=config_payload(cfg),
        null_fpr=null_fpr,
        latency_ms=latency_ms,
    )
    db.add(run)
    await db.flush()

    for row in _rows(report):
        db.add(ScannerResult(
            run_id=run.id, scan_date=report.as_of, symbol=row["symbol"],
            verdict=row["verdict"], rank=row["rank"],
            composite=row["composite"], detail=row["detail"],
        ))
    await db.commit()
    return run


async def run_momentum_scan(
    db: AsyncSession,
    client,
    *,
    as_of: Optional[date] = None,
    config: Optional[ScanConfig] = None,
    trigger: str = "ON_DEMAND",
    with_null_fpr: bool = False,
    null_trials: int = 30,
) -> tuple[ScanReport, ScannerRun]:
    """Fetch, scan, persist. Returns the live report and its stored row."""
    cfg = config or ScanConfig()
    scan_date = as_of or date.today()
    t0 = time.time()

    symbols = await client.fetch_universe()
    bars = await load_universe_bars(client, symbols, scan_date)
    report = run_scan(bars, scan_date, cfg)

    null_payload: Optional[Dict[str, Any]] = None
    if with_null_fpr and symbols:
        n = estimate_null_fpr(
            run_scan, cfg, trials=null_trials,
            universe_size=len(symbols), bars_per_symbol=400,
        )
        null_payload = {
            "trials": n.trials, "universe_size": n.universe_size,
            "bars_per_symbol": n.bars_per_symbol,
            "trials_with_candidates": n.trials_with_candidates,
            "total_candidates": n.total_candidates,
            "symbols_tested": n.symbols_tested,
            "trial_fpr": n.trial_fpr, "symbol_fpr": n.symbol_fpr,
        }

    latency = int((time.time() - t0) * 1000)
    run = await persist_scan(db, report, cfg, trigger=trigger,
                             latency_ms=latency, null_fpr=null_payload)
    logger.info(
        "momentum scan %s: %d/%d candidates from %d ranked (%dms)",
        scan_date, len(report.candidates), report.universe_total,
        report.ranked_universe, latency,
    )
    return report, run
