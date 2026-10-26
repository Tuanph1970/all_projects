"""Backlog #58 — does VCI adjust its price history for CASH dividends?

    python3 tests/backlog58_cash_dividend_adjustment.py [divs.tsv] [bars.tsv] [indices.tsv]

Not a test: a determination. Share-count adjustment is already proven (`#56`),
but cash-dividend treatment was unknown and the UI discloses it as such. It
became answerable only once `#59` made the dividend history available.

The mechanism
-------------
On an ex-dividend date the share drops by roughly the dividend, because the
buyer no longer receives it. So:

* an **unadjusted** series shows that drop in its close-to-close return;
* a **back-adjusted** series has scaled the earlier prices down, so the drop
  is gone and the recorded return across the ex-date carries no trace of it.

PRE-REGISTERED CRITERION (fixed before the first run)
------------------------------------------------------
Per event, measure the **market-excess** return across the ex-date —
the stock's return minus VNINDEX's on the same day, because ex-dates cluster
around results season and a market move would otherwise contaminate the
estimate.

> **UNADJUSTED** if mean excess return on ex-dates is significantly negative
> (t < −2) **and** its magnitude is at least **half** the mean dividend yield.
>
> **ADJUSTED** if mean excess return on ex-dates is indistinguishable from the
> ordinary-day control **and** clearly smaller than the mean yield.
>
> Anything else is reported as **inconclusive**, not forced into a verdict.

A regression of excess return on **−yield** is reported alongside: a slope
near 1 means the whole drop is present (unadjusted), near 0 means none of it
is (adjusted). The slope is the sharper statistic because it uses each
event's own size rather than an average.

Units, which matter here
------------------------
`value` is VND per share (1,850.0). The bar file is in **thousands** of VND
(VNM 8.04 = 8,040), so the yield is `value / (close * 1000)`. Getting this
wrong by 1000x would make every dividend look negligible and return a false
"adjusted".

Two dividends can share one ex-date (VNM paid 2,500 and 350 on 2025-10-16),
so amounts are **aggregated per (symbol, ex-date)** before anything else.
"""
from __future__ import annotations

import math
import statistics
import sys
from collections import defaultdict

PRICE_SCALE = 1000.0          # bar file is in thousands of VND

#: Only events from this date are used for the YIELD, and the reason is a flaw
#: the first run exposed: it reported a mean yield of 9.61%, which is
#: impossible for VN cash dividends (1-5%).
#:
#: The dividend amounts are NOMINAL VND of their day, while the price series is
#: BACK-ADJUSTED (`#56`), so historical closes are scaled far down — VNM shows
#: 8.04 in 2007. Dividing a nominal 2007 dividend by a back-adjusted 2007 price
#: inflates the ratio several-fold. Recent events are unaffected, because
#: little adjustment has accumulated since.
#:
#: Note this does NOT affect the headline evidence: the ABSENCE of any ex-date
#: drop is measured from returns alone and needs no yield at all.
YIELD_WINDOW_FROM = "2024-01-01"
MIN_EVENTS = 50
T_CRITICAL = 2.0


def load_bars(path):
    bars = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 6:
                bars[p[0]].append((p[1], float(p[5])))
    for s in bars:
        bars[s].sort()
    return bars


def load_index(path, code="VNINDEX"):
    out = {}
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 6 and p[0] == code:
                out[p[1]] = float(p[5])
    return out


def load_divs(path):
    agg = defaultdict(float)
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                # aggregated per (symbol, ex-date): two payments can share one
                agg[(p[0], p[1][:10])] += float(p[2])
    return agg


def _returns(series):
    """date -> (return, prev_close), for every day with a predecessor."""
    out = {}
    for i in range(1, len(series)):
        d, c = series[i]
        _, prev = series[i - 1]
        if prev > 0 and c > 0:
            out[d] = (c / prev - 1.0, prev)
    return out


def mean_t(xs):
    if len(xs) < 3:
        return None, None
    m = statistics.fmean(xs)
    sd = statistics.stdev(xs)
    if sd <= 0:
        return m, None
    return m, m / (sd / math.sqrt(len(xs)))


