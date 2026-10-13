"""EM-1 / S2 — the `FR-EM-V11` parameter sweep.

Not a test (no `test_` prefix, so pytest ignores it). Run explicitly:

    python3 -m tests.sweep_params            # the full sweep
    python3 -m tests.sweep_params --quick    # fewer surrogates

`CLAUDE.md` is blunt about this: every magnitude in the spec is illustrative,
E&M's own figures are 1940s-60s NYSE rules, and a default that has not been
swept is an inherited guess. This measures each one against the harnesses that
already exist rather than against a number from the book.

Three metrics, all properties rather than magnitudes:

  H1 separation   mean(volume_score | volume aligned with price)
                  minus mean(volume_score | volume permuted).
                  Larger is better: it is the degree to which the rule reads
                  the price-volume RELATIONSHIP rather than volume's level.

  H2 suppression  (mean composite - mean geometric) / mean geometric, over
                  random-walk surrogates. More negative is better: it is how
                  much confidence the layer withdraws from noise.

  Real spread     the verdict distribution on real symbols. A setting that
                  collapses to all-confirms or all-contradicts is useless
                  however well it scores above, so this is a veto, not a
                  score.
"""
from __future__ import annotations

import sys
from dataclasses import replace

import numpy as np

from app.services.patterns import volume as V
from tests.volume_harness import (
    adverse_frames,
    detect_all,
    planted_frames,
    random_walk_ohlcv,
    shuffle_volume,
    synthetic_volume,
)

QUICK = "--quick" in sys.argv
N_SURROGATES = 40 if QUICK else 120
SEED = 20261013


# --- metrics ---------------------------------------------------------------

def _verdicts(frame, window):
    out = []
    for m in detect_all(frame):
        v = V.evaluate_pattern_volume(m, frame, baseline_window=window)
        if v.score is not None:
            out.append((m, v))
    return out


def h1_separation(window):
    """Aligned minus shuffled, averaged over the planted set."""
    rng = np.random.default_rng(SEED)
    aligned, shuffled = [], []
    for pf in planted_frames():
        aligned += [v.score for _, v in _verdicts(pf.frame, window)]
        shuffled += [v.score for _, v in _verdicts(shuffle_volume(pf.frame, rng), window)]
    if not aligned or not shuffled:
        return float("nan")
    return float(np.mean(aligned) - np.mean(shuffled))


def textbook_vs_adverse(window):
    """The same statement on the hand-built pairs: identical geometry,
    opposite volume script. Independent of H1's permutation."""
    tb = {pf.name: pf for pf in planted_frames()}
    ad = {pf.name: pf for pf in adverse_frames()}
    gaps = []
    for name, a in ad.items():
        t = tb.get(name)
        if t is None:
            continue
        ts = [v.score for m, v in _verdicts(t.frame, window) if m.pattern_name == t.target_pattern]
        as_ = [v.score for m, v in _verdicts(a.frame, window) if m.pattern_name == a.target_pattern]
        if ts and as_:
            gaps.append(float(np.mean(ts) - np.mean(as_)))
    return float(np.mean(gaps)) if gaps else float("nan")


def h2_suppression(window, n=N_SURROGATES):
    """How much confidence the layer withdraws from pure noise."""
    rng = np.random.default_rng(SEED)
    geo, comp = [], []
    for _ in range(n):
        frame = random_walk_ohlcv(250, 0.015, synthetic_volume(250, rng), rng)
        for m in detect_all(frame):
            g = m.geometric_confidence if m.geometric_confidence is not None else m.confidence
            v = V.evaluate_pattern_volume(m, frame, baseline_window=window)
            geo.append(g)
            comp.append(min(1.0, max(0.0, g * v.factor)))
    if not geo:
        return float("nan")
    return (float(np.mean(comp)) - float(np.mean(geo))) / float(np.mean(geo))


def real_spread(window, bars_by_symbol):
    """Verdict distribution on real data — the veto metric."""
    import pandas as pd
    from collections import Counter
    counts = Counter()
    for sym, bars in bars_by_symbol.items():
        df = pd.DataFrame(bars, columns=["date", "open", "high", "low", "close", "volume"])
        df = df.tail(250).reset_index(drop=True)
        for m in detect_all(df):
            v = V.evaluate_pattern_volume(m, df, baseline_window=window)
            counts[v.evidence.get("verdict", "unknown")] += 1
    total = max(sum(counts.values()), 1)
    # The share held by the single most common verdict. 1.0 means the setting
    # says the same thing about everything, which is no information at all.
    return max(counts.values()) / total, dict(counts)


def load_real_bars(path="/tmp/s1_bars.tsv"):
    import collections
    rows = collections.defaultdict(list)
    try:
        for line in open(path):
            s, d, o, hi, lo, c, v = line.rstrip("\n").split("\t")
            rows[s].append((d, float(o), float(hi), float(lo), float(c), float(v)))
    except FileNotFoundError:
        return {}
    return rows


# --- the sweeps ------------------------------------------------------------

