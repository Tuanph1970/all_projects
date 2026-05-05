"""
chapter11_demo.py
=================
End-to-end demonstration of the Chapter 11 detectors on a synthetic
price series engineered to contain ALL of the failed-signal events
described in the chapter.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from chapter11_detectors import (
    detect_bull_bear_traps,
    detect_filled_gaps,
    detect_spikes,
    detect_spike_failures,
    detect_wide_ranging_days,
    detect_wrd_failures,
)

np.random.seed(42)

# ---------------------------------------------------------------------------
# Build a synthetic OHLC dataframe with a bull trap, a downside spike,
# a filled gap, and a wide-ranging-day failure
# ---------------------------------------------------------------------------
def make_test_data():
    closes = np.r_[
        # 0–25  : range $48–52
        np.linspace(50, 51, 25) + np.random.randn(25) * 0.4,
        # 26–30 : false breakout up to 55 (bull trap)
        np.linspace(52, 55, 5) + np.random.randn(5) * 0.3,
        # 31–35 : snap back to 47 (bull trap confirmed)
        np.linspace(54, 47, 5) + np.random.randn(5) * 0.4,
        # 36–60 : downtrend to 38, with a spike high mid-trend
        np.linspace(47, 38, 25) + np.random.randn(25) * 0.4,
        # 61–80 : recovery to 50, includes a downside gap that gets filled
        np.linspace(38, 50, 20) + np.random.randn(20) * 0.4,
        # 81–100: rally to 60
        np.linspace(50, 60, 20) + np.random.randn(20) * 0.4,
    ]
    n = len(closes)
    opens = np.r_[closes[0], closes[:-1]]
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(n)) * 0.5
    lows  = np.minimum(opens, closes) - np.abs(np.random.randn(n)) * 0.5

    # Inject a downside spike at index 50 (close at top of range)
    highs[50] = lows[50] = closes[50] - 5
    lows[50]  = closes[50] - 6
    highs[50] = closes[50] - 1
    closes[50] = highs[50] - 0.1

    # Inject a downside gap at index 70
    highs[70] = lows[69] - 1.5
    lows[70]  = highs[70] - 0.8
    closes[70] = lows[70] + 0.2

    df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes},
                      index=pd.bdate_range("2024-01-02", periods=n))
    return df


def main():
    df = make_test_data()
    print(f"Built {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}\n")

    # --- 1. Bull / bear traps (concept 2)
    traps = detect_bull_bear_traps(df, lookback=15, time_confirm_days=15)
    print(f"--- Bull / bear traps: {len(traps)} ---")
    if not traps.empty:
        print(traps.to_string(index=False))

    # --- 2. Filled gaps (concept 5)
    gaps = detect_filled_gaps(df)
    print(f"\n--- Filled gaps: {len(gaps)} ---")
    if not gaps.empty:
        print(gaps.head().to_string(index=False))

    # --- 3. Spikes + failures (concept 6)
    spikes = detect_spikes(df, k=1.0)
    print(f"\n--- Spikes detected: {len(spikes)} ---")
    if not spikes.empty:
        print(spikes.to_string(index=False))
        fails = detect_spike_failures(df, spikes, min_age_days=5)
        print(f"   Spike failures: {len(fails)}")
        if not fails.empty:
            print(fails.to_string(index=False))

    # --- 4. Wide-ranging days + failures (concept 7)
    wrds = detect_wide_ranging_days(df, n=10, k=1.6)
    print(f"\n--- Wide-ranging days: {len(wrds)} ---")
    if not wrds.empty:
        print(wrds.head().to_string(index=False))
        wf = detect_wrd_failures(df, wrds)
        print(f"   WRD failures: {len(wf)}")
        if not wf.empty:
            print(wf.head().to_string(index=False))

    # --- Visual summary
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df.index, df["close"], lw=1, color="#333")
    if not traps.empty:
        for _, r in traps.iterrows():
            color = "red" if r["type"] == "bull_trap" else "green"
            ax.axvline(r["date"], color=color, alpha=0.35, ls="--",
                       label=r["type"])
    if not gaps.empty:
        for _, g in gaps.iterrows():
            ax.axvspan(g["gap_date"], g["fill_date"], color="orange", alpha=0.15)
    handles, labels = ax.get_legend_handles_labels()
    seen = {}
    for h, l in zip(handles, labels):
        seen.setdefault(l, h)
    ax.legend(seen.values(), seen.keys())
    ax.set_title("Detected failed-signal events on synthetic data",
                 fontweight="bold")
    ax.grid(alpha=0.25)
    out = "/home/claude/chapter11/images/13_demo_detection.png"
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print(f"\n--- Wrote demo overview to {out} ---")


if __name__ == "__main__":
    main()