def ols_slope(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    vx = sum((a - mx) ** 2 for a in x)
    if vx <= 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / vx


def main():
    divs_p = sys.argv[1] if len(sys.argv) > 1 else "/tmp/divs.tsv"
    bars_p = sys.argv[2] if len(sys.argv) > 2 else "/tmp/deep_bars.tsv"
    idx_p = sys.argv[3] if len(sys.argv) > 3 else "/tmp/vn_indices.tsv"

    bars = load_bars(bars_p)
    index = load_index(idx_p)
    divs = load_divs(divs_p)
    idx_ret = {}
    idx_series = sorted(index.items())
    for i in range(1, len(idx_series)):
        d, c = idx_series[i]
        _, prev = idx_series[i - 1]
        if prev > 0:
            idx_ret[d] = c / prev - 1.0

    print("=" * 94)
    print("Backlog #58 — does VCI adjust price history for CASH dividends?")
    print("=" * 94)
    print(f"  dividend events loaded: {len(divs)} (aggregated per symbol+ex-date)")
    print(f"  symbols with bars: {len(bars)} | VNINDEX days: {len(idx_ret)}")
    print(f"  CRITERION: unadjusted if mean excess < 0 at t < -{T_CRITICAL:.0f} AND "
          f"|mean excess| >= half the mean yield")
    print(f"             adjusted if indistinguishable from the control AND "
          f"clearly below the yield\n")

    ex_excess, ex_yield, ctrl_excess = [], [], []
    recent_yield, recent_excess = [], []
    matched = skipped = 0

    for sym, series in bars.items():
        rets = _returns(series)
        sym_ex_dates = set()
        for (s, day), amount in divs.items():
            if s != sym or day not in rets:
                continue
            r, prev = rets[day]
            mkt = idx_ret.get(day)
            if mkt is None:
                skipped += 1
                continue
            y = amount / (prev * PRICE_SCALE)
            if not (0 < y < 0.5):          # a >50% "yield" is a data error
                skipped += 1
                continue
            ex_excess.append(r - mkt)
            ex_yield.append(y)
            if day >= YIELD_WINDOW_FROM:
                recent_yield.append(y)
                recent_excess.append(r - mkt)
            sym_ex_dates.add(day)
            matched += 1
        # control: every other day of the same symbol
        for day, (r, _prev) in rets.items():
            if day in sym_ex_dates:
                continue
            mkt = idx_ret.get(day)
            if mkt is not None:
                ctrl_excess.append(r - mkt)

    print(f"  matched events: {matched}   skipped: {skipped}   "
          f"control days: {len(ctrl_excess)}")
    if matched < MIN_EVENTS:
        print(f"\n  TOO FEW EVENTS (<{MIN_EVENTS}) — INCONCLUSIVE")
        return

    m_ex, t_ex = mean_t(ex_excess)
    m_ct, _ = mean_t(ctrl_excess)
    m_y = statistics.fmean(ex_yield)
    diff = [e - m_ct for e in ex_excess]
    _, t_diff = mean_t(diff)
    slope = ols_slope([-y for y in ex_yield], ex_excess)

    m_y_recent = statistics.fmean(recent_yield) if recent_yield else float("nan")
    m_ex_recent, t_ex_recent = mean_t(recent_excess)
    slope_recent = ols_slope([-y for y in recent_yield], recent_excess)

    print("\n" + "-" * 94)
    print(f"  mean 'yield' over ALL events         {m_y:+.4%}  <- INFLATED, see "
          f"YIELD_WINDOW_FROM")
    print(f"  mean yield, events since {YIELD_WINDOW_FROM}  {m_y_recent:+.4%}  "
          f"({len(recent_yield)} events) <- trustworthy")
    if m_ex_recent is not None:
        print(f"  mean EXCESS return, those events     {m_ex_recent:+.4%}   "
              f"(t = {t_ex_recent:+.2f})")
    if slope_recent is not None:
        print(f"  slope on -yield, those events        {slope_recent:+.3f}")
    print(f"  mean EXCESS return on ex-dates       {m_ex:+.4%}   (t = {t_ex:+.2f})")
    print(f"  mean EXCESS return, ordinary days    {m_ct:+.4%}   (control)")
    print(f"  ex-date minus control                {m_ex - m_ct:+.4%}   "
          f"(t = {t_diff:+.2f})")
    print(f"  regression slope of excess on -yield {slope:+.3f}   "
          f"(1 = full drop present, 0 = none)")

    drop = m_ex - m_ct
    # the trustworthy yield, per YIELD_WINDOW_FROM
    y_ref = m_y_recent if recent_yield else m_y
    unadjusted = (t_diff is not None and t_diff < -T_CRITICAL
                  and abs(drop) >= 0.5 * y_ref)
    adjusted = (t_diff is not None and abs(t_diff) < T_CRITICAL
                and abs(drop) < 0.5 * y_ref)

    print("\n" + "=" * 94)
    if unadjusted:
        print("  VERDICT: UNADJUSTED — the ex-dividend drop is present in the series.")
        print(f"  Scored returns understate total return by roughly the yield "
              f"({y_ref:.2%} per event).")
    elif adjusted:
        print("  VERDICT: ADJUSTED — no ex-dividend drop survives in the series.")
        print("  Scored returns already include cash dividends; nothing to add back.")
    else:
        print("  VERDICT: INCONCLUSIVE — reported, not forced.")
    print("=" * 94)


if __name__ == "__main__":
    main()