def sweep_baseline_window(real):
    print("\n## SRS open question 1 — baseline_window")
    print(f"{'window':>8} {'H1 sep':>9} {'tb-adv':>9} {'H2 suppr':>10} {'top verdict share':>19}")
    best = None
    for w in (20, 50, 100):
        sep, gap, sup = h1_separation(w), textbook_vs_adverse(w), h2_suppression(w)
        share, dist = real_spread(w, real) if real else (float("nan"), {})
        print(f"{w:>8} {sep:>9.4f} {gap:>9.4f} {sup:>+9.2%} {share:>18.0%}  {dist}")
        # Rank on H1 separation, with the real-data veto.
        if not np.isnan(sep) and (np.isnan(share) or share < 0.85):
            if best is None or sep > best[1]:
                best = (w, sep)
    print(f"  -> best separation among non-degenerate settings: baseline_window={best[0] if best else 'n/a'}")
    return best[0] if best else V.DEFAULT_BASELINE_WINDOW


def sweep_factor_bounds(window, real):
    print("\n## SRS open question 2 — volume_factor bounds (floor, ceiling)")
    print("  The bounds cannot change H1 separation or the verdict labels: they")
    print("  scale the FACTOR, not the score. So the question is only how much")
    print("  authority volume gets over the final confidence — measured as H2")
    print("  suppression, and bounded by how far a verdict may move a number.")
    print(f"{'floor':>7} {'ceiling':>9} {'H2 suppr':>10} {'max downgrade':>15} {'max upgrade':>13}")
    orig = (V.FACTOR_FLOOR, V.FACTOR_CEILING)
    rows = []
    for floor, ceil in ((0.4, 1.10), (0.5, 1.15), (0.6, 1.20), (0.5, 1.30), (0.7, 1.10)):
        V.FACTOR_FLOOR, V.FACTOR_CEILING = floor, ceil
        sup = h2_suppression(window, n=max(20, N_SURROGATES // 3))
        print(f"{floor:>7} {ceil:>9} {sup:>+9.2%} {1-floor:>14.0%} {ceil-1:>12.0%}")
        rows.append((floor, ceil, sup))
    V.FACTOR_FLOOR, V.FACTOR_CEILING = orig
    print(f"  -> current bounds {orig} kept unless a row below is clearly better")
    return rows


def sweep_confirm_rvol(window):
    print("\n## the governing rule threshold — confirm_rvol")
    print("  How much expansion counts as expansion. Swept on the GENERIC")
    print("  bullish/bearish breakout rules, which every unregistered pattern")
    print("  uses and which the per-detector rules inherit their shape from.")
    print(f"{'confirm_rvol':>13} {'H1 sep':>9} {'tb-adv':>9}")
    # PATTERN_RULES captured the BreakoutRule OBJECTS at import, so patching
    # V.BULLISH_BREAKOUT alone reaches nothing — the first version of this
    # sweep reported a perfectly flat curve for exactly that reason, which is
    # a sweep bug masquerading as "this parameter does not matter".
    # Every rule in the registry is rebuilt instead.
    import copy
    original = copy.deepcopy(V.PATTERN_RULES)
    out = []
    for r in (1.25, 1.5, 1.75, 2.0):
        for name, rule in list(V.PATTERN_RULES.items()):
            kw = {}
            if rule.breakout is not None:
                kw["breakout"] = replace(rule.breakout, confirm_rvol=r)
            if rule.breakout_by_direction is not None:
                kw["breakout_by_direction"] = {
                    d: replace(b, confirm_rvol=r,
                               suspect_above_rvol=(max(b.suspect_above_rvol, r * 1.2)
                                                   if b.suspect_above_rvol else None))
                    for d, b in rule.breakout_by_direction.items()
                }
            if kw:
                V.PATTERN_RULES[name] = replace(rule, **kw)
        sep, gap = h1_separation(window), textbook_vs_adverse(window)
        print(f"{r:>13} {sep:>9.4f} {gap:>9.4f}")
        out.append((r, sep, gap))
        V.PATTERN_RULES.clear()
        V.PATTERN_RULES.update(copy.deepcopy(original))
    return out


def sweep_climax(real):
    """Backlog #72 — the climax flag never fires on real data."""
    print("\n## Backlog #72 — the climax gates, measured on real bars")
    if not real:
        print("  (no real bars available; run the S1 extract first)")
        return
    print(f"{'rvol>=':>8} {'progress<=':>11} {'bars flagged':>13} {'symbols':>9}")
    for rvol_t in (1.5, 2.0, 2.5):
        for prog_t in (0.6, 1.0, 1.5):
            flagged = syms = 0
            for sym, bars in real.items():
                close = [b[4] for b in bars]
                vol = [b[5] for b in bars]
                hit = 0
                for i in range(V.LONG_BASELINE_WINDOW, len(bars)):
                    prior = [v for v in vol[i - V.LONG_BASELINE_WINDOW:i] if v > 0]
                    if len(prior) < 60:
                        continue
                    ref = V._percentile(prior, V.LONG_BASELINE_PERCENTILE)
                    if ref <= 0 or vol[i] / ref < rvol_t:
                        continue
                    moves = [abs(close[j] - close[j - 1])
                             for j in range(i - V.LONG_BASELINE_WINDOW + 1, i)]
                    typ = V._median(moves) if moves else 0.0
                    if typ <= 0:
                        continue
                    if abs(close[i] - close[i - 1]) / typ <= prog_t:
                        hit += 1
                flagged += hit
                syms += 1 if hit else 0
            print(f"{rvol_t:>8} {prog_t:>11} {flagged:>13} {syms:>9}")


if __name__ == "__main__":
    real = load_real_bars()
    print(f"EM-1 / S2 sweep — surrogates={N_SURROGATES}, real symbols={len(real)}")
    w = sweep_baseline_window(real)
    sweep_factor_bounds(w, real)
    sweep_confirm_rvol(w)
    sweep_climax(real)
