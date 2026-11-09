"""S-1/S-2 — run the momentum scanner over the real VN100 universe.

    PYTHONPATH=. python3 tests/s1_momentum_scan.py [bars.tsv] [YYYY-MM-DD] [--no-base] [--null]

Not a test. It is the CLI the S-1 phase delivers instead of an HTTP endpoint:
the ranking has to be judged against real charts before FR-SCAN-API, a nightly
job and a screen get built on top of it (SRS §9, S-3).

Input is the same seven-column TSV the EM studies read —
`symbol\\tdate\\topen\\thigh\\tlow\\tclose\\tvolume` — so the dump can come from
`stock_prices` or from `tests/deep_history_dump.py` without this script caring.
Produce one from the database with:

    docker exec stock_mysql mysql -ustockuser -p<pw> defaultdb -N --batch -e \\
      "SELECT c.symbol,p.date,p.open,p.high,p.low,p.close,p.volume
         FROM stock_prices p JOIN companies c ON c.id=p.company_id
        ORDER BY c.symbol,p.date" > bars.tsv

`--no-base` drops back to the S-1 funnel, which is how the two phases stay
comparable on the same data. `--null` adds the VT-4 random-walk false-positive
rate; it costs a minute, and C4/EC-S5 want it beside any candidate list that is
going to be acted on.

WHAT THIS IS NOT. Even with S-2 on, a candidate is a *setup*, not a trade: no
entry, stop or size (EC-S6), and no evidence yet that the setup has edge on VN
equities (VT-5). Read it as a shortlist to look at.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List

from app.services.scanner.null_model import estimate_null_fpr
from app.services.scanner.screen import ScanConfig, ScanReport, run_scan
from app.services.signal.base import OHLCVBar

#: One definition, shared with the API and the nightly job — three copies of
#: this list is how they stop agreeing about which seams are real (SRS 2.4).
from app.services.scanner.screen import KNOWN_PROVIDER_SEAMS as SEAM_ALLOWLIST

DEFAULT_TSV = "bars.tsv"


def load_bars(path: str) -> Dict[str, List[OHLCVBar]]:
    """Same seven-column reader as `tests/failed_signal_override_study.py`."""
    rows: Dict[str, List[OHLCVBar]] = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 7:
                continue
            sym, d, o, hi, lo, c, v = parts
            try:
                rows[sym].append(OHLCVBar(
                    date=datetime.strptime(d, "%Y-%m-%d").date(),
                    open=float(o), high=float(hi), low=float(lo),
                    close=float(c), volume=float(v),
                ))
            except ValueError:
                continue
    return dict(rows)


def report(r: ScanReport, cfg: ScanConfig) -> None:
    acc = r.accounting()
    print(f"\nS-1 momentum scan — as of {r.as_of}")
    print(f"  universe {r.universe_total} | required bars {r.required_bars} "
          f"| ranked {r.ranked_universe}")
    print(f"  floor {cfg.min_avg_daily_value/1e9:.0f} tỷ/phiên over "
          f"{cfg.liquidity_lookback} bars | horizons {list(cfg.horizons)} "
          f"| advance >= {cfg.min_prior_advance_pct:.0f}% over {cfg.advance_lookback}")

    print("\n  funnel")
    for label, key in (
        ("no bars", "no_bars"),
        ("short history", "insufficient_history"),
        ("price seam", "price_seam"),
        ("illiquid", "illiquid"),
        ("failed trend template", "failed_trend"),
        ("failed base / squeeze", "failed_base"),
        ("QUALIFIED (shown)", "candidates"),
        ("qualified (beyond cut)", "excess_qualified"),
    ):
        print(f"    {label:<24} {acc[key]:>4}")
    assert acc["accounted"] == acc["universe_total"], "symbols were lost in the funnel"
    print(f"    {'accounted':<24} {acc['accounted']:>4} / {acc['universe_total']}")

    if r.excluded_price_seam:
        print("\n  excluded for a price seam (run POST /stocks/{sym}/repair-history):")
        for s in r.excluded_price_seam:
            print(f"    {s.symbol:<5} {s.bar_date}  {s.prev_close:>8.2f} -> {s.close:>8.2f}"
                  f"  {s.move_pct:+7.2f}%")
    if r.flagged_price_seam:
        print("\n  seam flagged, NOT excluded (survived a re-pull — provider data):")
        for s in r.flagged_price_seam:
            print(f"    {s.symbol:<5} {s.bar_date}  {s.move_pct:+7.2f}%")

    hs = list(cfg.horizons)
    print(f"\n  candidates (composite = mean percentile across {hs})")
    head = (f"    {'#':>2}  {'sym':<5} {'comp':>5} " +
            " ".join(f"{str(h)+'b':>8}" for h in hs) + "  " +
            " ".join(f"{'pct'+str(h):>6}" for h in hs) +
            f"  {'adv%':>6} {'tỷ/phiên':>9}")
    print(head)
    print("    " + "-" * (len(head) - 4))
    for c in r.candidates:
        m, t = c.momentum, c.trend
        print(f"    {c.rank:>2}  {c.symbol:<5} {m.composite:>5.2f} "
              + " ".join(f"{m.returns[h]:>+7.1f}%" for h in hs) + "  "
              + " ".join(f"{m.percentiles[h]:>6.2f}" for h in hs)
              + f"  {t.prior_advance_pct:>5.0f}% "
              + f"{c.liquidity.avg_daily_value*cfg.price_unit_vnd/1e9:>8.1f}")

    from collections import Counter
    for label, group in (("the trend template", r.failed_trend),
                         ("the base stage", r.failed_base)):
        if not group:
            continue
        reasons: Counter = Counter()
        for item in group:
            for name in item.failed_clauses():
                reasons[name] += 1
        print(f"\n  why names failed {label} (a name can fail several)")
        for name, n in reasons.most_common():
            print(f"    {name:<24} {n:>4}")


def main(argv: List[str]) -> int:
    path = argv[1] if len(argv) > 1 else DEFAULT_TSV
    bars = load_bars(path)
    if not bars:
        print(f"no bars loaded from {path}", file=sys.stderr)
        return 1

    as_of = (datetime.strptime(argv[2], "%Y-%m-%d").date() if len(argv) > 2
             else max(b.date for s in bars.values() for b in s))

    cfg = ScanConfig(seam_allowlist=SEAM_ALLOWLIST,
                     require_base="--no-base" not in argv)
    report(run_scan(bars, as_of, cfg), cfg)

    if "--null" in argv:
        # C4 / EC-S5: the candidate list is reported BESIDE the rate at which
        # the same funnel fires on random walks. A low number here proves
        # selectivity against noise and nothing at all about edge — that is
        # VT-5, and it needs months of live runs.
        n = estimate_null_fpr(run_scan, cfg, trials=30,
                              universe_size=len(bars), bars_per_symbol=400)
        print(f"\n  VT-4 null false-positive rate ({n.trials} random-walk universes "
              f"of {n.universe_size}, VN-calibrated 2.405% daily SD)")
        print(f"    universes emitting any candidate  {n.trials_with_candidates:>4} / {n.trials}"
              f"   ({n.trial_fpr:.1%})")
        print(f"    synthetic symbols admitted        {n.total_candidates:>4} / {n.symbols_tested}"
              f"   ({n.symbol_fpr:.2%})")
        print("    a low rate shows selectivity against noise, NOT edge (VT-5)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
