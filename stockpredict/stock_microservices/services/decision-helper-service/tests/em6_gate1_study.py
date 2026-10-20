"""EM-6 D3 — GATE 1: does the confirmed primary trend predict anything at all?

    PYTHONPATH=. python3 tests/em6_gate1_study.py [indices.tsv] [symbols.tsv]

Not a test. The cheapest decisive measurement in the EM-6 plan, run **before**
any pipeline work, because a gate cannot improve signals by conditioning on a
state that carries no information about forward returns — and no amount of
wiring changes that.

PRE-REGISTERED CRITERION (plan §4, fixed before this file was written)
-----------------------------------------------------------------------
> Forward returns conditioned on the confirmed primary trend must separate:
> `TREND_UP`-confirmed days must beat `TREND_DOWN`-confirmed days at **two or
> more** of the 10/20/60-session horizons, with date-clustered significance
> and non-overlapping samples.
>
> **If this fails, stop.** Record the negative and close `#66`.

Declared **secondary** before running, so it cannot be promoted afterwards:
the same separation for the **ungated** lead trend. If gating adds nothing
over reading VNINDEX alone, the witnesses are pointless even where the trend
state itself predicts — and that, not the primary, is the question EM-6 exists
to answer.

Method, and why it is shaped this way
--------------------------------------
* **Date clustering (plan §3).** The treatment is market-wide: every symbol is
  gated on the same days, so (symbol, date) pairs are not independent and a
  trade-level t would be badly overstated. Collapsed to **one observation per
  date** — the equal-weighted mean forward return across the universe — which
  removes the cross-sectional correlation by construction rather than
  correcting for it afterwards.
* **Non-overlap.** Consecutive days' forward windows overlap almost entirely
  (the `#79` trap), so observations are taken greedily: every qualifying day
  is considered, and one is kept only if its window clears the last kept one.
  Every qualifying day, never a fixed stride — the `#87` defect, where a
  stride stepped over whole clustered episodes and returned n = 0 on *more*
  data.
* **Episode bootstrap.** The adopted trend changes ~21 times in 20 years, so
  the honest sample size is the number of **episodes**, not of observations.
  The confidence interval resamples whole episodes with replacement, and the
  episode count is reported beside every p-value (`#87`'s habit).
"""
from __future__ import annotations

import math
import os
import random
import statistics
import sys
from collections import defaultdict
from datetime import date as date_type
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.market_context.dow import TREND_DOWN, TREND_UP, swing_trend_series  # noqa: E402
from app.services.backtest.market_features import compute_regime  # noqa: E402
from app.services.market_context.dow_context import adopt_turns, market_context_series  # noqa: E402
from app.services.signal.base import OHLCVBar  # noqa: E402

HORIZONS = (10, 20, 60)
ALPHA = 0.05
BOOTSTRAP_DRAWS = 2000
RNG_SEED = 20261020


def load(path: str) -> Dict[str, List[OHLCVBar]]:
    series: Dict[str, List[OHLCVBar]] = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 7:
                continue
            code, day, o, h, l, c, v = parts[:7]
            series[code].append(OHLCVBar(
                date=date_type.fromisoformat(day), open=float(o), high=float(h),
                low=float(l), close=float(c), volume=int(float(v))))
    for code in series:
        series[code].sort(key=lambda b: b.date)
    return dict(series)


# ---------------------------------------------------------------------------
# forward returns, one observation per date
# ---------------------------------------------------------------------------

def basket_forward(symbols: Dict[str, List[OHLCVBar]],
                   dates: Sequence[date_type],
                   horizon: int) -> List[Optional[float]]:
    """Equal-weighted mean forward return across the universe, per lead date.

    Each symbol contributes its own `horizon`-session return measured on its
    own calendar, so a symbol that was not trading simply does not vote.
    """
    index: Dict[str, Dict[date_type, int]] = {
        sym: {b.date: i for i, b in enumerate(bars)} for sym, bars in symbols.items()
    }
    out: List[Optional[float]] = []
    for d in dates:
        rets = []
        for sym, bars in symbols.items():
            i = index[sym].get(d)
            if i is None or i + horizon >= len(bars):
                continue
            start, end = bars[i].close, bars[i + horizon].close
            if start > 0:
                rets.append(end / start - 1.0)
        out.append(statistics.fmean(rets) if rets else None)
    return out


