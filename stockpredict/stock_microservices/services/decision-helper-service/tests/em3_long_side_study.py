"""Backlog #86 — is EM-3's basing-point edge a LONG-SIDE effect?

    PYTHONPATH=. python3 tests/em3_long_side_study.py

Pre-registered in `docs/backlog86_em3_long_side.md`, Part 1, committed at
`a0e99f30` **before this file was written**. Nothing here may be tuned against
its own output.

The hypothesis and why it is tested on different symbols
-------------------------------------------------------
`#85` refuted the regime gate: the basing-point advantage was *higher* in
RANGE (+65.86) than in trend (+47.69). But its one negative bucket was
TREND_DOWN (−7.32), and TREND_DOWN entries are **79.6% shorts** (measured, not
assumed). E&M's Ch 28 procedure is written for an **advance**; the short-side
mirror is our translation. Hence: the edge may be long-side, not trend-side.

That hypothesis was generated from #85's data, so testing it there would
manufacture a finding. `#87`'s deep pull supplies the fix — **61 of the 92
deep-dump symbols have never been seen by #63, #84 or #85.**

Backlog #101 — gross AND net
----------------------------
`#86` reported GROSS, per `#80`, which pinned the metric at gross because a
flat commission came to 1.8x the result it was measuring. That is the right
choice for isolating the stop rule and the WRONG one for a shipping decision,
so `#101` adds NET beside it. They answer different questions and `#82` says
why in so many words: at these fee levels *"an arm wins on net by trading
less"*, and the basing-point arm trades 23% less by construction. Both are
printed, with commission paid per arm, so the net figure can be decomposed
instead of merely quoted.

Inference
---------
Gross P&L per trade (`#80`), **clustered by symbol** (`#84`): one observation
per symbol, paired across arms, t over 61 independent units. #85 used an
unpaired per-trade Welch, which treated ~1,300 trades from 12 symbols as
independent draws.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars
from app.services.signal.base import OHLCVBar

from tests.failed_signal_override_study import WARMUP, load_bars

DEEP = "/tmp/deep_bars.tsv"
SHALLOW = "/tmp/all_bars.tsv"
MIN_BARS = WARMUP + 90
MIN_TRADES_PER_SIDE = 2          # pre-registered exclusion rule
FILTER_PCT = 6.0                 # #84's primary value; NOT swept
SUBPERIOD_START = "2021-06-09"   # the shallow file's first bar

ARMS = {
    # Backlog #101 pinned this. The class default moved to "BASING_POINT" on
    # 2026-10-27, so the ATR control must say so explicitly — otherwise this
    # study would compare the basing point against itself and report ~0.
    "A_atr": {"trailing_stop_mode": "ATR"},
    "B_basing_both": {"trailing_stop_mode": "BASING_POINT"},
    "C_basing_long_only": {"trailing_stop_mode": "BASING_POINT_LONG_ONLY"},
}


def held_out_symbols() -> Tuple[Dict[str, List[OHLCVBar]], List[str]]:
    """The 61 symbols no EM-3 study has touched, recomputed rather than pasted.

    Derived from the two dumps so that a change to either is caught loudly
    here instead of silently shifting the sample — which is exactly what #85
    suffered when `MAX_SYMBOLS` moved under it.
    """
    deep = load_bars(DEEP)
    seen = set(load_bars(SHALLOW))
    held = sorted(s for s in deep
                  if s not in seen and len(deep[s]) >= MIN_BARS)
    return deep, held


def trades(bars: Sequence[OHLCVBar], **kw):
    cfg = BacktestConfig(
        ticker="T", start_date=bars[WARMUP].date, end_date=bars[-1].date,
        basing_point_filter_pct=FILTER_PCT, **kw,
    )
    return run_backtest_on_bars(cfg, bars).trade_ledger


#: Backlog #101. `gross_pnl` isolates the stop rule; `net_pnl` is what a user
#: actually keeps. Both are needed and they answer DIFFERENT questions — see
#: the module docstring and docs/backlog101_em3_net.md.
GROSS, NET = "gross_pnl", "net_pnl"


def mean_pnl(ledger, side: Optional[str], field: str = GROSS) -> Optional[float]:
    """Mean P&L per trade on one side, or None if too few to mean."""
    xs = [getattr(t, field) or 0.0 for t in ledger
          if side is None or t.direction == side]
    if len(xs) < MIN_TRADES_PER_SIDE:
        return None
    return sum(xs) / len(xs)


def total_pnl(ledger, side: Optional[str], field: str = GROSS) -> Optional[float]:
    """TOTAL gross P&L on one side, not a per-trade mean.

    POST-HOC DIAGNOSTIC, added after the pre-registered criterion had been
    computed and reported, and labelled as such. The reason it is needed: arm
    B takes **23% fewer trades** than arm A (18,586 against 24,225), because a
    wider stop both holds longer and sizes smaller. A per-trade mean can
    therefore flatter a rule that simply trades less, and `#80` fixed the
    metric at gross-per-trade for a different reason entirely (commission was
    1.8x the result it was measuring), so it never addressed this.

    Total P&L over the same period from the same starting equity is the
    economically meaningful quantity. If the advantage survives here it is not
    an artefact of trade count; if it does not, the per-trade framing is
    misleading and the headline has to change.
    """
    xs = [getattr(t, field) or 0.0 for t in ledger
          if side is None or t.direction == side]
    if len(xs) < MIN_TRADES_PER_SIDE:
        return None
    return sum(xs)


def days_held(ledger, side: Optional[str]) -> float:
    """Calendar days in the market — a crude exposure denominator."""
    out = 0.0
    for t in ledger:
        if side is not None and t.direction != side:
            continue
        if t.exit_date and t.entry_date:
            out += max(1, (t.exit_date - t.entry_date).days)
    return out


def paired_t(diffs: Sequence[float]) -> Tuple[float, Optional[float], int]:
    """(mean difference, paired t, n) over one-observation-per-symbol data."""
    n = len(diffs)
    if n < 2:
        return (sum(diffs) / n if n else 0.0), None, n
    m = sum(diffs) / n
    sd = math.sqrt(sum((d - m) ** 2 for d in diffs) / (n - 1))
    se = sd / math.sqrt(n)
    return m, (m / se if se else None), n


def compare(per_symbol: Dict[str, Dict[str, object]], left: str, right: str,
            side: Optional[str], stat=mean_pnl
            ) -> Tuple[float, Optional[float], int, int, int]:
    """`left` minus `right` on one side.

    Returns (edge, t, n used, n dropped, n symbols where left > right). The
    last is the sign count: #84 found EM-3's edge magnitude-driven and
    INCONSISTENT (54% of windows, sign test never significant), so a paired t
    alone would not say whether this replication is broad or tail-driven.
    """
    diffs: List[float] = []
    dropped = 0
    for sym, arms in per_symbol.items():
        a = stat(arms[left], side)
        b = stat(arms[right], side)
        if a is None or b is None:
            dropped += 1
            continue
        diffs.append(a - b)
    edge, t, n = paired_t(diffs)
    return edge, t, n, dropped, sum(1 for d in diffs if d > 0)


def total_commission(ledger) -> float:
    """What the arm actually paid. Backlog #101 reports it so the net result
    can be DECOMPOSED rather than just quoted: net edge = gross edge minus the
    commission difference, and #82 warns in so many words that at these fee
    levels "an arm wins on net by trading less"."""
    return sum(t.commission or 0.0 for t in ledger)


def counts(per_symbol, arm: str, side: Optional[str]) -> int:
    return sum(1 for arms in per_symbol.values() for t in arms[arm]
               if side is None or t.direction == side)


def run(bars_by_symbol: Dict[str, List[OHLCVBar]], symbols: List[str],
        label: str, since: Optional[str] = None) -> None:
    per_symbol: Dict[str, Dict[str, object]] = {}
    for i, sym in enumerate(symbols, 1):
        series = bars_by_symbol[sym]
        if since:
            series = [b for b in series if str(b.date) >= since]
        if len(series) < MIN_BARS:
            print(f"   [{i:>2}/{len(symbols)}] {sym}: {len(series)} bars, skipped",
                  flush=True)
            continue
        per_symbol[sym] = {name: trades(series, **kw) for name, kw in ARMS.items()}
        print(f"   [{i:>2}/{len(symbols)}] {sym}: "
              + "  ".join(f"{n}={len(v)}" for n, v in per_symbol[sym].items()),
              flush=True)

    print(f"\n{'=' * 78}\n{label}: {len(per_symbol)} symbols\n{'=' * 78}")
    print(f"{'arm':<22}{'trades':>9}{'longs':>9}{'shorts':>9}")
    for arm in ARMS:
        print(f"{arm:<22}{counts(per_symbol, arm, None):>9}"
              f"{counts(per_symbol, arm, 'LONG'):>9}"
              f"{counts(per_symbol, arm, 'SHORT'):>9}")

    print(f"\ngross P&L per trade, paired by symbol\n")
    print(f"{'comparison':<34}{'side':<8}{'edge':>10}{'t':>9}{'n':>5}{'drop':>6}"
          f"{'pos':>8}")
    rows = {}
    for key, (l, r, side) in {
        "long_B_vs_A": ("B_basing_both", "A_atr", "LONG"),
        "short_B_vs_A": ("B_basing_both", "A_atr", "SHORT"),
        "all_B_vs_A": ("B_basing_both", "A_atr", None),
        "long_C_vs_A": ("C_basing_long_only", "A_atr", "LONG"),
        "all_C_vs_A": ("C_basing_long_only", "A_atr", None),
        "all_C_vs_B": ("C_basing_long_only", "B_basing_both", None),
    }.items():
        edge, t, n, drop, pos = compare(per_symbol, l, r, side)
        rows[key] = (edge, t, n, drop)
        sig = "SIG" if t is not None and abs(t) > 1.96 else "ns"
        print(f"{l + ' - ' + r:<34}{str(side or 'all'):<8}{edge:>+10.2f}"
              f"{(t if t is not None else float('nan')):>+9.2f}{n:>5}{drop:>6}"
              f"{f'{pos}/{n}':>8} {sig}")

    lt = rows["long_B_vs_A"][1]
    se = rows["short_B_vs_A"][0]
    c1 = lt is not None and lt > 1.96
    c2 = se <= 0
    print("\nCRITERION (pre-registered, docs/backlog86_em3_long_side.md)")
    print(f"  1. LONG: basing point beats ATR, t > +1.96      -> "
          f"t={lt:+.2f}  {'PASS' if c1 else 'FAIL'}")
    print(f"  2. SHORT: basing point does NOT beat ATR, <= 0  -> "
          f"edge={se:+.2f}  {'PASS' if c2 else 'FAIL'}")
    print(f"  HYPOTHESIS: {'SUPPORTED' if (c1 and c2) else 'NOT SUPPORTED'}")
    if not c1:
        print("  NOTE: criterion 1 failing is the pre-stated 'bigger negative "
              "result' reading -\n        the EM-3 edge not replicating on unseen "
              "symbols at all.")

    # POST-HOC, and labelled: arm B takes ~23% fewer trades, so a per-trade mean
    # could flatter it. Total P&L over the same period is the economically
    # meaningful check. Not a criterion - the criterion is above and stands.
    print("\nPOST-HOC DIAGNOSTIC (not a criterion): TOTAL gross P&L per symbol,")
    print("because arm B trades ~23% less and a per-trade mean can reward that.")
    print(f"{'comparison':<34}{'side':<8}{'edge':>12}{'t':>9}{'n':>5}{'pos':>8}")
    for l, r, side in (
        ("B_basing_both", "A_atr", "LONG"),
        ("B_basing_both", "A_atr", "SHORT"),
        ("B_basing_both", "A_atr", None),
        ("C_basing_long_only", "B_basing_both", None),
    ):
        edge, t, n, _, pos = compare(per_symbol, l, r, side, stat=total_pnl)
        sig = "SIG" if t is not None and abs(t) > 1.96 else "ns"
        print(f"{l + ' - ' + r:<34}{str(side or 'all'):<8}{edge:>+12.0f}"
              f"{(t if t is not None else float('nan')):>+9.2f}{n:>5}"
              f"{f'{pos}/{n}':>8} {sig}")

    # -----------------------------------------------------------------------
    # Backlog #101 — NET. Pre-registered in docs/backlog101_em3_net.md: the
    # inference is #86's, unchanged; only the field changes.
    # -----------------------------------------------------------------------
    print("\n" + "-" * 78)
    print("Backlog #101 - NET of commission (0.15%/side) and sell tax (0.10%).")
    print("Inference inherited from #86 unchanged; only gross_pnl -> net_pnl.")
    print("-" * 78)
    print(f"{'arm':<22}{'commission':>14}{'per trade':>12}{'trades':>9}")
    for arm in ARMS:
        paid = sum(total_commission(a[arm]) for a in per_symbol.values())
        tr = counts(per_symbol, arm, None)
        print(f"{arm:<22}{paid:>14,.0f}{paid / max(1, tr):>12.2f}{tr:>9}")

    print(f"\n{'comparison':<34}{'side':<8}{'GROSS':>12}{'NET':>12}{'t net':>9}"
          f"{'n':>5}{'pos':>8}")
    net_rows = {}
    for key, (l, r, side) in {
        "long_B_vs_A": ("B_basing_both", "A_atr", "LONG"),
        "short_B_vs_A": ("B_basing_both", "A_atr", "SHORT"),
        "all_B_vs_A": ("B_basing_both", "A_atr", None),
        "all_C_vs_B": ("C_basing_long_only", "B_basing_both", None),
    }.items():
        g, _, _, _, _ = compare(per_symbol, l, r, side,
                                stat=lambda L, S: total_pnl(L, S, GROSS))
        n_edge, n_t, n_n, _, n_pos = compare(
            per_symbol, l, r, side, stat=lambda L, S: total_pnl(L, S, NET))
        net_rows[key] = (n_edge, n_t, n_pos, n_n)
        sig = "SIG" if n_t is not None and abs(n_t) > 1.96 else "ns"
        print(f"{l + ' - ' + r:<34}{str(side or 'all'):<8}{g:>+12.0f}"
              f"{n_edge:>+12.0f}{(n_t if n_t is not None else float('nan')):>+9.2f}"
              f"{n_n:>5}{f'{n_pos}/{n_n}':>8} {sig}")

    edge, t_net, pos, nn = net_rows["all_B_vs_A"]
    print("\n#101 DECISION INPUT (threshold fixed before the run):")
    print(f"  TOTAL NET P&L per symbol, basing point vs ATR: {edge:+,.0f} "
          f"t={t_net:+.2f}  {pos}/{nn} symbols")
    print(f"  -> net advantage positive AND t > +1.96: "
          f"{'YES' if (edge > 0 and t_net and t_net > 1.96) else 'NO'}")

    print("\nexposure (calendar days in market, all symbols pooled):")
    for arm in ARMS:
        d = sum(days_held(arms[arm], None) for arms in per_symbol.values())
        tr = counts(per_symbol, arm, None)
        print(f"   {arm:<22} days={d:>9.0f}  trades={tr:>6}  "
              f"days/trade={d / max(1, tr):>6.1f}")


if __name__ == "__main__":
    deep, held = held_out_symbols()
    print(f"deep dump {len(deep)} symbols; held out from #63/#84/#85: {len(held)}")
    if len(held) != 61:
        print(f"WARNING: pre-registration fixed 61 held-out symbols, got {len(held)}")
    print(f"{held}\n")
    run(deep, held, "PRIMARY - full held-out history")
    print("\n\nSECONDARY (diagnostic, not a criterion): post-2021 only, to "
          "separate a\nperiod effect from a symbol effect.")
    run(deep, held, f"SECONDARY - held-out symbols since {SUBPERIOD_START}",
        since=SUBPERIOD_START)
