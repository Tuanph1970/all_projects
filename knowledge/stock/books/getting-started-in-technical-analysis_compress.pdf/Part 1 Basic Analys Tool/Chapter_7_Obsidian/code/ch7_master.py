"""
Chapter 7 — "Is Chart Analysis Still Valid?"
Master code file: implements every concept in the chapter and generates
all illustrations used in the Obsidian notes.

Source: Schwager, J.D. — Getting Started in Technical Analysis (Wiley, 1999),
        Chapter 7, pp. 120-126.

The running example throughout the chapter is the September 1992 Eurodollar
contract, which in 1991 was assumed to have entered a trading range. Three
breakout trades occurred: the first two were false breakouts (small losses),
the third was a real breakout (large profit).  This file recreates that
scenario with synthetic but realistic data so every illustration is
reproducible.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from dataclasses import dataclass
from typing import List, Optional, Tuple

# ----------------------------------------------------------------------------
# 0. Synthetic Eurodollar-style price series
# ----------------------------------------------------------------------------
# We construct a series that reproduces the qualitative behaviour described
# in Figures 7.1, 7.2, 7.3:
#   • A trading range from ~Mar 1991 through ~Aug 1991
#   • A false upside breakout (~Mar 1991) -> small loss
#   • A false downside breakout (~May 1991) -> small loss
#   • A real upside breakout (~Aug 1991) -> sustained advance
# Prices are in Eurodollar index points (100 - yield); a 1-point move = 100
# bp = $2,500 per contract (we'll use $2,500/pt throughout).

def make_eurodollar_series(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = 260                                   # ~1 year of trading days
    dates = pd.date_range("1991-03-01", periods=n, freq="B")

    # Phase 1 (days 0-40):    trading range around 92.0 ± 0.4
    # Phase 2 (days 41-55):   false upside breakout above 92.4 then back inside
    # Phase 3 (days 56-110):  trading range widens, drifts
    # Phase 4 (days 111-125): false downside breakout below 91.5 then back inside
    # Phase 5 (days 126-260): real upside breakout above 92.6 -> sustained rally
    close = np.empty(n)
    close[0] = 92.0
    for t in range(1, n):
        if t < 40:                                            # range
            target, k, vol = 92.0, 0.10, 0.06
        elif t < 55:                                          # false upside
            target = 92.55 if t < 48 else 91.95
            k, vol = 0.18, 0.08
        elif t < 110:                                         # range again
            target, k, vol = 92.0, 0.08, 0.07
        elif t < 125:                                         # false downside
            target = 91.40 if t < 118 else 92.05
            k, vol = 0.18, 0.09
        elif t < 135:                                         # consolidation
            target, k, vol = 92.10, 0.10, 0.07
        else:                                                 # real rally
            target, k, vol = 92.0 + 0.025 * (t - 135), 0.06, 0.08
        close[t] = close[t-1] + k * (target - close[t-1]) + rng.normal(0, vol)

    high = close + rng.uniform(0.05, 0.15, n)
    low  = close - rng.uniform(0.05, 0.15, n)
    open_ = np.r_[close[0], close[:-1]] + rng.normal(0, 0.05, n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close}, index=dates
    )

# ----------------------------------------------------------------------------
# 1. Concept 1 — Skepticism / "Is Chart Analysis Still Valid?"
# ----------------------------------------------------------------------------
def illustrate_skepticism(df: pd.DataFrame, out: str) -> None:
    """
    A conceptual chart contrasting the *naive view* ("everyone reads charts
    so they can't work") with the *informed view* ("interpretation is an art
    that survives publicity"). We simply annotate the price chart with the
    three classic objections and Schwager's response.
    """
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df.index, df["close"], color="#1f4e79", lw=1.3)
    ax.set_title("Chapter 7 — The Skeptic's Challenge to Chart Analysis",
                 fontsize=12)
    objections = [
        ("Too simple to work?",          0.02, 0.92),
        ("Stops easily triggered?",      0.34, 0.92),
        ("Too well publicized?",         0.66, 0.92),
    ]
    for txt, x, y in objections:
        ax.text(x, y, txt, transform=ax.transAxes,
                fontsize=10, color="#a23b3b",
                bbox=dict(boxstyle="round", fc="#fff2f2", ec="#a23b3b"))
    ax.text(0.5, 0.05,
            "Schwager's answer: 5 reasons charts still work in skilled hands",
            transform=ax.transAxes, ha="center",
            fontsize=11, color="#1a6e1a", weight="bold",
            bbox=dict(boxstyle="round", fc="#eaffea", ec="#1a6e1a"))
    ax.set_ylabel("Price")
    ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


# ----------------------------------------------------------------------------
# 2. Concept 2 — Risk Control: win rate < 50% can still be profitable
# ----------------------------------------------------------------------------
@dataclass
class Trade:
    entry_date: pd.Timestamp
    exit_date:  pd.Timestamp
    entry_px:   float
    exit_px:    float
    direction:  int                 # +1 long, -1 short
    pnl_pts:    float

def simulate_breakout_strategy(
    df: pd.DataFrame, lookback: int = 30, stop_to_mid: bool = True
) -> List[Trade]:
    """
    Schwager's exact Ch. 7 setup:
      • Build a trading range from the last `lookback` daily highs/lows.
      • Buy on a CLOSE above the range; sell on a CLOSE below.
      • Stop = midpoint of the range that was active at entry.
      • If signal reverses (close on the other side of midpoint after stop),
        widen the range and look for the next breakout.
    """
    trades: List[Trade] = []
    in_pos = 0                       # current position direction
    entry_date = entry_px = stop = None

    for i in range(lookback, len(df)):
        window = df.iloc[i - lookback:i]
        hi, lo = window["high"].max(), window["low"].min()
        mid    = 0.5 * (hi + lo)
        c      = df["close"].iat[i]
        d      = df.index[i]

        if in_pos == 0:
            if c > hi:                                # upside breakout
                in_pos, entry_date, entry_px, stop = +1, d, c, mid
            elif c < lo:                              # downside breakout
                in_pos, entry_date, entry_px, stop = -1, d, c, mid
        else:                                         # already in a trade
            stopped = (in_pos == +1 and c < stop) or (in_pos == -1 and c > stop)
            if stopped:
                pnl = (c - entry_px) * in_pos
                trades.append(Trade(entry_date, d, entry_px, c, in_pos, pnl))
                in_pos = 0

    # Mark-to-market a position still open at the end
    if in_pos != 0:
        last = df.iloc[-1]
        pnl  = (last["close"] - entry_px) * in_pos
        trades.append(Trade(entry_date, df.index[-1], entry_px,
                            last["close"], in_pos, pnl))
    return trades

def illustrate_risk_control(df: pd.DataFrame, trades: List[Trade], out: str
                            ) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df.index, df["close"], color="#1f4e79", lw=1.0, label="Close")
    cum = 0.0
    for k, t in enumerate(trades, 1):
        col = "#1a6e1a" if t.pnl_pts > 0 else "#a23b3b"
        ax.scatter(t.entry_date, t.entry_px, marker="^" if t.direction == 1
                   else "v", color=col, s=80, zorder=5)
        ax.scatter(t.exit_date,  t.exit_px,  marker="x", color=col,
                   s=80, zorder=5)
        cum += t.pnl_pts
        ax.annotate(f"#{k}\n{t.pnl_pts:+.2f}pt",
                    xy=(t.exit_date, t.exit_px),
                    xytext=(0, 18 if t.direction == 1 else -28),
                    textcoords="offset points",
                    fontsize=8, color=col, ha="center")
    win = sum(1 for t in trades if t.pnl_pts > 0)
    ax.set_title(
        f"Risk Control — {len(trades)} trades, "
        f"{win}/{len(trades)} winners, net {cum:+.2f}pt "
        f"(${cum*2500:+,.0f} per contract)", fontsize=11
    )
    ax.set_ylabel("Eurodollar index")
    ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


# ----------------------------------------------------------------------------
# 3. Concept 3 — Confirmation Conditions
# ----------------------------------------------------------------------------
def simulate_with_confirmation(
    df: pd.DataFrame, lookback: int = 30, wait_days: int = 3
) -> List[Trade]:
    """
    Schwager's two-rule confirmation:
      a. Wait `wait_days` after the breakout signal.
      b. Enter only if `wait_days` after the signal, price is STILL on the
         breakout side of the original range boundary.
    Otherwise, abandon the signal (it was a false breakout).
    """
    trades: List[Trade] = []
    in_pos = 0
    pending: Optional[dict] = None
    entry_date = entry_px = stop = None

    for i in range(lookback, len(df)):
        window = df.iloc[i - lookback:i]
        hi, lo = window["high"].max(), window["low"].min()
        mid    = 0.5 * (hi + lo)
        c      = df["close"].iat[i]
        d      = df.index[i]

        # Look for a fresh signal only if flat & nothing pending
        if in_pos == 0 and pending is None:
            if c > hi:
                pending = dict(dir=+1, signal_idx=i,
                               level=hi, mid=mid)
            elif c < lo:
                pending = dict(dir=-1, signal_idx=i,
                               level=lo, mid=mid)

        # Evaluate pending signal
        elif pending is not None and in_pos == 0:
            days_since = i - pending["signal_idx"]
            if days_since >= wait_days:
                # Confirmation: still on the breakout side of original level
                confirmed = (
                    (pending["dir"] == +1 and c > pending["level"]) or
                    (pending["dir"] == -1 and c < pending["level"])
                )
                if confirmed:
                    in_pos     = pending["dir"]
                    entry_date = d
                    entry_px   = c
                    stop       = pending["mid"]
                pending = None        # always retire pending after wait

        # Manage active trade
        elif in_pos != 0:
            stopped = (in_pos == +1 and c < stop) or (in_pos == -1 and c > stop)
            if stopped:
                pnl = (c - entry_px) * in_pos
                trades.append(Trade(entry_date, d, entry_px, c, in_pos, pnl))
                in_pos = 0

    if in_pos != 0:
        last = df.iloc[-1]
        pnl  = (last["close"] - entry_px) * in_pos
        trades.append(Trade(entry_date, df.index[-1], entry_px,
                            last["close"], in_pos, pnl))
    return trades

def illustrate_confirmation(
    df: pd.DataFrame,
    trades_no_conf: List[Trade], trades_with_conf: List[Trade], out: str
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for ax, trs, title in zip(
        axes,
        [trades_no_conf, trades_with_conf],
        ["No confirmation: every breakout taken (false signals included)",
         "With confirmation (3-day wait + close beyond ref-extreme)"]
    ):
        ax.plot(df.index, df["close"], color="#1f4e79", lw=1.0)
        for t in trs:
            col = "#1a6e1a" if t.pnl_pts > 0 else "#a23b3b"
            ax.scatter(t.entry_date, t.entry_px,
                       marker="^" if t.direction == 1 else "v",
                       color=col, s=70, zorder=5)
            ax.scatter(t.exit_date, t.exit_px, marker="x",
                       color=col, s=70, zorder=5)
        net = sum(t.pnl_pts for t in trs)
        win = sum(1 for t in trs if t.pnl_pts > 0)
        ax.set_title(f"{title}  →  {win}/{len(trs)} wins, net {net:+.2f}pt",
                     fontsize=10)
        ax.grid(alpha=0.25)
    axes[1].set_xlabel("Date")
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


# ----------------------------------------------------------------------------
# 4. Concept 4 — Putting Chart Patterns in Context (Multi-timeframe)
# ----------------------------------------------------------------------------
def to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    return df["close"].resample("W").last().to_frame("close")

def illustrate_multi_timeframe(df: pd.DataFrame, out: str) -> None:
    weekly = to_weekly(df)
    # Build a synthetic 5-year weekly series for context: take the daily
    # series and prepend several years of slow uptrend (Schwager's Fig 7.4
    # showed Eurodollar at the top of a 5-year range).
    hist_dates = pd.date_range(end=weekly.index[0] - pd.Timedelta(days=7),
                               periods=260, freq="W")
    rng = np.random.default_rng(11)
    hist = 88.0 + np.cumsum(rng.normal(0.015, 0.18, len(hist_dates)))
    hist = pd.Series(hist, index=hist_dates).to_frame("close")
    weekly_full = pd.concat([hist, weekly])

    fig, axes = plt.subplots(2, 1, figsize=(11, 7))
    # Top: long-term weekly view
    axes[0].plot(weekly_full.index, weekly_full["close"], color="#1f4e79")
    axes[0].axhspan(weekly_full["close"].min(),
                    weekly_full["close"].max(),
                    alpha=0.06, color="#1f4e79")
    axes[0].axhline(weekly_full["close"].rolling(52).max().iloc[-1],
                    color="#a23b3b", ls="--", lw=1)
    axes[0].set_title(
        "Weekly (long-term) view: market sits near top of multi-year range "
        "→ context says BIAS = LONG", fontsize=10)
    axes[0].grid(alpha=0.25)

    # Bottom: short-term daily view
    axes[1].plot(df.index, df["close"], color="#1f4e79")
    axes[1].set_title(
        "Daily (short-term) view: looks like a trading range — but in "
        "context, only LONG breakouts deserve action", fontsize=10)
    axes[1].grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


# ----------------------------------------------------------------------------
# 5. Concept 5 — Knowledge of Fundamentals (filtered signals)
# ----------------------------------------------------------------------------
def filter_by_fundamental(trades: List[Trade], bias: int) -> List[Trade]:
    """Accept only trades whose direction matches the fundamental bias.
       bias = +1 (bullish), -1 (bearish), 0 (neutral, accept all)."""
    if bias == 0:
        return list(trades)
    return [t for t in trades if t.direction == bias]

def illustrate_fundamentals(
    df: pd.DataFrame, trades_all: List[Trade], trades_filtered: List[Trade],
    bias: int, out: str
) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df.index, df["close"], color="#1f4e79", lw=1.0)
    for t in trades_all:
        kept = t in trades_filtered
        col = "#1a6e1a" if t.pnl_pts > 0 else "#a23b3b"
        alpha = 1.0 if kept else 0.25
        ax.scatter(t.entry_date, t.entry_px,
                   marker="^" if t.direction == 1 else "v",
                   color=col, alpha=alpha, s=80, zorder=5)
    sum_all  = sum(t.pnl_pts for t in trades_all)
    sum_kept = sum(t.pnl_pts for t in trades_filtered)
    bias_txt = {+1: "BULLISH (longs only)", -1: "BEARISH (shorts only)",
                 0: "NEUTRAL"}[bias]
    ax.set_title(
        f"Fundamentals filter ({bias_txt}): "
        f"all={sum_all:+.2f}pt → kept={sum_kept:+.2f}pt", fontsize=11
    )
    ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


# ----------------------------------------------------------------------------
# 6. Concept 6 — Using Failed Signals
# ----------------------------------------------------------------------------
def detect_failed_breakouts(df: pd.DataFrame, lookback: int = 30,
                            fail_window: int = 20) -> List[dict]:
    """
    A 'failed signal' = an upside breakout that closes back BELOW the prior
    range high within `fail_window` days (or a downside breakout that closes
    back ABOVE the prior range low within `fail_window` days). Each such
    failure becomes a CONTRARIAN trade signal in the opposite direction.

    Schwager: "If a market fails to follow through in the direction of a key
    chart signal, this is a crucial item of information often overlooked by
    novice chartists." (Ch. 11; introduced in Ch. 7 §5.)
    """
    failures: List[dict] = []
    i = lookback
    while i < len(df):
        window = df.iloc[i - lookback:i]
        hi, lo = window["high"].max(), window["low"].min()
        c = df["close"].iat[i]
        if c > hi:                                       # upside breakout
            for j in range(i + 1, min(i + 1 + fail_window, len(df))):
                if df["close"].iat[j] < hi:              # closed back inside
                    failures.append(dict(
                        signal_date=df.index[i], signal_dir=+1,
                        fail_date=df.index[j], contrarian_dir=-1,
                        signal_px=c, fail_px=df["close"].iat[j],
                    ))
                    i = j                # skip past the failure
                    break
            else:
                pass
        elif c < lo:                                     # downside breakout
            for j in range(i + 1, min(i + 1 + fail_window, len(df))):
                if df["close"].iat[j] > lo:
                    failures.append(dict(
                        signal_date=df.index[i], signal_dir=-1,
                        fail_date=df.index[j], contrarian_dir=+1,
                        signal_px=c, fail_px=df["close"].iat[j],
                    ))
                    i = j
                    break
        i += 1
    return failures

def illustrate_failed_signals(df: pd.DataFrame, failures: List[dict],
                              out: str) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df.index, df["close"], color="#1f4e79", lw=1.0)
    for f in failures:
        ax.axvspan(f["signal_date"], f["fail_date"],
                   color="#fff2cc", alpha=0.6)
        ax.scatter(f["signal_date"], f["signal_px"],
                   marker="^" if f["signal_dir"] == 1 else "v",
                   color="#a23b3b", s=80, zorder=5)
        ax.scatter(f["fail_date"], f["fail_px"],
                   marker="*", color="#1a6e1a", s=160, zorder=6)
        ax.annotate(
            "Failed → reverse",
            xy=(f["fail_date"], f["fail_px"]),
            xytext=(0, 25), textcoords="offset points", ha="center",
            fontsize=8, color="#1a6e1a",
            arrowprops=dict(arrowstyle="->", color="#1a6e1a")
        )
    ax.set_title("Failed Signals: a failure of the breakout itself becomes "
                 "the trade", fontsize=11)
    ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


# ----------------------------------------------------------------------------
# 7. Concept 7 — Chart Analysis as Art (vs. Mechanical Science)
# ----------------------------------------------------------------------------
def illustrate_art_vs_science(out: str) -> None:
    """A conceptual side-by-side: same chart, two interpretations."""
    rng = np.random.default_rng(2)
    n = 120
    x = np.arange(n)
    y = 100 + np.cumsum(rng.normal(0.05, 1.0, n))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax in axes:
        ax.plot(x, y, color="#1f4e79", lw=1.2)
        ax.grid(alpha=0.25)

    # Mechanical view (fixed rules)
    ma = pd.Series(y).rolling(20).mean()
    axes[0].plot(x, ma, color="#a23b3b", lw=1.0, label="MA(20)")
    crosses = np.where(np.diff(np.sign(y - ma.values)))[0]
    for c in crosses:
        axes[0].axvline(c, color="#a23b3b", alpha=0.4, ls=":")
    axes[0].set_title("Mechanical (science): every MA-cross taken",
                      fontsize=10)
    axes[0].legend(loc="upper left")

    # Discretionary view (art)
    axes[1].plot([20, 60], [y[20], y[60]], color="#1a6e1a", lw=1.2,
                 label="Trend line (drawn by eye)")
    axes[1].annotate("Flag forming?", xy=(85, y[85]), xytext=(70, y[85] + 4),
                     arrowprops=dict(arrowstyle="->", color="#1a6e1a"),
                     fontsize=9, color="#1a6e1a")
    axes[1].set_title("Discretionary (art): context, experience, judgment",
                      fontsize=10)
    axes[1].legend(loc="upper left")

    fig.suptitle("Same chart, two readings: textbook rules vs. "
                 "experienced eye", fontsize=12)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


# ----------------------------------------------------------------------------
# Main: build all illustrations
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    out_dir = os.path.join(os.path.dirname(__file__), "..", "charts")
    os.makedirs(out_dir, exist_ok=True)

    df = make_eurodollar_series()

    illustrate_skepticism(
        df, os.path.join(out_dir, "01_skepticism.png"))

    trades = simulate_breakout_strategy(df, lookback=30)
    illustrate_risk_control(
        df, trades, os.path.join(out_dir, "02_risk_control.png"))

    trades_conf = simulate_with_confirmation(df, lookback=30, wait_days=3)
    illustrate_confirmation(
        df, trades, trades_conf,
        os.path.join(out_dir, "03_confirmation.png"))

    illustrate_multi_timeframe(
        df, os.path.join(out_dir, "04_context.png"))

    bias = +1                                          # bullish fundamental
    kept = filter_by_fundamental(trades, bias)
    illustrate_fundamentals(
        df, trades, kept, bias,
        os.path.join(out_dir, "05_fundamentals.png"))

    failures = detect_failed_breakouts(df, lookback=30, fail_window=5)
    illustrate_failed_signals(
        df, failures, os.path.join(out_dir, "06_failed_signals.png"))

    illustrate_art_vs_science(
        os.path.join(out_dir, "07_art_vs_science.png"))

    # ---------------- numeric summary printed for the notes ----------------
    print(f"Trades (no confirmation):  {len(trades)} "
          f"net={sum(t.pnl_pts for t in trades):+.2f}pt "
          f"(${sum(t.pnl_pts for t in trades)*2500:+,.0f})")
    for k, t in enumerate(trades, 1):
        print(f"  #{k:>2}  {t.entry_date.date()} → {t.exit_date.date()}  "
              f"dir={'L' if t.direction==1 else 'S'}  "
              f"pnl={t.pnl_pts:+.2f}pt")
    print()
    print(f"Trades (with confirmation): {len(trades_conf)} "
          f"net={sum(t.pnl_pts for t in trades_conf):+.2f}pt "
          f"(${sum(t.pnl_pts for t in trades_conf)*2500:+,.0f})")
    for k, t in enumerate(trades_conf, 1):
        print(f"  #{k:>2}  {t.entry_date.date()} → {t.exit_date.date()}  "
              f"dir={'L' if t.direction==1 else 'S'}  "
              f"pnl={t.pnl_pts:+.2f}pt")
    print()
    print(f"Failed-signal events: {len(failures)}")
    for f in failures:
        print(f"  signal {f['signal_date'].date()} "
              f"({'up' if f['signal_dir']==1 else 'dn'}) "
              f"failed by {f['fail_date'].date()}")
