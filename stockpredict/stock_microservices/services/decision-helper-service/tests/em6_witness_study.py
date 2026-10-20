"""EM-6 Phase 1 — is a multi-index confirmation gate vacuous on VN data?

    PYTHONPATH=. python3 tests/em6_witness_study.py [indices.tsv]

Not a test: a design-phase measurement whose answer decides whether EM-6 gets
built, and in what form.

The question
------------
E&M's tenet 8 is their most durable claim: *"no valid trend-change signal from
one average alone"* — two averages must confirm, though *"they need not confirm
on the same day"*. Bassetti's 9th-edition revision is the directly applicable
part: thirty stocks can no longer represent an economy, so he reads the broad
trend from the **Industrials + S&P 500 + NASDAQ** together, requires "harmonic
convergence" among the three, and treats **disagreement among them as itself a
signal to hedge**.

The register flagged the risk before any work started, and deferred it here:

> VNINDEX and VN30 share most of their weight, so they may confirm trivially;
> HNX / UPCOM or a breadth measure (EM-4) may be the real second witness.
> That question belongs in the Phase-1 SRS, not here.

A gate that almost never disagrees cannot filter anything: it would pass every
signal, add a stage to the pipeline, and buy nothing. So the design hinges on
whether VN indices are *independent enough to disagree*, and that is measurable
before a line of gate code is written.

PRE-REGISTERED CRITERIA (fixed before the first run)
-----------------------------------------------------
A candidate second witness is **usable** only if, on its common history with
VNINDEX, all three hold:

  W1  it is not substantially the same instrument
      -> daily-return correlation with VNINDEX <= 0.95
  W2  the gate would actually bind
      -> the two disagree on >= 10% of days
  W3  disagreement persists long enough to act on
      -> median disagreement episode >= 5 trading days

W3 is there because a gate on a signal that flickers daily is noise: a trade
held for weeks cannot be governed by a witness that changes its mind every
other day.

If **no** candidate passes all three, EM-6's multi-index form is vacuous on
this market, and the SRS must either take the MEI (EM-4) as the second witness
-- a genuinely different construction, counting constituents instead of
weighting them -- or recommend closing EM-6 unbuilt.

Two trend definitions, deliberately
------------------------------------
The conclusion must not hinge on one proxy, so agreement is measured twice:

  (a) `compute_regime` -- the shipped instrument (20/50 MA spread), the same
      stand-in EM-4 used for Magee's eye. Mechanical and already tested.
  (b) a **Dow swing rule** -- closing prices only, trend UP while the last
      confirmed swing high *and* low are both above their predecessors. This
      is the book's actual rule; (a) is not.

A zigzag threshold is an unavoidable discretisation of "secondary reaction".
5% is used because E&M's own "line" formations are ~5% ranges. Both
definitions are computed causally: day *i* reads bars up to *i* and nothing
later.
"""
from __future__ import annotations

import os
import statistics
import sys
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.backtest.market_features import compute_regime  # noqa: E402
from app.services.signal.base import OHLCVBar  # noqa: E402

FAST, SLOW = 20, 50          # passed explicitly: they are bound defaults
SWING_PCT = 0.05             # the "secondary reaction" discretisation
CORR_CEILING = 0.95          # W1
MIN_DISAGREE_SHARE = 0.10    # W2
MIN_EPISODE_BARS = 5         # W3


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def load(path: str) -> Dict[str, List[OHLCVBar]]:
    series: Dict[str, List[OHLCVBar]] = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 7:
                continue
            code, day, o, h, l, c, v = parts[:7]
            series[code].append(
                OHLCVBar(date=day, open=float(o), high=float(h),
                         low=float(l), close=float(c), volume=float(v))
            )
    for code in series:
        series[code].sort(key=lambda b: b.date)
    return dict(series)


# ---------------------------------------------------------------------------
# trend definitions
# ---------------------------------------------------------------------------

def regime_series(bars: Sequence[OHLCVBar]) -> List[str]:
    """`compute_regime` per day, causally.

    It reads only the trailing `SLOW` closes, so a trailing window is exactly
    equivalent to the full prefix -- asserted, not assumed, in `_self_check`.
    """
    out: List[str] = []
    for i in range(1, len(bars) + 1):
        window = bars[max(0, i - SLOW):i]
        out.append(compute_regime(list(window), fast=FAST, slow=SLOW))
    return out


