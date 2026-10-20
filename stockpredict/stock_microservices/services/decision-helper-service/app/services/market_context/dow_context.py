"""EM-6 — adopting the primary trend only when a witness confirms it.

`FR-EM-D3`, `FR-EM-D4`, `FR-EM-D5`. Design:
`docs/SRS_edwards_magee_dow_gate.md`; composition:
`docs/implementation_plan_em6_dow_gate.md` §1.

The rule
--------
E&M's tenet 8 — *"no valid trend-change signal from one average alone"*, and
*"they need not confirm on the same day"* — joined to tenet 12, *"a trend is
assumed to continue until reversal is definitely signalled"*:

* a **turn** in the lead index is a *proposal*, not a fact;
* it is **adopted** at the bar a witness reaches the same state, within `k`
  bars of the turn;
* if no witness does, the turn is **not adopted and the previous trend
  stands** — which is tenet 12, not a special case invented here.

Why `k` exists at all
---------------------
E&M place no limit on how late an average may confirm. A literal reading would
therefore adopt almost every turn eventually, and the witness study measured
exactly that: HNXINDEX confirms **98%** of VNINDEX turns within 120 bars
(median 2). An unbounded window would make the gate nearly inert, so `k`
bounds the proposal's life, and once it lapses the signal is stale — a witness
turning up long afterwards is not a confirmation of a turn that has passed.
That is a design decision taken from a measurement, and `D6` sweeps it.

The witness set is a measurement, not a preference
---------------------------------------------------
See `EXCLUDED_INDICES`. VN30 is the one the register expected to use and the
one the data rules out.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type
from typing import Dict, List, Optional, Sequence, Tuple

from app.services.market_context.dow import (
    TREND_UP,
    UNDEFINED,
    swing_trend_series,
)
from app.services.signal.base import OHLCVBar

#: The symbol's own market. The universe is HOSE-listed, so VNINDEX leads;
#: `EC-D4` requires this to follow the symbol's exchange if that ever widens.
LEAD_INDEX = "VNINDEX"

#: Pairwise 0.45-0.47 with the lead and with each other, across three
#: exchanges — the closest this market offers to Industrials-vs-Transports.
WITNESS_INDICES: Tuple[str, ...] = ("HNXINDEX", "UPCOMINDEX")

#: Rejected by measurement, with the measurement kept here so the next reader
#: does not re-litigate it from intuition (`tests/em6_witness_study.py`).
EXCLUDED_INDICES: Dict[str, str] = {
    "VN30": (
        "daily-return correlation 0.965 with VNINDEX — the same instrument "
        "under a second name; disagreements have a median length of 2 bars "
        "and it confirms a VNINDEX turn with a median lag of 0 bars, 99% of "
        "the time. A witness that agrees with everything gates nothing."
    ),
    "HNX30": (
        "daily-return correlation 0.887 with HNXINDEX — a redundant subset "
        "of a witness already in the set."
    ),
}

#: Provisional per `FR-EM-D10`; `D6` sweeps it. The witness study's median
#: confirmation lag is 0-5 bars, so this admits the typical case without
#: reaching the 120-bar horizon at which the gate is inert.
DEFAULT_LAG_BARS = 5

#: A witness quiet for longer than this is treated as absent rather than
#: allowed to vote with an old reading. Sized for Tết, which closes VN
#: exchanges for about nine days.
DEFAULT_MAX_STALE_DAYS = 10

STATUS_OK = "OK"
STATUS_NO_WITNESS = "SKIP_NO_WITNESS"


class ExcludedWitnessError(ValueError):
    """Raised for an index the measurement rules out, or does not know."""


@dataclass(frozen=True)
class MarketContext:
    """One day's reading of the market, as the gate will see it."""
    date: date_type
    lead_trend: str
    adopted_trend: str
    agreeing: Tuple[str, ...]
    disagreeing: Tuple[str, ...]
    pending_turn: Optional[str]
    status: str


def validate_witness_codes(codes: Sequence[str], *,
                           allow_excluded: bool = False) -> None:
    """`EC-D5` — indices are addressed from the allow-list, never guessed."""
    for code in codes:
        if code in WITNESS_INDICES:
            continue
        if code in EXCLUDED_INDICES:
            if allow_excluded:
                continue
            raise ExcludedWitnessError(
                f"{code} is excluded as a witness: {EXCLUDED_INDICES[code]} "
                f"Pass allow_excluded=True only to measure it deliberately."
            )
        raise ExcludedWitnessError(
            f"{code} is not a known index. Witnesses must come from "
            f"{WITNESS_INDICES!r}."
        )


