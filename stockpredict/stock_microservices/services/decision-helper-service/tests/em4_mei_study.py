"""EM-4 — does an extremely low MEI mark a market bottom?

    PYTHONPATH=. python3 tests/em4_mei_study.py

E&M's falsifiable claim, from Magee's market letter of 28 September 1985
reproduced in Ch 38:

    "For over 20 years, all major stock market Bottoms have corresponded with
    extremely low MEI readings."

He cites 9% Strong at the June 1982 low before the run from 770 to ~1300, and
8% at the February/June 1984 double bottom before 1079 to 1372.

That is a prediction, not a parameter, and it is testable without touching the
backtest: if extreme lows mark bottoms, forward market returns after a
low-MEI reading should beat the unconditional forward return.

CRITERION, FIXED BEFORE THE RUN
-------------------------------
Both, or the claim does not reproduce:

  1. forward market return after a BOTTOM-DECILE MEI reading is significantly
     higher than the unconditional forward return; and
  2. it holds at MORE THAN ONE horizon (10, 20, 60 sessions), so the result is
     not one lucky window length.

NON-OVERLAPPING samples only. Consecutive days' forward returns overlap almost
completely, and overlapping windows inflate significance — the trap #79
documented. Observations are therefore sampled every `horizon` sessions.

The market proxy, and its honest limits
---------------------------------------
There is no VN-Index series in the local dump, so the market is proxied by an
**equal-weighted** basket of the same 32 symbols, each normalised to 1 at its
first bar. Two consequences, stated rather than buried:

* VN-Index is **cap-weighted**, and the VN market is dominated by a handful of
  large caps, so a cap-weighted proxy would be closer to what a user sees.
* The proxy is built from the **same universe** the MEI is built from, so the
  two are not independent. That makes this a test of internal consistency —
  "does breadth of this basket predict the basket" — which is the weaker form
  of E&M's claim. The stronger form needs the real index.
"""
from __future__ import annotations

import math
import random
from bisect import insort
from statistics import mean
import os
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from app.services.breadth.mei import MeiPoint, compute_mei_series
from app.services.signal.base import OHLCVBar

from tests.failed_signal_override_study import load_bars as load_shallow_bars

HORIZONS = (10, 20, 60)

#: Backlog #87. When the deep dump exists, the study uses ~18 years of VN100
#: and the REAL cap-weighted VNINDEX instead of 5.3 years of VN30 and an
#: equal-weighted basket of the same symbols the MEI is built from. Both are
#: reported in the header, because every EM-4 conclusion depends on which was
#: used and a study that silently swapped its inputs would be worthless.
DEEP_BARS = os.environ.get("EM4_BARS", "/tmp/deep_bars.tsv")
DEEP_INDEX = os.environ.get("EM4_INDEX", "/tmp/deep_index.tsv")
DECILE = 10.0        # "extremely low" = bottom decile of the trailing history
WARMUP_POINTS = 250  # readings before a percentile is trusted


def load_bars() -> Tuple[Dict[str, List[OHLCVBar]], str]:
    """The deep VN100 dump when it exists, the shallow VN30 one otherwise."""
    if Path(DEEP_BARS).exists():
        from tests.failed_signal_override_study import load_bars as _loader

        return _loader(DEEP_BARS), f"deep:{Path(DEEP_BARS).name}"
    return load_shallow_bars(), "shallow:all_bars.tsv"


def load_index() -> Tuple[Optional[Dict[object, float]], str]:
    """The real cap-weighted VNINDEX, if the dump is present.

    This is what `#87` was raised to supply. Before it, the market was proxied
    by an equal-weighted basket of the **same symbols the MEI is built from**,
    so breadth was being tested against a basket it partly defined — internal
    consistency, not E&M's claim.
    """
    path = Path(DEEP_INDEX)
    if not path.exists():
        return None, "equal-weighted basket (proxy)"
    out: Dict[object, float] = {}
    from datetime import datetime as _dt

    with path.open() as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 7:
                continue
            try:
                out[_dt.strptime(parts[1], "%Y-%m-%d").date()] = float(parts[5])
            except ValueError:
                continue
    return (out, "VNINDEX (real, cap-weighted)") if out else (None, "basket")