def dow_series(bars: Sequence[OHLCVBar], pct: float = SWING_PCT) -> List[str]:
    """Dow's primary trend from successive confirmed swing highs and lows.

    Closing prices only (tenet 11). A swing is confirmed once price reverses
    `pct` from the running extreme; the trend turns UP only when the newest
    confirmed high *and* low both exceed their predecessors, and DOWN only
    when both fall below -- which is the two-condition rule, not a single
    higher high.
    """
    out: List[str] = []
    highs: List[float] = []
    lows: List[float] = []
    direction = 0               # +1 rising leg, -1 falling leg, 0 unknown
    extreme = bars[0].close if bars else 0.0
    trend = "UNDEFINED"

    for b in bars:
        c = b.close
        if direction >= 0:
            if c > extreme:
                extreme = c
            elif c <= extreme * (1 - pct):
                highs.append(extreme)          # the leg's top is confirmed
                direction, extreme = -1, c
        if direction <= 0:
            if c < extreme or direction == 0:
                extreme = min(extreme, c)
            if c >= extreme * (1 + pct):
                lows.append(extreme)           # the leg's bottom is confirmed
                direction, extreme = 1, c

        if len(highs) >= 2 and len(lows) >= 2:
            up = highs[-1] > highs[-2] and lows[-1] > lows[-2]
            down = highs[-1] < highs[-2] and lows[-1] < lows[-2]
            if up:
                trend = "TREND_UP"
            elif down:
                trend = "TREND_DOWN"
            # neither: the trend stands until reversal is signalled (tenet 12)
        out.append(trend)
    return out


def _self_check(bars: Sequence[OHLCVBar]) -> None:
    """The trailing-window optimisation must not change a single reading."""
    full = [compute_regime(list(bars[:i]), fast=FAST, slow=SLOW)
            for i in range(1, min(len(bars), 400) + 1)]
    windowed = regime_series(bars[:min(len(bars), 400)])
    assert full == windowed, "trailing window changed a regime reading"


# ---------------------------------------------------------------------------
# agreement
# ---------------------------------------------------------------------------

def align(a: Sequence[OHLCVBar], b: Sequence[OHLCVBar]) -> Tuple[List[int], List[int]]:
    """Indices into each series for the dates they share."""
    pos_b = {bar.date: i for i, bar in enumerate(b)}
    ia, ib = [], []
    for i, bar in enumerate(a):
        j = pos_b.get(bar.date)
        if j is not None:
            ia.append(i)
            ib.append(j)
    return ia, ib


