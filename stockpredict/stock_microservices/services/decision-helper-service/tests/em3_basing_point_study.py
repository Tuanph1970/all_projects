"""EM-3's mandatory C4 benchmark: the basing-point stop against the ATR trail.

    PYTHONPATH=. python3 tests/em3_basing_point_study.py

The register asked for this explicitly: "A/B against the shipped ATR trailing
stop in the existing backtest harness, on the same signals, reporting stop-out
frequency, average adverse excursion before exit, and expectancy. This is the
one candidate that produces a single comparable number."

The bench is only now clean. `#80` fixed books that did not reconcile and a
cost model that dominated every result; `#82` turned off an override that was
closing two thirds of positions before their stop was reached — which would
have made a *stop rule* unevaluable, since the treatment was barely applied.

CRITERION, FIXED BEFORE THE RUN
-------------------------------
The basing-point stop earns its place if **gross P&L per trade** is higher
than the ATR trail's, on the same signals.

Gross and per-trade for `#80`'s reason: at ~3x fees an arm wins on net purely
by trading less, and a wider stop holds positions longer by construction.

Reported alongside, not decisive: stop-out frequency (does it get hit less?),
holding period, and the exit mix. E&M's claim is specifically that a stop put
"where they're hard to get to" is *not taken out by a probe* — so stop-out
frequency falling while expectancy holds up is the mechanism, if it is there.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars

from tests.failed_signal_override_study import MAX_SYMBOLS, WARMUP, load_bars


def arm(bars_by_symbol, label: str, **kw) -> Dict[str, object]:
    trades = gross = net = 0.0
    n = wins = bars_seen = 0
    reasons: Counter = Counter()
    holds: List[int] = []
    per_trade: List[float] = []

    for sym in sorted(bars_by_symbol)[:MAX_SYMBOLS]:
        b = bars_by_symbol[sym]
        if len(b) < WARMUP + 90:
            continue
        cfg = BacktestConfig(ticker=sym, start_date=b[WARMUP].date,
                             end_date=b[-1].date, **kw)
        res = run_backtest_on_bars(cfg, b)
        n += res.stats.num_trades
        gross += res.stats.total_gross_pnl
        net += res.stats.total_net_pnl
        wins += res.stats.num_wins
        bars_seen += sum(1 for x in b if x.date >= cfg.start_date)
        for t in res.trade_ledger:
            reasons[t.exit_reason] += 1
            per_trade.append(t.gross_pnl or 0.0)
            if t.exit_date:
                holds.append((t.exit_date - t.entry_date).days)

    holds.sort()
    return {
        "label": label, "trades": n,
        "bars_per_trade": bars_seen / n if n else 0.0,
        "gross": gross, "gross_per_trade": gross / n if n else 0.0,
        "net": net, "win_rate": wins / n if n else 0.0,
        "median_hold": holds[len(holds) // 2] if holds else 0,
        "stop_rate": reasons["STOP_HIT"] / n if n else 0.0,
        "target_rate": reasons["TARGET_HIT"] / n if n else 0.0,
        "per_trade": per_trade,
    }


def welch(a: List[float], b: List[float]):
    if len(a) < 2 or len(b) < 2:
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return (ma - mb) / se if se else None


if __name__ == "__main__":
    bars = load_bars()
    arms = [
        arm(bars, "ATR trail (shipped)"),
        arm(bars, "Basing point (rules 1-3)", trailing_stop_mode="BASING_POINT"),
        arm(bars, "Basing point + rule 4", trailing_stop_mode="BASING_POINT",
            basing_point_new_high_rule=True),
    ]
    print(f"symbols={min(MAX_SYMBOLS, len(bars))}\n")
    for a in arms:
        print(f"{a['label']:26s} trades={a['trades']:5d}  bars/trade={a['bars_per_trade']:5.2f}  "
              f"median hold={a['median_hold']:3d}d")
        print(f"{'':26s} GROSS/TRADE={a['gross_per_trade']:8.2f}  win={a['win_rate']:.1%}  "
              f"stop-outs={a['stop_rate']:.1%}  targets={a['target_rate']:.1%}\n")

    base = arms[0]
    print("CRITERION (pre-registered): basing point earns its place only if "
          "gross/trade beats the ATR trail.")
    for a in arms[1:]:
        t = welch(a["per_trade"], base["per_trade"])
        diff = a["gross_per_trade"] - base["gross_per_trade"]
        verdict = ("BEATS IT" if diff > 0 and t is not None and abs(t) > 1.96
                   else "does not beat it")
        print(f"   {a['label']:26s} {diff:+8.2f} vs ATR   "
              f"Welch t={t:+.2f}   -> {verdict}" if t is not None else "   n/a")