def adopt_turns(lead_trend: Sequence[str],
                witness_trends: Dict[str, Sequence[Optional[str]]],
                k: Optional[int] = None,
                required: int = 1) -> List[str]:
    """The confirmation rule, over trend series already aligned to one calendar.

    `witness_trends` values carry `None` where a witness is unavailable on
    that bar. Separated from `market_context_series` because this is the
    subtle half and deserves to be tested on literal sequences.
    """
    window = DEFAULT_LAG_BARS if k is None else k

    adopted = UNDEFINED
    pending: Optional[Tuple[str, int]] = None   # (proposed state, deadline)
    previous: Optional[str] = None
    out: List[str] = []

    for i, current in enumerate(lead_trend):
        turned = (previous is not None and current != previous) or (
            previous is None and current != UNDEFINED
        )
        if turned:
            pending = (current, i + window)
        previous = current

        if pending is not None:
            proposed, deadline = pending
            if proposed == adopted:
                pending = None                      # nothing left to adopt
            elif i <= deadline:
                available = [t[i] for t in witness_trends.values()
                             if t[i] is not None]
                if not available:
                    adopted = proposed              # EC-D1: fail open
                    pending = None
                else:
                    agreeing = sum(1 for t in available if t == proposed)
                    # Ask only the witnesses that are reporting: demanding
                    # absent ones would suppress on an outage, which is
                    # EC-D1's failure mode wearing a different hat.
                    if agreeing >= min(required, len(available)):
                        adopted = proposed
                        pending = None
            else:
                pending = None                      # stale: the turn lapses

        out.append(adopted)

    return out


def _align_to_lead(lead: Sequence[OHLCVBar],
                   witness: Sequence[OHLCVBar],
                   trends: Sequence[str],
                   max_stale_days: int) -> List[Optional[str]]:
    """`EC-D2` — the witness's reading as of each lead date.

    `None` before the witness's first bar (it had not listed), and `None`
    again once its last bar is older than `max_stale_days`, which routes it
    into `EC-D1` instead of letting a months-old reading vote.
    """
    mapped: List[Optional[str]] = []
    j = -1
    for bar in lead:
        while j + 1 < len(witness) and witness[j + 1].date <= bar.date:
            j += 1
        if j < 0:
            mapped.append(None)
            continue
        gap = (bar.date - witness[j].date).days
        mapped.append(None if gap > max_stale_days else trends[j])
    return mapped


def market_context_series(lead: Sequence[OHLCVBar],
                          witnesses: Dict[str, Sequence[OHLCVBar]],
                          *,
                          k: Optional[int] = None,
                          required: int = 1,
                          pct: Optional[float] = None,
                          max_stale_days: Optional[int] = None,
                          allow_excluded: bool = False) -> List[MarketContext]:
    """One `MarketContext` per lead bar, causally.

    With no witness available the lead's own trend is adopted unchanged
    (`EC-D1`): a data outage must never be able to look like a quiet market,
    because that failure would silently suppress every signal.
    """
    validate_witness_codes(list(witnesses), allow_excluded=allow_excluded)
    if not lead:
        return []

    stale_limit = DEFAULT_MAX_STALE_DAYS if max_stale_days is None else max_stale_days

    lead_trend = swing_trend_series(lead, pct=pct)
    aligned: Dict[str, List[Optional[str]]] = {
        code: _align_to_lead(lead, bars, swing_trend_series(bars, pct=pct),
                             stale_limit)
        for code, bars in witnesses.items()
    }
    adopted = adopt_turns(lead_trend, aligned, k=k, required=required)

    out: List[MarketContext] = []
    for i, bar in enumerate(lead):
        agreeing = tuple(code for code, t in aligned.items()
                         if t[i] is not None and t[i] == lead_trend[i])
        disagreeing = tuple(code for code, t in aligned.items()
                            if t[i] is not None and t[i] != lead_trend[i])
        any_available = bool(agreeing or disagreeing)
        out.append(MarketContext(
            date=bar.date,
            lead_trend=lead_trend[i],
            adopted_trend=adopted[i],
            agreeing=agreeing,
            disagreeing=disagreeing,
            pending_turn=(lead_trend[i] if lead_trend[i] != adopted[i] else None),
            status=STATUS_OK if any_available else STATUS_NO_WITNESS,
        ))
    return out


__all__ = [
    "DEFAULT_LAG_BARS",
    "DEFAULT_MAX_STALE_DAYS",
    "EXCLUDED_INDICES",
    "LEAD_INDEX",
    "WITNESS_INDICES",
    "ExcludedWitnessError",
    "MarketContext",
    "TREND_UP",
    "adopt_turns",
    "market_context_series",
    "validate_witness_codes",
]
