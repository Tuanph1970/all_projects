"""services/ CallScorer — marks every stored TCBS call to market (FR-BM-SCORE, EC-B7).

A call sitting in `tcb_news_reco` is an opinion. Scored at fixed horizons against both
the stock's own close and the index over the *same window*, it becomes a track record —
which is the only basis on which EC-B7 / CLAUDE.md C4 would ever let a broker field near
a decision.

Three rules the implementation exists to enforce:

1. **Horizons are sessions, not calendar days.** The price series' own dates are the
   trading calendar, so "20 sessions later" is a positional step, never a date + 28d
   guess that lands on a holiday.

2. **Never score an unfinished horizon.** If the 60th session after the call has not
   happened, `ret_60d` stays NULL. There is no "use the last available bar instead"
   fallback, because that silently shortens the horizon and flatters the desk.

3. **Index-relative uses the same window as absolute** (SRS §5.4). The excess return
   compares the stock's move between two specific dates with the index's move between
   *those same two dates* — not between the same two positions in the index's own
   series, which drift apart whenever the stock is halted.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.ingest.price_history import PriceHistorySource, PriceSeries, PriceUnavailableError

logger = logging.getLogger(__name__)

# The horizons SRS §3.8 fixes. Changing this list changes the table's columns.
HORIZONS: tuple[int, ...] = (1, 5, 20, 60)

# Enough history before the call to guarantee a reference bar even across a long holiday.
_LOOKBACK_DAYS = 21

# A 60-session horizon needs ~85 calendar days. Past this, a still-unscored call is a
# delisted or untracked symbol, not a pending one — stop retrying it every tick.
GIVE_UP_AFTER_DAYS = 200


@dataclass
class CallScore:
    """The outcome of scoring one call. Every return is a fraction (0.031 = +3.1%)."""

    ref_date: Optional[date] = None
    ref_close: Optional[float] = None
    returns: dict[int, Optional[float]] = field(default_factory=dict)
    excess: dict[int, Optional[float]] = field(default_factory=dict)
    adjusted: bool = False

    @property
    def complete(self) -> bool:
        """True once every horizon is filled — the call needs no further ticks."""
        return all(self.returns.get(h) is not None for h in HORIZONS)

    @property
    def any_scored(self) -> bool:
        return any(self.returns.get(h) is not None for h in HORIZONS)


def score_call(
    *,
    session_date: date,
    prices: PriceSeries,
    index: Optional[PriceSeries] = None,
    horizons: tuple[int, ...] = HORIZONS,
) -> CallScore:
    """Mark one call to market. Pure — no I/O, no clock.

    `session_date` is the session the mail described; its close is the reference price,
    because the mail is published after that close.
    """
    score = CallScore(returns={h: None for h in horizons},
                      excess={h: None for h in horizons},
                      adjusted=prices.adjusted)

    ref_i = prices.index_at_or_before(session_date)
    if ref_i is None:
        # The series starts after the call — nothing to price it against.
        return score
    ref_close = prices.closes[ref_i]
    if ref_close <= 0:
        return score
    score.ref_date = prices.dates[ref_i]
    score.ref_close = ref_close

    for h in horizons:
        j = ref_i + h
        if j >= len(prices):
            continue  # horizon not yet elapsed — stays None (rule 2)
        score.returns[h] = prices.closes[j] / ref_close - 1.0
        if index is not None:
            index_move = _index_return(index, score.ref_date, prices.dates[j])
            if index_move is not None:
                score.excess[h] = score.returns[h] - index_move
    return score


def _index_return(index: PriceSeries, start: date, end: date) -> Optional[float]:
    """The index's move between two calendar dates — rule 3's "same window".

    Returns None unless the index series actually *reaches* `end`. Without that guard
    an index that stops short silently measures its move over the days it does cover
    and reports it as the full-horizon benchmark — understating what the call had to
    beat, which is the precise failure rule 3 exists to prevent.
    """
    if not index.dates or index.dates[-1] < end:
        return None
    i, j = index.index_at_or_before(start), index.index_at_or_before(end)
    if i is None or j is None or j <= i:
        return None
    base = index.closes[i]
    if base <= 0:
        return None
    return index.closes[j] / base - 1.0


@dataclass
class ScoringResult:
    """What one tick did — surfaced by POST /news/tcb/score and the metrics log."""

    considered: int = 0
    scored: int = 0
    completed: int = 0
    gave_up: int = 0
    unavailable: list[str] = field(default_factory=list)


class CallScorer:
    """Scheduled job: score every call that has an unfilled, elapsed horizon."""

    def __init__(
        self,
        repo,
        price_source: PriceHistorySource,
        *,
        index_symbol: str = "VNINDEX",
        give_up_after_days: int = GIVE_UP_AFTER_DAYS,
    ):
        self._repo = repo
        self._prices = price_source
        self._index_symbol = index_symbol
        self._give_up_after_days = give_up_after_days

    async def tick(self, *, today: Optional[date] = None) -> dict:
        """One scoring pass. Never raises: a price outage defers, it does not fail."""
        today = today or datetime.now(timezone.utc).date()
        result = ScoringResult()

        pending = self._repo.list_unscored()
        result.considered = len(pending)
        if not pending:
            return _as_dict(result)

        # One index fetch covers every call in the batch.
        earliest = min(session_date for _, session_date in pending)
        index = self._fetch(self._index_symbol, earliest, today)
        if index is None:
            logger.warning("index %s unavailable; scoring absolute returns only",
                           self._index_symbol)

        for reco, session_date in pending:
            prices = self._fetch(reco.symbol, session_date, today)
            if prices is None:
                result.unavailable.append(reco.symbol)
                # Only give up once the window has long closed — a transient outage
                # must not permanently retire a call that is still scoreable.
                if (today - session_date).days > self._give_up_after_days:
                    self._repo.mark_scoring_done(reco.id)
                    result.gave_up += 1
                continue

            score = score_call(session_date=session_date, prices=prices, index=index)
            done = score.complete or (today - session_date).days > self._give_up_after_days
            self._repo.save_score(reco.id, score, scoring_done=done)
            if score.any_scored:
                result.scored += 1
            if score.complete:
                result.completed += 1
            elif done:
                result.gave_up += 1

        logger.info("call scoring tick: %s", _as_dict(result))
        return _as_dict(result)

    def _fetch(self, symbol: str, session_date: date, today: date) -> Optional[PriceSeries]:
        try:
            return self._prices.history(
                symbol, session_date - timedelta(days=_LOOKBACK_DAYS), today)
        except PriceUnavailableError as exc:
            logger.warning("prices unavailable for %s: %s", symbol, exc)
            return None


def _as_dict(r: ScoringResult) -> dict:
    return {
        "considered": r.considered,
        "scored": r.scored,
        "completed": r.completed,
        "gave_up": r.gave_up,
        "unavailable": sorted(set(r.unavailable)),
    }


# ---------------------------------------------------------------------------
# The record (FR-BM-RECORD, EC-B7)
# ---------------------------------------------------------------------------

# Only BUY and SELL assert a direction. HOLD and WATCH ("Chờ mua" — wait) make no
# directional claim, so counting them in a hit rate would invent a prediction the desk
# never made. They still get their mean returns reported, which IS the evidence for them.
DIRECTIONAL = {"BUY": 1, "SELL": -1}


def build_record(rows: list[tuple], *, min_calls: int) -> dict:
    """Aggregate scored calls into the desk's track record.

    `rows` are (action, {horizon: ret}, {horizon: excess}) triples.

    Every hit rate is reported beside the benchmark it must beat — what the same
    directional bet on the index over the same windows would have returned (C4/EC-B7).
    A method only "improves" if it beats that, which is why the two numbers always
    travel together rather than the hit rate being published alone.
    """
    scored = [r for r in rows if any(v is not None for v in r[1].values())]
    record = {
        "total_calls": len(rows),
        "scored_calls": len(scored),
        "min_calls": min_calls,
        "reportable": len(scored) >= min_calls,
        "horizons": {},
        "by_action": {},
    }
    if not record["reportable"]:
        return record

    for h in HORIZONS:
        abs_returns = [r[1][h] for r in scored if r[1].get(h) is not None]
        exc_returns = [r[2][h] for r in scored if r[2].get(h) is not None]
        directional = [r for r in scored
                       if r[0] in DIRECTIONAL and r[1].get(h) is not None]
        hits = [r for r in directional if r[1][h] * DIRECTIONAL[r[0]] > 0]
        # The benchmark: the same directional bet placed on the index instead. An
        # excess return is (stock - index), so index move = stock move - excess.
        benchmark = [r for r in directional if r[2].get(h) is not None
                     and (r[1][h] - r[2][h]) * DIRECTIONAL[r[0]] > 0]
        benchmark_n = [r for r in directional if r[2].get(h) is not None]

        record["horizons"][f"{h}d"] = {
            "n": len(abs_returns),
            "mean_return": _mean(abs_returns),
            "mean_excess_return": _mean(exc_returns),
            "directional_n": len(directional),
            "hit_rate": (len(hits) / len(directional)) if directional else None,
            "benchmark_hit_rate": (len(benchmark) / len(benchmark_n)) if benchmark_n else None,
        }

    for action in ("BUY", "SELL", "HOLD", "WATCH"):
        of_action = [r for r in scored if r[0] == action]
        if not of_action:
            continue
        record["by_action"][action] = {
            "n": len(of_action),
            "horizons": {
                f"{h}d": {
                    "n": len([r for r in of_action if r[1].get(h) is not None]),
                    "mean_return": _mean([r[1][h] for r in of_action if r[1].get(h) is not None]),
                    "mean_excess_return": _mean(
                        [r[2][h] for r in of_action if r[2].get(h) is not None]),
                }
                for h in HORIZONS
            },
        }
    return record


def _mean(values: list[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None
