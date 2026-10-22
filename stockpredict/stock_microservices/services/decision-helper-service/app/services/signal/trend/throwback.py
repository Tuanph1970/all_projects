"""EM-7 — the throwback entry at a broken boundary (`FR-EM-T2`..`T5`, `T8`).

E&M Ch 6 calls the return to a broken neckline *"the short-seller's second
chance and his stop-placement reference"*. Ch 13 says **why** it works, and
that sentence is the reason this module is anchored where it is:

> **Pattern resistance** — *the mechanism explains the patterns*: a broken
> H&S neckline becomes resistance; a rectangle's supply line becomes support
> once decisively exceeded. **Throwbacks to a pattern boundary need no
> 10%-away rule — a conclusive breakout is enough.**

So the boundary here is a **broken S/R level**, not a pattern neckline. That
is not a compromise forced by plumbing: a neckline works as resistance
*because* it is a broken support, so the level is the cause and the pattern
is a label on it. It also means this detector needs no pattern detector —
which matters, because `EM-8`'s `M3` found `MEASURED_MOVE` to be dead code for
exactly that dependency, reading a key no shipped detector ever supplied.

Ch 33 gives the tactic as **"whichever comes first"** of a pullback to the
line or a 40% recovery, which is `MODE_EITHER`. The two triggers are also
offered separately, because `EITHER` alone cannot say which half does the
work and combining them silently would make each unobservable — the `#83`
bug class.

What is measured, and what is not
----------------------------------
`T2`/Gate 1 measured the phenomenon on 92 symbols and 85,623 breaks: price
returns to a broken level **82.3%** of the time against a distance-matched
null of **72.3%**, and overshoots the old line by **0.23 ATR less**. Both of
E&M's claims hold, in 9 of 9 grid cells.

But that is a **ten-point edge on a 72% base**: price returns to a level it
merely sits half an ATR from nearly three times in four. So the detector
ships `OFF`, and `T4` decides whether it ever ships enabled — the `#82`
discipline, after the failed-signal override shipped on by default and
distorted every exit statistic computed afterwards.

**Confidence is a constant**, deliberately. `#70` is the warning against
hardcoded scores — but it was a warning against *ignoring evidence the
detector already measured*. Here Gate 1 measured which evidence relates to
the return: the level's touch count is a **whisper** (+2.3pp) and break
direction is larger (+4.5pp) but was reported as *descriptive only* and must
not become a scoring rule on the data that generated it. Inventing a
modulation now would be the unverified claim `CLAUDE.md` forbids, so the
evidence dict carries the raw facts and a later task can measure what should
weight them.
"""
from __future__ import annotations

import logging
from datetime import date as date_type
from typing import Any, Dict, List, Optional

from app.services.backtest.market_features import (
    atr_series,
    compute_sr_levels,
)
from app.services.signal.base import OHLCVBar, RawSignal

logger = logging.getLogger(__name__)

MODE_OFF = "OFF"
MODE_BAND = "BAND"
MODE_RETRACE = "RETRACE_40"
MODE_EITHER = "EITHER"

#: Mutually exclusive by design. See the module docstring.
THROWBACK_MODES = frozenset({MODE_OFF, MODE_BAND, MODE_RETRACE, MODE_EITHER})

#: Gate 1's primary setting — the configuration the effect was measured at
#: (`docs/em7_gate1.md`). Read in the body, never as a default argument, so a
#: sweep over it is not a silent no-op. Ninth instance of that trap.
DEFAULT_BAND_ATR = 0.5

#: `FR-EM-T5`. A second chance, not a standing offer.
DEFAULT_STALE_BARS = 60

#: E&M Ch 33's figure, and a 1940s NYSE one — a legitimate default, not a
#: measured result (`CLAUDE.md` rule 3). `T4` sweeps it.
DEFAULT_RETRACE_PCT = 0.40

#: Below this there is no level structure to speak of.
MIN_BARS = 40

#: Not modulated by anything yet, and the docstring says why.
BASE_CONFIDENCE = 0.50


def _candidates(sr: Dict[str, Any], bars: List[OHLCVBar], idx: int,
                stale: int) -> List[Dict[str, Any]]:
    """Levels broken recently, strictly before `idx`, nearest first.

    `EC-T5` and `EC-T2` both fall out of "strictly before": if a break is
    recorded ON this bar, price went *through* the level rather than stopping
    at it, which is a fresh break or a failed throwback — not an entry.
    """
    out: List[Dict[str, Any]] = []
    for group in ("supports", "resistances"):
        for lvl in sr.get(group, []):
            brk = lvl.get("breaks") or []
            if not brk:
                continue
            last = brk[-1]
            age = idx - int(last["bar_index"])
            if age <= 0 or age > stale:
                continue
            out.append({
                "price": float(lvl["price"]),
                "break_bar": int(last["bar_index"]),
                "break_direction": last["direction"],
                "bars_since_break": age,
                "touches": int(lvl.get("strength") or 1),
                "penetration_atr": float(last.get("penetration_atr") or 0.0),
            })
    close = bars[idx].close
    out.sort(key=lambda c: abs(c["price"] - close))
    return out