def correlation(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    if n < 3:
        return float("nan")
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return float("nan")
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return cov / (va ** 0.5 * vb ** 0.5)


def episodes(flags: Sequence[bool]) -> List[int]:
    """Lengths of consecutive True runs."""
    runs, cur = [], 0
    for f in flags:
        if f:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return runs


def compare(name_a: str, bars_a: Sequence[OHLCVBar],
            name_b: str, bars_b: Sequence[OHLCVBar],
            trend_a: Sequence[str], trend_b: Sequence[str]) -> dict:
    """Compare two pre-computed trend series on their shared dates.

    The trend series are passed in rather than computed here: computing them
    per pair made this O(n^2) and the study never finished.
    """
    ia, ib = align(bars_a, bars_b)
    if len(ia) < SLOW * 3:
        return {"pair": f"{name_a}/{name_b}", "n": len(ia), "skip": True}

    ta = [trend_a[i] for i in ia]
    tb = [trend_b[i] for i in ib]

    # returns on the shared dates, for a definition-free redundancy measure
    ra = [bars_a[ia[k]].close / bars_a[ia[k - 1]].close - 1 for k in range(1, len(ia))]
    rb = [bars_b[ib[k]].close / bars_b[ib[k - 1]].close - 1 for k in range(1, len(ib))]

    decided = [(x, y) for x, y in zip(ta, tb)
               if x != "UNDEFINED" and y != "UNDEFINED"]
    disagree = [x != y for x, y in decided]
    runs = episodes(disagree)

    # the cost side: VNINDEX says go, the witness withholds confirmation
    blocked = sum(1 for x, y in decided if x == "TREND_UP" and y != "TREND_UP")
    up_days = sum(1 for x, _ in decided if x == "TREND_UP")

    return {
        "pair": f"{name_a}/{name_b}",
        "n": len(decided),
        "from": bars_a[ia[0]].date,
        "to": bars_a[ia[-1]].date,
        "corr": correlation(ra, rb),
        "disagree_share": (sum(disagree) / len(decided)) if decided else 0.0,
        "median_episode": statistics.median(runs) if runs else 0.0,
        "max_episode": max(runs) if runs else 0,
        "episodes": len(runs),
        "blocked_share": (blocked / up_days) if up_days else 0.0,
        "skip": False,
    }


def verdict(row: dict) -> Tuple[bool, str]:
    w1 = row["corr"] <= CORR_CEILING
    w2 = row["disagree_share"] >= MIN_DISAGREE_SHARE
    w3 = row["median_episode"] >= MIN_EPISODE_BARS
    flags = f"W1{'+' if w1 else '-'} W2{'+' if w2 else '-'} W3{'+' if w3 else '-'}"
    return (w1 and w2 and w3), flags



# ---------------------------------------------------------------------------
# witness independence, convergence, and confirmation lag
# ---------------------------------------------------------------------------

def corr_matrix(series: Dict[str, List[OHLCVBar]]) -> None:
    """Pairwise daily-return correlation across every index.

    A witness triple is only three witnesses if the witnesses are independent
    of EACH OTHER too, not just of VNINDEX.
    """
    codes = sorted(series, key=lambda c: -len(series[c]))
    print(f"\n{'':12s}" + "".join(f"{c[:9]:>10s}" for c in codes))
    for a in codes:
        cells = []
        for b in codes:
            if a == b:
                cells.append(f"{'-':>10s}")
                continue
            ia, ib = align(series[a], series[b])
            if len(ia) < 50:
                cells.append(f"{'n/a':>10s}")
                continue
            ra = [series[a][ia[k]].close / series[a][ia[k - 1]].close - 1
                  for k in range(1, len(ia))]
            rb = [series[b][ib[k]].close / series[b][ib[k - 1]].close - 1
                  for k in range(1, len(ib))]
            cells.append(f"{correlation(ra, rb):>10.3f}")
        print(f"{a:12s}" + "".join(cells))


def convergence(series: Dict[str, List[OHLCVBar]],
                trends: Dict[str, Sequence[str]],
                triple: Sequence[str]) -> None:
    """Bassetti's 'harmonic convergence': how often do all three agree?

    Also the state he says to act on -- disagreement -- as a share of days,
    since he treats it as a hedge signal rather than merely an absence.
    """
    a, b, c = triple
    pos_b = {bar.date: i for i, bar in enumerate(series[b])}
    pos_c = {bar.date: i for i, bar in enumerate(series[c])}
    states: List[Tuple[str, str, str]] = []
    for i, bar in enumerate(series[a]):
        j, k = pos_b.get(bar.date), pos_c.get(bar.date)
        if j is None or k is None:
            continue
        t = (trends[a][i], trends[b][j], trends[c][k])
        if "UNDEFINED" in t:
            continue
        states.append(t)
    if not states:
        print("  no common history")
        return
    n = len(states)
    allagree = sum(1 for t in states if t[0] == t[1] == t[2])
    two = sum(1 for t in states
              if not (t[0] == t[1] == t[2])
              and (t[0] == t[1] or t[0] == t[2] or t[1] == t[2]))
    none = n - allagree - two
    print(f"  {' + '.join(triple)}   n = {n}")
    print(f"    all three agree (harmonic convergence)  {allagree / n:>6.1%}")
    print(f"    two of three agree                      {two / n:>6.1%}")
    print(f"    all three differ                        {none / n:>6.1%}")
    unanimous_up = sum(1 for t in states if t[0] == t[1] == t[2] == "TREND_UP")
    vn_up = sum(1 for t in states if t[0] == "TREND_UP")
    if vn_up:
        print(f"    VNINDEX TREND_UP days surviving unanimity "
              f"{unanimous_up / vn_up:>6.1%}  ({unanimous_up} of {vn_up})")


def confirmation_lag(series: Dict[str, List[OHLCVBar]],
                     trends: Dict[str, Sequence[str]],
                     lead: str, witness: str, horizon: int = 120) -> None:
    """E&M: the averages *need not confirm on the same day*.

    So the gate needs a lag window, and its size is an empirical question:
    when the lead index turns, how long until the witness agrees -- and how
    often does it never agree at all?
    """
    ia, ib = align(series[lead], series[witness])
    tl = [trends[lead][i] for i in ia]
    tw = [trends[witness][i] for i in ib]
    lags: List[int] = []
    never = 0
    for i in range(1, len(tl)):
        if tl[i] == tl[i - 1] or tl[i] == "UNDEFINED":
            continue                      # only the lead's turn days
        found = None
        for d in range(0, min(horizon, len(tl) - i)):
            if tw[i + d] == tl[i]:
                found = d
                break
        if found is None:
            never += 1
        else:
            lags.append(found)
    turns = len(lags) + never
    if not turns:
        print(f"  {lead} -> {witness}: no turns")
        return
    print(f"  {lead} turns -> {witness} confirms   ({turns} turns)")
    if lags:
        print(f"    confirmed within {horizon} bars: {len(lags)}/{turns} "
              f"({len(lags)/turns:.0%})   median lag {statistics.median(lags):.0f} bars, "
              f"mean {statistics.mean(lags):.1f}")
    print(f"    never confirmed within {horizon} bars: {never}/{turns} "
          f"({never/turns:.0%})")


# ---------------------------------------------------------------------------

def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/vn_indices.tsv"
    series = load(path)

    print("=" * 78)
    print("EM-6 Phase 1 - is a multi-index confirmation gate vacuous on VN data?")
    print("=" * 78)
    for code, bars in sorted(series.items(), key=lambda kv: -len(kv[1])):
        print(f"  {code:12s} {len(bars):5d} bars  {bars[0].date} -> {bars[-1].date}")

    _self_check(series["VNINDEX"])
    print("\n  self-check: trailing-window regime == full-prefix regime  OK")

    print(f"\nPRE-REGISTERED: W1 corr <= {CORR_CEILING}, "
          f"W2 disagree >= {MIN_DISAGREE_SHARE:.0%}, "
          f"W3 median episode >= {MIN_EPISODE_BARS} bars")

    kept_trends: Dict[str, Dict[str, Sequence[str]]] = {}
    for label, fn in (("compute_regime (20/50 MA spread)", regime_series),
                      ("Dow swing rule (5%, closes only)", dow_series)):
        print("\n" + "-" * 78)
        print(f"TREND DEFINITION: {label}")
        print("-" * 78)
        print(f"{'pair':22s} {'n':>5s} {'corr':>6s} {'disagree':>9s} "
              f"{'med':>4s} {'max':>4s} {'eps':>4s} {'blocked':>8s}  verdict")
        trends = {code: fn(bars) for code, bars in series.items()}
        kept_trends[label] = trends
        passed = []
        for other in [c for c in series if c != "VNINDEX"]:
            row = compare("VNINDEX", series["VNINDEX"], other, series[other],
                          trends["VNINDEX"], trends[other])
            if row["skip"]:
                print(f"{row['pair']:22s} {row['n']:>5d}  too little overlap")
                continue
            ok, flags = verdict(row)
            if ok:
                passed.append(row["pair"])
            print(f"{row['pair']:22s} {row['n']:>5d} {row['corr']:>6.3f} "
                  f"{row['disagree_share']:>8.1%} {row['median_episode']:>4.0f} "
                  f"{row['max_episode']:>4d} {row['episodes']:>4d} "
                  f"{row['blocked_share']:>7.1%}  "
                  f"{'USABLE' if ok else 'no':6s} {flags}")
        print(f"  -> {len(passed)} usable witness(es): {passed or 'NONE'}")

    print("\n" + "-" * 78)
    print("WITNESS INDEPENDENCE - daily-return correlation, every pair")
    print("-" * 78)
    corr_matrix(series)

    for label, trends in kept_trends.items():
        print("\n" + "-" * 78)
        print(f"HARMONIC CONVERGENCE - {label}")
        print("-" * 78)
        convergence(series, trends, ["VNINDEX", "HNXINDEX", "UPCOMINDEX"])
        convergence(series, trends, ["VNINDEX", "HNXINDEX", "VN30"])

        print("\n  CONFIRMATION LAG (E&M: they need not confirm on the same day)")
        for w in ("HNXINDEX", "UPCOMINDEX", "VN30"):
            confirmation_lag(series, trends, "VNINDEX", w)

    print("\n" + "=" * 78)
    print("'blocked' = share of VNINDEX TREND_UP days the witness would not confirm")
    print("  (the gate's cost: signals it would suppress)")
    print("=" * 78)


if __name__ == "__main__":
    main()