def market_proxy(bars_by_symbol: Dict[str, Sequence[OHLCVBar]]) -> Dict[object, float]:
    """Equal-weighted basket: each symbol normalised to 1 at its first bar."""
    first: Dict[str, float] = {}
    level: Dict[object, List[float]] = {}
    for sym, bars in bars_by_symbol.items():
        for b in sorted(bars, key=lambda x: x.date):
            if sym not in first:
                first[sym] = b.close
            if first[sym] > 0:
                level.setdefault(b.date, []).append(b.close / first[sym])
    return {d: mean(v) for d, v in level.items() if v}


def welch(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    if len(a) < 2 or len(b) < 2:
        return None
    ma, mb = mean(a), mean(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return (ma - mb) / se if se else None


def forward_returns(
    series: List[MeiPoint],
    proxy: Dict[object, float],
    horizon: int,
) -> Tuple[List[float], List[float], int]:
    """(low-MEI forward returns, baseline forward returns, n low).

    SUPERSEDED as of Backlog #99 — `forward_observations` + `block_bootstrap`
    is the primary estimator. This one is **kept, not deleted**, because #87's
    and #90's published tables are derived from it and a result nobody can
    re-derive is not a record. It is phase-dependent: see #99 for why that
    matters and docs/backlog99_phase_independent_em4.md for the replacement.

    Both arms are sampled so that no two observations within an arm share a
    forward bar — overlapping windows inflate significance, the trap `#79`
    documented.

    **How, and why not the obvious way.** The first version of this walked a
    fixed stride (`range(warmup, n, horizon)`) and tested whichever days it
    landed on. That is a *systematic* sample, and low-MEI episodes are short
    and clustered in time — a handful of bear markets — so a stride can step
    straight over all of them. It did: on 19.7 years at the 60-session horizon
    it found **zero** low-MEI observations, fewer than the 5.3-year data had
    found, which is impossible for a real sampler and was the clue.

    So every qualifying day is considered, and non-overlap is enforced
    *within* each arm by taking the earliest and skipping forward by
    `horizon`. That uses every available episode instead of whichever happened
    to fall on a stride.
    """
    days = [p.day for p in series]
    # "Extremely low" against the reading's OWN trailing history, so the
    # threshold is never set with hindsight. Shared with the #99 estimator via
    # `low_flags` so the two samplers cannot classify differently.
    flags = low_flags(series)
    low_idx: List[int] = []
    other_idx: List[int] = []
    for i in range(WARMUP_POINTS, len(series) - horizon):
        (low_idx if flags[i] else other_idx).append(i)

    def harvest(indices: List[int]) -> List[float]:
        out: List[float] = []
        last = -10**9
        for i in indices:
            if i - last < horizon:
                continue
            d0, d1 = days[i], days[i + horizon]
            if d0 not in proxy or d1 not in proxy or proxy[d0] <= 0:
                continue
            out.append((proxy[d1] / proxy[d0] - 1.0) * 100.0)
            last = i
        return out

    low = harvest(low_idx)
    base = harvest(other_idx)
    return low, base, len(low)


# ---------------------------------------------------------------------------
# Backlog #99 — the phase-independent estimator
# ---------------------------------------------------------------------------
# Every constant here was fixed in docs/backlog99_phase_independent_em4.md and
# committed BEFORE this code was written (commit 9bd6ecfd). They are not to be
# tuned against output; doing so would void the only thing that makes the
# result readable.
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20261027
BLOCK_MULTIPLE = 2                 # primary block length = 2 x horizon
BLOCK_SENSITIVITY = (1, 2, 3)      # pre-registered robustness report


def low_flags(series: List[MeiPoint]) -> List[bool]:
    """Is each reading in the bottom `DECILE` of its OWN trailing history?

    Factored out of `forward_returns` so that the old phase-dependent sampler
    and the `#99` estimator cannot drift apart: #99 pre-registered that the
    classification is untouched and only the *sampling* changes, and sharing
    one implementation makes that structurally true instead of merely
    intended. The expanding window is what keeps the threshold free of
    hindsight.

    O(n log n)-ish via insertion into a sorted list, where the original
    re-sorted the whole history on every reading. Same numbers — #90's table
    is reproduced exactly from this path, which is the regression check.
    """
    flags = [False] * len(series)
    history: List[float] = []
    for i, point in enumerate(series):
        if i >= WARMUP_POINTS and history:
            cutoff = history[max(0, int(len(history) * DECILE / 100.0) - 1)]
            flags[i] = point.mei <= cutoff
        insort(history, point.mei)
    return flags


def forward_observations(
    series: List[MeiPoint],
    proxy: Dict[object, float],
    horizon: int,
) -> List[Tuple[bool, float]]:
    """EVERY qualifying day as `(is_low, forward_return_pct)`, in time order.

    The `#99` sample. `forward_returns` below enforces non-overlap by taking
    the earliest qualifying day and skipping forward by `horizon`, so the set
    it returns is decided by which index comes first — and `WARMUP_POINTS` is
    an *index*. #90 measured what that costs: shifting the series start by up
    to 44 readings, which changes nothing about the market, moved Welch t
    across a full point.

    Here there is no grid for an offset to move, because nothing is skipped.
    The price is that consecutive observations overlap by `horizon - 1` bars,
    so the naive standard error is meaningless and inference must come from
    `block_bootstrap`. That trade is deliberate: the overlap is a *known*
    dependence that a block bootstrap can price, whereas the old design's
    phase was an arbitrary choice that nothing could correct for.

    Time order is load-bearing — the bootstrap resamples contiguous blocks.
    """
    days = [p.day for p in series]
    flags = low_flags(series)
    out: List[Tuple[bool, float]] = []
    for i in range(WARMUP_POINTS, len(series) - horizon):
        d0, d1 = days[i], days[i + horizon]
        if d0 not in proxy or d1 not in proxy or proxy[d0] <= 0:
            continue
        out.append((flags[i], (proxy[d1] / proxy[d0] - 1.0) * 100.0))
    return out


def edge(observations: Sequence[Tuple[bool, float]]) -> Optional[float]:
    """mean(forward | low) - mean(forward | other), in percentage points."""
    low_sum = other_sum = 0.0
    low_n = other_n = 0
    for is_low, ret in observations:
        if is_low:
            low_sum += ret
            low_n += 1
        else:
            other_sum += ret
            other_n += 1
    if low_n < 2 or other_n < 2:
        return None
    return low_sum / low_n - other_sum / other_n


def block_bootstrap(
    observations: Sequence[Tuple[bool, float]],
    block: int,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> Tuple[Optional[float], Optional[float], int]:
    """`(SE of the edge, 2.5th percentile of the edge, replicates discarded)`.

    Moving-block bootstrap: draw contiguous blocks of `(is_low, return)` pairs
    **jointly** and with replacement until a replicate is as long as the
    original, then recompute the edge. Drawing the pair jointly is the point —
    it keeps a low-MEI episode intact, so whole episodes enter or leave a
    replicate together and the bootstrap sees how few of them there really
    are.

    This is what makes using every overlapping day legitimate. Two dependences
    need pricing and a naive SE prices neither:

    * **mechanical** — forward returns `horizon - 1` bars apart share bars;
    * **episodic** — low-MEI days cluster into a handful of bear markets, so
      hundreds of them may carry three or four independent events.

    `#87` did not escape this by sampling non-overlapping days: 11 of them
    drawn from 3-4 bear markets are not 11 independent draws, and Welch
    treated them as though they were. The old design paid 99% of the data for
    an independence it never achieved.

    Implemented over prefix sums, so a block contributes in O(1) and a
    replicate costs O(n / block) rather than O(n). Same draws as the naive
    form — the random stream is one `randint` per block either way.
    """
    n = len(observations)
    if n < 4:
        return None, None, replicates
    block = max(1, min(block, n))

    # Prefix sums per arm, so any contiguous block's contribution is a subtraction.
    low_sum = [0.0] * (n + 1)
    low_cnt = [0] * (n + 1)
    oth_sum = [0.0] * (n + 1)
    oth_cnt = [0] * (n + 1)
    for i, (is_low, ret) in enumerate(observations):
        low_sum[i + 1] = low_sum[i] + (ret if is_low else 0.0)
        low_cnt[i + 1] = low_cnt[i] + (1 if is_low else 0)
        oth_sum[i + 1] = oth_sum[i] + (0.0 if is_low else ret)
        oth_cnt[i + 1] = oth_cnt[i] + (0 if is_low else 1)

    rng = random.Random(seed)
    max_start = n - block
    edges: List[float] = []
    discarded = 0

    for _ in range(replicates):
        remaining = n
        ls = os_ = 0.0
        lc = oc = 0
        while remaining > 0:
            start = rng.randint(0, max_start) if max_start > 0 else 0
            take = block if block <= remaining else remaining
            end = start + take
            ls += low_sum[end] - low_sum[start]
            lc += low_cnt[end] - low_cnt[start]
            os_ += oth_sum[end] - oth_sum[start]
            oc += oth_cnt[end] - oth_cnt[start]
            remaining -= take
        if lc < 2 or oc < 2:
            # A replicate that drew no bear market cannot produce an edge. Counted
            # and reported rather than silently dropped: a high discard rate means
            # the episodes are too few for the bootstrap to say anything.
            discarded += 1
        else:
            edges.append(ls / lc - os_ / oc)

    if len(edges) < 2:
        return None, None, discarded
    centre = mean(edges)
    se = math.sqrt(sum((x - centre) ** 2 for x in edges) / (len(edges) - 1))
    low_pct = sorted(edges)[int(0.025 * len(edges))]
    return se, low_pct, discarded


def phase_independent_table(
    series: List[MeiPoint],
    proxy: Dict[object, float],
    block_multiple: int = BLOCK_MULTIPLE,
) -> List[Tuple[int, int, int, float, Optional[float], Optional[float], int]]:
    """`(horizon, n_low, n_other, edge, t_boot, pct2.5, discarded)` per horizon."""
    rows = []
    for horizon in HORIZONS:
        obs = forward_observations(series, proxy, horizon)
        value = edge(obs)
        if value is None:
            continue
        n_low = sum(1 for f, _ in obs if f)
        se, low_pct, discarded = block_bootstrap(obs, block_multiple * horizon)
        t_boot = (value / se) if se else None
        rows.append((horizon, n_low, len(obs) - n_low, value, t_boot,
                     low_pct, discarded))
    return rows


if __name__ == "__main__":
    bars, bars_label = load_bars()
    index, index_label = load_index()
    print(f"universe = {len(bars)} symbols  ({bars_label})")
    print(f"market   = {index_label}\n")

    series = compute_mei_series(bars)
    proxy = index if index is not None else market_proxy(bars)
    print(f"MEI series: {len(series)} readings, {series[0].day} -> {series[-1].day}")
    values = [p.mei for p in series]
    print(f"   range {min(values):.1f}% - {max(values):.1f}%   "
          f"mean {mean(values):.1f}%   proxy days {len(proxy)}\n")

    print("E&M: extremely low MEI marks a bottom. Forward proxy returns, "
          "non-overlapping:\n")
    print(f"{'horizon':>8}{'n low':>7}{'after low MEI':>15}{'after others':>15}"
          f"{'edge':>9}{'Welch t':>10}")
    passes = 0
    for h in HORIZONS:
        low, every, n = forward_returns(series, proxy, h)
        if len(low) < 2 or len(every) < 2:
            print(f"{h:>8}{n:>7}  insufficient non-overlapping sample")
            continue
        t = welch(low, every)
        sig = t is not None and t > 1.96
        passes += 1 if sig else 0
        print(f"{h:>8}{n:>7}{mean(low):>14.2f}%{mean(every):>14.2f}%"
              f"{mean(low) - mean(every):>+8.2f}%{t:>+9.2f} "
              f"{'SIG' if sig else 'ns'}")

    print(f"\nCRITERION: significant at more than one horizon -> "
          f"{passes} of {len(HORIZONS)} significant: "
          f"{'PASS' if passes >= 2 else 'FAIL'}")
    print("   (^ the phase-DEPENDENT sampler #87 and #90 published; kept so "
          "those\n    tables stay reproducible. #99's estimator follows.)")

    # -----------------------------------------------------------------------
    # Backlog #99 - pre-registered in docs/backlog99_phase_independent_em4.md
    # -----------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("Backlog #99 - phase-independent estimator: EVERY qualifying day,")
    print(f"moving-block bootstrap (L = {BLOCK_MULTIPLE}h, B = "
          f"{BOOTSTRAP_REPLICATES}, seed {BOOTSTRAP_SEED}).")
    print("Criterion INHERITED from #87, unchanged: t > 1.96 at more than one "
          "horizon.")
    print("=" * 78 + "\n")

    print(f"{'horizon':>8}{'n low':>7}{'n other':>9}{'edge':>9}"
          f"{'SE boot':>9}{'t boot':>9}{'2.5 pct':>9}{'disc':>6}")
    passes99 = 0
    rows99 = phase_independent_table(series, proxy)
    for h, n_low, n_oth, value, t_boot, low_pct, disc in rows99:
        sig = t_boot is not None and t_boot > 1.96
        passes99 += 1 if sig else 0
        se = value / t_boot if t_boot else float("nan")
        print(f"{h:>8}{n_low:>7}{n_oth:>9}{value:>+8.2f}%{se:>9.2f}"
              f"{(t_boot if t_boot is not None else float('nan')):>+9.2f}"
              f"{(low_pct if low_pct is not None else float('nan')):>+8.2f}%"
              f"{disc:>6}  {'SIG' if sig else 'ns'}")
    print(f"\nCRITERION: {passes99} of {len(HORIZONS)} significant: "
          f"{'PASS' if passes99 >= 2 else 'FAIL'}")

    print("\nPre-registered block-length sensitivity (t boot):")
    print(f"{'horizon':>8}" + "".join(f"{'L=' + str(m) + 'h':>10}"
                                     for m in BLOCK_SENSITIVITY))
    for h in HORIZONS:
        obs = forward_observations(series, proxy, h)
        value = edge(obs)
        cells = ""
        for m in BLOCK_SENSITIVITY:
            se, _, _ = block_bootstrap(obs, m * h)
            cells += f"{(value / se if se else float('nan')):>+10.2f}"
        print(f"{h:>8}{cells}")

    # The pre-registered test of the FIX, not of E&M: #90 showed that dropping
    # the first k readings moved the old t by a full point. If the new estimator
    # is phase-independent that spread must collapse; if it does not, #99 failed.
    print("\nPhase sweep - the pre-registered test of #99 itself.")
    print("Dropping the first k readings changes nothing about the market.")
    print("#90 measured the OLD spread as 1.00 (h10) / 1.18 (h20) / 0.75 (h60).")
    print(f"\n{'k':>4}{'starts':>13}" + "".join(f"{'t' + str(h):>9}"
                                                for h in HORIZONS))
    sweep: dict = {h: [] for h in HORIZONS}
    for k in (0, 5, 15, 20, 30, 40):
        sub = series[k:]
        cells = ""
        for h in HORIZONS:
            obs = forward_observations(sub, proxy, h)
            value = edge(obs)
            se, _, _ = block_bootstrap(obs, BLOCK_MULTIPLE * h)
            t = value / se if (value is not None and se) else None
            if t is not None:
                sweep[h].append(t)
            cells += f"{(t if t is not None else float('nan')):>+9.2f}"
        print(f"{k:>4}{str(sub[0].day):>13}{cells}")
    print(f"\n{'horizon':>8}{'t range':>20}{'spread':>9}{'old spread':>12}")
    for h, old in zip(HORIZONS, (1.00, 1.18, 0.75)):
        ts = sweep[h]
        if not ts:
            continue
        print(f"{h:>8}{f'{min(ts):+.2f} .. {max(ts):+.2f}':>20}"
              f"{max(ts) - min(ts):>9.2f}{old:>12.2f}")


# ---------------------------------------------------------------------------
# Two follow-ups the first result forces
# ---------------------------------------------------------------------------

def describe_extremes(series: List[MeiPoint], proxy: Dict[object, float]) -> None:
    """Did the MEI actually collapse during the one real bear market here?

    DESCRIPTIVE, not a test — n=1 event. But if the measure failed even to
    fall during a 2022-style decline, nothing built on it could work, so it is
    worth knowing before the predictive question is pursued further.
    """
    lows = sorted(series, key=lambda p: p.mei)[:8]
    print("the eight lowest readings in the series:")
    for p in lows:
        print(f"   {p.day}  MEI={p.mei:5.1f}%  "
              f"(+{p.bullish} -{p.bearish} ={p.neutral} of {p.classified})")

    dd = sorted(proxy.items(), key=lambda kv: kv[1])[:3]
    print("\nthe proxy's three lowest closes:")
    for d, v in dd:
        at = next((p.mei for p in series if p.day == d), None)
        print(f"   {d}  level={v:.3f}   MEI that day="
              f"{'n/a' if at is None else f'{at:.1f}%'}")


def quintile_monotonicity(
    series: List[MeiPoint], proxy: Dict[object, float], horizon: int
) -> None:
    """Does forward return vary with the LEVEL of breadth, across all of it?

    A different question from E&M's bottoms claim, and the one the register's
    other half actually needs: an exposure governor scales commitments with
    the reading, so what matters is whether the reading carries information
    across its whole range — not only at a rare extreme.

    It is also the better-powered question: every observation is used instead
    of a tail, so a null here is informative where the bottoms null is merely
    underpowered.
    """
    days = [p.day for p in series]
    rows: List[Tuple[float, float]] = []
    for i in range(WARMUP_POINTS, len(series) - horizon, horizon):
        d0, d1 = days[i], days[i + horizon]
        if d0 not in proxy or d1 not in proxy or proxy[d0] <= 0:
            continue
        rows.append((series[i].mei, (proxy[d1] / proxy[d0] - 1.0) * 100.0))

    if len(rows) < 10:
        print(f"   horizon {horizon}: only {len(rows)} observations")
        return

    rows.sort(key=lambda r: r[0])
    k = len(rows) // 5 or 1
    print(f"   horizon {horizon} sessions, {len(rows)} non-overlapping observations")
    buckets = []
    for q in range(5):
        chunk = rows[q * k: (q + 1) * k] if q < 4 else rows[4 * k:]
        if not chunk:
            continue
        mei_lo, mei_hi = chunk[0][0], chunk[-1][0]
        fwd = mean(r[1] for r in chunk)
        buckets.append(fwd)
        print(f"      Q{q + 1}  MEI {mei_lo:5.1f}-{mei_hi:5.1f}%  "
              f"n={len(chunk):3d}  forward {fwd:+7.2f}%")
    if len(buckets) == 5:
        t = welch([r[1] for r in rows[4 * k:]], [r[1] for r in rows[:k]])
        print(f"      top quintile vs bottom: {buckets[-1] - buckets[0]:+.2f}%  "
              f"Welch t={t:+.2f} {'SIG' if t and abs(t) > 1.96 else 'ns'}")