def _retraced(bars: List[OHLCVBar], idx: int, cand: Dict[str, Any],
              pct: float) -> bool:
    """Has price given back `pct` of the move the break produced?

    E&M: *"If the breakout continues for several days, compute the 40% on the
    whole move."* So the move is measured from the level to the post-break
    extreme reached so far, not to the break bar's close.
    """
    b = cand["break_bar"]
    level = cand["price"]
    up = cand["break_direction"] == "up"
    seg = bars[b: idx + 1]
    if not seg:
        return False
    extreme = max(x.high for x in seg) if up else min(x.low for x in seg)
    move = (extreme - level) if up else (level - extreme)
    if move <= 0:
        return False
    given_back = (extreme - bars[idx].close) if up else (bars[idx].close - extreme)
    return given_back >= pct * move


def detect_throwback(
    bars: List[OHLCVBar],
    bar_date: date_type,
    mode: str = MODE_OFF,
    band_atr: Optional[float] = None,
    stale_bars: Optional[int] = None,
    retrace_pct: Optional[float] = None,
) -> Optional[RawSignal]:
    """A `RawSignal` if a throwback triggered on `bar_date`, else `None`.

    The entry is always **in the direction of the break** (Ch 13): long on a
    return to a resistance broken upward, short on a pullback to a support
    broken downward.
    """
    if mode not in THROWBACK_MODES:
        raise ValueError(f"mode {mode!r} is not one of {sorted(THROWBACK_MODES)}")
    if mode == MODE_OFF or not bars or len(bars) < MIN_BARS:
        return None

    band_mult = DEFAULT_BAND_ATR if band_atr is None else band_atr
    stale = DEFAULT_STALE_BARS if stale_bars is None else stale_bars
    pct = DEFAULT_RETRACE_PCT if retrace_pct is None else retrace_pct

    idx = next((i for i, b in enumerate(bars) if b.date == bar_date), None)
    if idx is None or idx < MIN_BARS - 1:
        return None

    atr = atr_series(bars[: idx + 1])
    a = atr[idx] if idx < len(atr) else None
    if a is None or a <= 0:
        return None

    close = bars[idx].close
    # Computed ONCE. The first version called this inside the candidate loop
    # as well, which doubled an O(n x window) scan on every bar -- fine in a
    # unit test, ruinous for T4's 92-symbol replay.
    sr = compute_sr_levels(bars[: idx + 1])
    cands = _candidates(sr, bars, idx, stale)

    for cand in cands:                       # nearest first (`EC-T4`)
        in_band = abs(close - cand["price"]) <= a * band_mult
        retraced = _retraced(bars, idx, cand, pct)

        if mode == MODE_BAND:
            trigger = MODE_BAND if in_band else None
        elif mode == MODE_RETRACE:
            trigger = MODE_RETRACE if retraced else None
        else:                                 # EITHER — "whichever comes first"
            trigger = MODE_BAND if in_band else (MODE_RETRACE if retraced else None)
        if trigger is None:
            continue

        # `EC-T6`: contradictory evidence is not an entry. An unbroken level
        # of the opposite side sitting in the same band means price is caught
        # between two boundaries, not standing on one.
        opposing_group = ("resistances" if cand["break_direction"] == "up"
                          else "supports")
        opposing = any(
            (not (other.get("breaks") or []))
            and abs(float(other["price"]) - close) <= a * band_mult
            for other in sr.get(opposing_group, [])
        )
        if opposing:
            return None

        direction = "LONG" if cand["break_direction"] == "up" else "SHORT"
        return RawSignal(
            kind="THROWBACK",
            direction=direction,
            confidence=BASE_CONFIDENCE,
            bar_date=bar_date,
            trigger_price=close,
            evidence={
                "level_price": cand["price"],
                "break_bar": cand["break_bar"],
                "break_direction": cand["break_direction"],
                "bars_since_break": cand["bars_since_break"],
                "touches": cand["touches"],
                "penetration_atr": cand["penetration_atr"],
                "trigger": trigger,
                "band_atr": band_mult,
                "distance_atr": round(abs(close - cand["price"]) / a, 4),
            },
        )
    return None
