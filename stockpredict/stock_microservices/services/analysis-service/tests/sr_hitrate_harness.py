"""EM-2 / S2 — `H-S1`, the three-arm forward hit-rate harness.

Test-support, not a test module and not shipped code (no ``test_`` prefix, so
pytest collects nothing here).

What `H-S1` asks
----------------
`docs/SRS_edwards_magee_sr_levels.md` §5 defines the C4 benchmark for EM-2: for
each level, measure whether price **reversed** at it or **penetrated** it,
causally, and compare three arms —

1. ``touch_count``  — the shipped `_find_sr_levels`, whose ``strength`` is
   ``len(cluster)``;
2. ``em2_volume``   — the volume-weighted levels, which do not exist until `S4`
   and so report as unavailable here;
3. ``random_null``  — levels at random prices with the distance-from-spot
   distribution held fixed.

"A method improves only if it beats *both*." Arm 3 is what stops a hit rate
that merely reflects *where* levels tend to sit from being read as evidence
that the levels mean something.

Why arm 3 is built the way it is
--------------------------------
A level's apparent hit rate is confounded by its distance from spot: near
levels get approached far more often, and price mean-reverts locally over short
horizons regardless of what is drawn on the chart. So the null must hold that
confound fixed while destroying the claim that *this particular price* is
special. It does so by taking the real levels' relative distances from spot,
**shuffling them across levels** and randomising the side, then placing null
levels at ``spot x (1 +/- d)``. The aggregate distance distribution is
preserved exactly; only the locations are arbitrary.

Two alternatives were rejected: a null at a uniformly random price in the
window ignores the distance confound entirely and would flatter any real arm;
a null at *exactly* the same distance on the same side is the real level, which
measures nothing.

Causality (C1)
--------------
The discipline Backlog #79 established, and the one this harness would be
worthless without:

* levels are built from a frame **sliced** to ``[t-window+1, t]`` — never
  computed over the whole series and then indexed into;
* an approach is searched for strictly **after** ``t``;
* the outcome is judged only in the bars after the approach bar.

`H-S4` in `test_sr_volume.py` guards the primitives; the slicing here is the
same rule applied to the study.

The data source
---------------
Real VN daily bars when available, a committed synthetic multi-symbol set
otherwise, and the harness always **reports which** — because the strength of
the claim depends on it, and a study that silently substitutes synthetic data
for market data overstates its own result. See `source_bars`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from unittest.mock import MagicMock

from app.models.schemas import SRLevel, SRLevelType
from app.services.analysis_service import AnalysisService

# --- Harness parameters -----------------------------------------------------
# Every number here is a harness choice, swept at `W1`, not a finding. The
# committed baseline describes exactly these values.

WINDOW = 250           # bars of history a level is built from (what the service scans)
STEP = 10              # sample every Nth bar as a test date
MAX_WAIT = 40          # bars after t in which an approach may occur
HORIZON = 10           # bars after the approach in which the outcome is judged
PROXIMITY_PCT = 1.0    # how close price must come to count as an approach
REVERSAL_PCT = 1.0     # how far it must then move away to count as a reversal
PENETRATION_PCT = 1.0  # how far through to count as a penetration
MAX_SYMBOLS = 12       # keeps the suite fast; override with EM2_MAX_SYMBOLS
SEED = 20261015

ARMS = ("touch_count", "em2_volume", "random_null")

_REAL_BARS_DEFAULT = Path("/tmp/all_bars.tsv")


# --- Reports ----------------------------------------------------------------

@dataclass(frozen=True)
class ArmReport:
    """One arm's outcome counts.

    ``hit_rate`` is ``hits / (hits + misses)``: the unresolved approaches —
    those where neither a reversal nor a penetration happened inside `HORIZON`
    — are reported separately rather than silently folded into either side,
    because folding them in would let a change in the *resolution* rate
    masquerade as a change in accuracy.
    """
    arm: str
    levels_tested: int
    approaches: int
    hits: int
    misses: int
    unresolved: int
    hit_rate: Optional[float]
    reason: str = ""

    @property
    def available(self) -> bool:
        return self.hit_rate is not None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "arm": self.arm,
            "levels_tested": self.levels_tested,
            "approaches": self.approaches,
            "hits": self.hits,
            "misses": self.misses,
            "unresolved": self.unresolved,
            "hit_rate": None if self.hit_rate is None else round(self.hit_rate, 4),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class StudyReport:
    source_label: str
    symbols: List[str]
    test_dates: int
    arms: Dict[str, ArmReport] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_label": self.source_label,
            "symbols": sorted(self.symbols),
            "test_dates": self.test_dates,
            "arms": {name: arm.as_dict() for name, arm in sorted(self.arms.items())},
        }


# --- Data source ------------------------------------------------------------

def _synthetic_bars(n_symbols: int = 6, length: int = 600) -> Dict[str, pd.DataFrame]:
    """A committed, deterministic multi-symbol set so the suite is
    self-contained and runs identically in CI.

    Volume is **scripted, not constant**: it carries a slow cycle plus
    occasional bursts. EM-1's `H1` recorded the reason — a constant volume
    column is invariant under permutation, which makes a shuffle harness
    satisfiable by an implementation that does nothing. `S3` depends on this
    property of these fixtures, so it is built in from the start rather than
    retro-fitted.
    """
    out: Dict[str, pd.DataFrame] = {}
    for s in range(n_symbols):
        rng = np.random.default_rng(SEED + s * 7919)
        steps = rng.normal(0.0, 0.015, size=length)
        close = 100.0 * np.exp(np.cumsum(steps))
        wobble = rng.normal(0.0, 0.004, size=length)
        high = close * (1.0 + np.abs(wobble) + 0.002)
        low = close * (1.0 - np.abs(wobble) - 0.002)

        cycle = 1.0 + 0.35 * np.sin(np.arange(length) / 23.0)
        burst = 1.0 + 3.0 * (rng.random(length) > 0.97)
        volume = np.round(800_000 * cycle * burst * (1.0 + rng.normal(0, 0.15, length)))
        volume = np.clip(volume, 1_000, None)

        out[f"SYN{s}"] = pd.DataFrame({
            "date": pd.date_range("2020-01-01", periods=length, freq="B"),
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume.astype(float),
        })
    return out


def _read_bars_tsv(path: Path) -> Dict[str, pd.DataFrame]:
    """``symbol date open high low close volume``, tab separated — the dump
    shape Backlog #79 established and the Sessions Log documents extracting
    from MySQL."""
    rows: Dict[str, List[tuple]] = {}
    with path.open() as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 7:
                continue
            sym, d, o, hi, lo, c, v = parts
            try:
                rows.setdefault(sym, []).append(
                    (d, float(o), float(hi), float(lo), float(c), float(v))
                )
            except ValueError:
                continue

    out: Dict[str, pd.DataFrame] = {}
    for sym, bars in rows.items():
        df = pd.DataFrame(bars, columns=["date", "open", "high", "low", "close", "volume"])
        df["date"] = pd.to_datetime(df["date"])
        out[sym] = df.sort_values("date").reset_index(drop=True)
    return out


def source_bars() -> Tuple[Dict[str, pd.DataFrame], str]:
    """The bars the study runs on, plus a label saying what they actually are.

    ``$EM2_BARS_TSV`` overrides the path; the default local dump is used when
    present; otherwise the committed synthetic set. The label is returned
    rather than assumed, and it is recorded in the baseline, so a number can
    never be compared across sources by accident.
    """
    if os.environ.get("EM2_FORCE_SYNTHETIC"):
        return _synthetic_bars(), "synthetic-v1"
    override = os.environ.get("EM2_BARS_TSV")
    path = Path(override) if override else _REAL_BARS_DEFAULT
    if path.exists():
        bars = _read_bars_tsv(path)
        if bars:
            return bars, f"real:{path.name}"
    return _synthetic_bars(), "synthetic-v1"


def _selected(bars: Dict[str, pd.DataFrame], max_symbols: int) -> Dict[str, pd.DataFrame]:
    """Deterministic symbol selection — sorted, then truncated. Never random:
    the committed baseline has to describe a reproducible set."""
    keep = sorted(bars)[:max_symbols]
    return {k: bars[k] for k in keep}


# --- Level construction per arm ---------------------------------------------

def _shipped_levels(svc: AnalysisService, frame: pd.DataFrame) -> List[SRLevel]:
    supports, resistances = svc._find_sr_levels(frame)
    # A FLIP level appears in both lists by design; de-duplicate on identity so
    # it is not counted twice and given double weight in the rate.
    seen: set = set()
    out: List[SRLevel] = []
    for lvl in list(supports) + list(resistances):
        key = (round(lvl.price, 6), lvl.type)
        if key in seen:
            continue
        seen.add(key)
        out.append(lvl)
    return out


def _em2_levels(svc: AnalysisService, frame: pd.DataFrame) -> Tuple[List[SRLevel], str]:
    """The volume-weighted arm.

    `S4` adds ``volume_strength`` to `SRLevel` and populates it in
    `_find_sr_levels`. Until then this arm is deliberately unavailable rather
    than quietly falling back to the shipped levels — a fallback would make the
    arm look identical to arm 1 and the comparison vacuous.
    """
    levels = _shipped_levels(svc, frame)
    if not levels:
        return [], "no_levels"
    if all(getattr(lvl, "volume_strength", None) is None for lvl in levels):
        return [], "volume_strength_absent_until_S4"
    # Once S4 lands: rank by volume_strength and keep the levels it promotes.
    ranked = sorted(
        levels,
        key=lambda lvl: (getattr(lvl, "volume_strength", None) or 0.0),
        reverse=True,
    )
    return ranked, ""


def _null_levels(
    levels: Sequence[SRLevel],
    spot: float,
    rng: np.random.Generator,
) -> List[Dict[str, Any]]:
    """Arm 3 — the matched-distance random null.

    Takes the real levels' relative distances from spot, shuffles them across
    levels, randomises the side, and places a level there. The distance
    distribution is preserved exactly; the locations are arbitrary. A level
    whose price would be non-positive is dropped rather than clamped, because
    clamping would pile null levels onto one price.
    """
    if not levels or spot <= 0:
        return []
    distances = np.array([abs(lvl.price - spot) / spot for lvl in levels], dtype=float)
    rng.shuffle(distances)
    signs = rng.choice((-1.0, 1.0), size=len(distances))

    out: List[Dict[str, Any]] = []
    for lvl, d, sign in zip(levels, distances, signs):
        price = spot * (1.0 + sign * d)
        if price <= 0:
            continue
        # The *kind* follows the null price's own side of spot, so the outcome
        # rule stays coherent: a price above spot can only be tested as
        # resistance.
        kind = SRLevelType.RESISTANCE if price > spot else SRLevelType.SUPPORT
        out.append({"price": float(price), "type": kind})
    return out


# --- The outcome rule -------------------------------------------------------

def _classify(
    future: pd.DataFrame,
    level_price: float,
    is_resistance: bool,
) -> Optional[str]:
    """Did price reverse at this level, penetrate it, or neither?

    Returns ``"hit"``, ``"miss"``, or ``None`` for *no approach*. Order
    matters: whichever of the two thresholds is crossed **first** decides, so a
    bar that pokes through and comes back is a penetration followed by a
    recovery, not a reversal.

    ``future`` must contain only bars after the level's own construction
    window — the caller guarantees that, and it is the C1 rule of this study.
    """
    if future.empty or level_price <= 0:
        return None

    highs = future["high"].to_numpy(dtype=float)
    lows = future["low"].to_numpy(dtype=float)
    closes = future["close"].to_numpy(dtype=float)

    prox = level_price * PROXIMITY_PCT / 100.0
    away = level_price * (1.0 - REVERSAL_PCT / 100.0) if is_resistance \
        else level_price * (1.0 + REVERSAL_PCT / 100.0)
    through = level_price * (1.0 + PENETRATION_PCT / 100.0) if is_resistance \
        else level_price * (1.0 - PENETRATION_PCT / 100.0)

    limit = min(MAX_WAIT, len(future))
    for i in range(limit):
        # The approach requires the CLOSE to sit within `prox` of the level,
        # not merely that the bar reached it from one side.
        #
        # This is the harness's own bias control, and it was found by looking
        # at the null arm. With the looser rule ("high touched the level and
        # the close is anywhere below it") the two outcome thresholds are not
        # equidistant from where price actually is: a close 0.9% under a
        # resistance is 0.1% from the reversal threshold and 1.9% from the
        # penetration threshold, a 19:1 head start for "hit". That inflates
        # every arm and compresses the differences between them — which is the
        # one thing a benchmark may not do. Requiring the close to be *at* the
        # level makes the two thresholds near-symmetric, and the null arm
        # landing near a coin flip is the evidence that it worked.
        reached = highs[i] >= level_price - prox if is_resistance else lows[i] <= level_price + prox
        if not (reached and abs(closes[i] - level_price) <= prox):
            continue

        # Judge only the bars after the approach bar.
        window = slice(i + 1, min(i + 1 + HORIZON, len(future)))
        w_close = closes[window]
        if w_close.size == 0:
            return None

        if is_resistance:
            rev = np.flatnonzero(w_close <= away)
            pen = np.flatnonzero(w_close >= through)
        else:
            rev = np.flatnonzero(w_close >= away)
            pen = np.flatnonzero(w_close <= through)

        first_rev = rev[0] if rev.size else None
        first_pen = pen[0] if pen.size else None
        if first_rev is None and first_pen is None:
            return "unresolved"
        if first_pen is None:
            return "hit"
        if first_rev is None:
            return "miss"
        return "hit" if first_rev < first_pen else "miss"

    return None


# --- The study --------------------------------------------------------------

def run_study(
    max_symbols: Optional[int] = None,
    step: int = STEP,
    window: int = WINDOW,
) -> StudyReport:
    """Run all three arms over the available bars and report the counts."""
    bars, label = source_bars()
    cap = max_symbols if max_symbols is not None else int(
        os.environ.get("EM2_MAX_SYMBOLS", str(MAX_SYMBOLS))
    )
    bars = _selected(bars, cap)

    svc = AnalysisService(session=MagicMock())
    rng = np.random.default_rng(SEED)

    counts = {
        arm: {"levels": 0, "hit": 0, "miss": 0, "unresolved": 0} for arm in ARMS
    }
    em2_reason = "no_levels"
    test_dates = 0

    for symbol in sorted(bars):
        df = bars[symbol]
        last_t = len(df) - HORIZON - 2
        for t in range(window, last_t + 1, step):
            # C1: slice first, then build. Never build on the full series.
            frame = df.iloc[t - window + 1: t + 1].reset_index(drop=True)
            future = df.iloc[t + 1:].reset_index(drop=True)
            if future.empty:
                continue
            test_dates += 1
            spot = float(frame["close"].iloc[-1])

            shipped = _shipped_levels(svc, frame)
            em2, reason = _em2_levels(svc, frame)
            if reason:
                em2_reason = reason
            nulls = _null_levels(shipped, spot, rng)

            per_arm: Dict[str, List[Tuple[float, bool]]] = {
                "touch_count": [
                    (lvl.price, lvl.price > spot) for lvl in shipped
                ],
                "em2_volume": [
                    (lvl.price, lvl.price > spot) for lvl in em2
                ],
                "random_null": [
                    (n["price"], n["type"] == SRLevelType.RESISTANCE) for n in nulls
                ],
            }

            for arm, entries in per_arm.items():
                for price, is_res in entries:
                    counts[arm]["levels"] += 1
                    verdict = _classify(future, price, is_res)
                    if verdict == "hit":
                        counts[arm]["hit"] += 1
                    elif verdict == "miss":
                        counts[arm]["miss"] += 1
                    elif verdict == "unresolved":
                        counts[arm]["unresolved"] += 1

    arms: Dict[str, ArmReport] = {}
    for arm in ARMS:
        c = counts[arm]
        resolved = c["hit"] + c["miss"]
        rate = (c["hit"] / resolved) if resolved else None
        reason = ""
        if arm == "em2_volume" and not c["levels"]:
            reason = em2_reason
            rate = None
        arms[arm] = ArmReport(
            arm=arm,
            levels_tested=c["levels"],
            approaches=resolved + c["unresolved"],
            hits=c["hit"],
            misses=c["miss"],
            unresolved=c["unresolved"],
            hit_rate=rate,
            reason=reason,
        )

    return StudyReport(
        source_label=label,
        symbols=list(bars),
        test_dates=test_dates,
        arms=arms,
    )