def self_forward(bars: Sequence[OHLCVBar], horizon: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i in range(len(bars)):
        if i + horizon >= len(bars) or bars[i].close <= 0:
            out.append(None)
        else:
            out.append(bars[i + horizon].close / bars[i].close - 1.0)
    return out


# ---------------------------------------------------------------------------
# sampling and inference
# ---------------------------------------------------------------------------

def episode_ids(states: Sequence[str]) -> List[int]:
    ids, cur = [], 0
    for i, s in enumerate(states):
        if i and s != states[i - 1]:
            cur += 1
        ids.append(cur)
    return ids


def sample_arm(states: Sequence[str], forward: Sequence[Optional[float]],
               episodes: Sequence[int], want: str,
               horizon: int) -> List[Tuple[float, int]]:
    """Every qualifying day, kept only if its window clears the last kept one."""
    picked: List[Tuple[float, int]] = []
    last = -10 ** 9
    for i, s in enumerate(states):
        if s != want or forward[i] is None:
            continue
        if i - last < horizon:
            continue
        picked.append((forward[i], episodes[i]))
        last = i
    return picked


def welch(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    if len(a) < 2 or len(b) < 2:
        return None
    va, vb = statistics.variance(a), statistics.variance(b)
    se = math.sqrt(va / len(a) + vb / len(b))
    if se <= 0:
        return None
    return (statistics.fmean(a) - statistics.fmean(b)) / se


def episode_bootstrap(up: Sequence[Tuple[float, int]],
                      down: Sequence[Tuple[float, int]]) -> Optional[Tuple[float, float]]:
    """Resample whole episodes, because episodes are what repeat independently."""
    def group(obs):
        g = defaultdict(list)
        for v, e in obs:
            g[e].append(v)
        return list(g.values())

    gu, gd = group(up), group(down)
    if len(gu) < 2 or len(gd) < 2:
        return None
    rng = random.Random(RNG_SEED)
    diffs = []
    for _ in range(BOOTSTRAP_DRAWS):
        su = [v for _ in range(len(gu)) for v in rng.choice(gu)]
        sd = [v for _ in range(len(gd)) for v in rng.choice(gd)]
        if su and sd:
            diffs.append(statistics.fmean(su) - statistics.fmean(sd))
    if len(diffs) < 100:
        return None
    diffs.sort()
    lo = diffs[int(ALPHA / 2 * len(diffs))]
    hi = diffs[int((1 - ALPHA / 2) * len(diffs)) - 1]
    return lo, hi


def evaluate(label: str, states: Sequence[str],
             forwards: Dict[int, Sequence[Optional[float]]]) -> int:
    print(f"\n{label}")
    print(f"  {'h':>4s} {'n up':>5s} {'n dn':>5s} {'eps up':>7s} {'eps dn':>7s} "
          f"{'up ret':>8s} {'dn ret':>8s} {'edge':>8s} {'Welch t':>8s} "
          f"{'episode 95% CI':>22s}  verdict")
    episodes = episode_ids(states)
    passed = 0
    for h in HORIZONS:
        fwd = forwards[h]
        up = sample_arm(states, fwd, episodes, TREND_UP, h)
        dn = sample_arm(states, fwd, episodes, TREND_DOWN, h)
        if len(up) < 2 or len(dn) < 2:
            print(f"  {h:>4d} {len(up):>5d} {len(dn):>5d}   too few observations")
            continue
        uv = [v for v, _ in up]
        dv = [v for v, _ in dn]
        t = welch(uv, dv)
        ci = episode_bootstrap(up, dn)
        edge = statistics.fmean(uv) - statistics.fmean(dv)
        # Significant only if BOTH the t and the episode interval exclude zero.
        sig = (t is not None and abs(t) > 1.96 and ci is not None
               and (ci[0] > 0 or ci[1] < 0))
        if sig and edge > 0:
            passed += 1
        ci_s = f"[{ci[0]:+.2%}, {ci[1]:+.2%}]" if ci else "n/a"
        n_eu = len({e for _, e in up})
        n_ed = len({e for _, e in dn})
        print(f"  {h:>4d} {len(up):>5d} {len(dn):>5d} {n_eu:>7d} {n_ed:>7d} "
              f"{statistics.fmean(uv):>7.2%} {statistics.fmean(dv):>7.2%} "
              f"{edge:>7.2%} {t:>8.2f} {ci_s:>22s}  "
              f"{'SIG' if sig else 'ns'}")
    print(f"  -> separates at {passed} of {len(HORIZONS)} horizons")
    return passed



def _regime_series(bars: Sequence[OHLCVBar], slow: int = 50) -> List[str]:
    """`compute_regime` per bar, causally. It reads only the trailing `slow`
    closes, so a trailing window is equivalent to the full prefix."""
    return [compute_regime(list(bars[max(0, i - slow):i]), fast=20, slow=slow)
            for i in range(1, len(bars) + 1)]


def _map(lead: Sequence[OHLCVBar], witness: Sequence[OHLCVBar],
         trends: Sequence[str]) -> List[Optional[str]]:
    """Witness reading as of each lead date; None before it starts."""
    out: List[Optional[str]] = []
    j = -1
    for bar in lead:
        while j + 1 < len(witness) and witness[j + 1].date <= bar.date:
            j += 1
        out.append(trends[j] if j >= 0 else None)
    return out


def main() -> None:
    idx_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/vn_indices.tsv"
    sym_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/deep_bars.tsv"

    indices = load(idx_path)
    symbols = load(sym_path)
    lead = indices["VNINDEX"]
    witnesses = {c: indices[c] for c in ("HNXINDEX", "UPCOMINDEX") if c in indices}

    print("=" * 108)
    print("EM-6 D3 / GATE 1 — does the confirmed primary trend predict forward returns?")
    print("=" * 108)
    print(f"  lead      VNINDEX  {len(lead)} bars  {lead[0].date} -> {lead[-1].date}")
    for c, b in witnesses.items():
        print(f"  witness   {c:11s} {len(b)} bars  {b[0].date} -> {b[-1].date}")
    print(f"  universe  {len(symbols)} symbols, "
          f"{sum(len(v) for v in symbols.values())} bars")
    print(f"\n  CRITERION: separation at >= 2 of {HORIZONS} horizons, "
          f"date-clustered, non-overlapping.")
    print("  Significance requires BOTH |Welch t| > 1.96 AND an episode "
          "bootstrap CI excluding zero.")

    dates = [b.date for b in lead]
    basket = {h: basket_forward(symbols, dates, h) for h in HORIZONS}
    own = {h: self_forward(lead, h) for h in HORIZONS}

    ctx = market_context_series(lead, witnesses)
    adopted = [c.adopted_trend for c in ctx]
    ungated = swing_trend_series(lead)

    print("\n" + "-" * 108)
    print("PRIMARY — the confirmed (gated) trend, universe forward returns")
    print("-" * 108)
    primary = evaluate("adopted trend (CONFIRM_2, default k)", adopted, basket)

    print("\n" + "-" * 108)
    print("SECONDARY (declared before running) — does gating add anything?")
    print("-" * 108)
    secondary = evaluate("ungated VNINDEX trend, universe forward returns",
                         ungated, basket)
    evaluate("adopted trend, VNINDEX's own forward returns", adopted, own)
    evaluate("ungated VNINDEX trend, VNINDEX's own forward returns", ungated, own)

    # Robustness, also declared before running: the plan (Q2) put both trend
    # rules behind a parameter and left the choice to measurement. If the MA
    # proxy separated where the Dow rule did not, the negative would be about
    # the RULE; if neither does, it is about the market.
    print("\n" + "-" * 108)
    print("ROBUSTNESS — the same question under the shipped MA regime proxy")
    print("-" * 108)
    ma = {code: _regime_series(bars)
          for code, bars in [("VNINDEX", lead)] + list(witnesses.items())}
    ma_aligned = {c: _map(lead, witnesses[c], ma[c]) for c in witnesses}
    ma_adopted = adopt_turns(ma["VNINDEX"], ma_aligned)
    ma_primary = evaluate("adopted trend (MA 20/50 proxy), universe forward returns",
                          ma_adopted, basket)
    evaluate("ungated MA regime, universe forward returns", ma["VNINDEX"], basket)

    print("\n" + "=" * 108)
    verdict = "PASS" if primary >= 2 else "FAIL"
    print(f"GATE 1: primary separates at {primary} of 3 horizons -> {verdict}")
    if verdict == "FAIL":
        print("  Pre-registered consequence: STOP. Record the negative and close #66.")
    print(f"  (secondary: ungated separates at {secondary} of 3 — "
          f"gating {'adds' if primary > secondary else 'adds nothing over'} "
          f"the lead alone)")
    print(f"  (robustness: the MA proxy separates at {ma_primary} of 3 — the "
          f"result is {'about the Dow rule' if ma_primary >= 2 else 'not specific to the Dow rule'})")
    print("=" * 108)


if __name__ == "__main__":
    main()
