"""
Chapter 16 — Personal Trading Analysis (Step Seven)
====================================================
Two tools described in the book:
  1. Segmented trade analysis — slice trades by category to find what works
  2. Equity chart — close-only chart of account equity, used as an early-warning
     system for sudden performance breakdowns.

This module reads from the CSV produced by the trader's notebook module.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def segment_by_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Group all closed trades by a column (e.g., 'symbol', 'direction')
    and return summary statistics.
    """
    closed = df[df["net_pl"].notna()].copy()
    if not len(closed):
        return pd.DataFrame()

    grouped = closed.groupby(column).agg(
        n_trades=("net_pl", "count"),
        total_pl=("net_pl", "sum"),
        avg_pl=("net_pl", "mean"),
        win_rate=("net_pl", lambda s: (s > 0).mean()),
        best=("net_pl", "max"),
        worst=("net_pl", "min"),
    ).round(2)
    grouped["win_rate"] = (grouped["win_rate"] * 100).round(1)
    return grouped.sort_values("total_pl", ascending=False)


def expectancy(df: pd.DataFrame) -> dict:
    """
    Average dollar gain per trade.
        E = (win_rate * avg_win) - (loss_rate * avg_loss)
    """
    closed = df[df["net_pl"].notna()]
    if not len(closed):
        return {}

    wins = closed[closed["net_pl"] > 0]["net_pl"]
    losses = closed[closed["net_pl"] <= 0]["net_pl"]

    win_rate = len(wins) / len(closed) if len(closed) else 0
    avg_win = wins.mean() if len(wins) else 0
    avg_loss = losses.mean() if len(losses) else 0  # negative

    e = win_rate * avg_win + (1 - win_rate) * avg_loss

    return {
        "n_trades": len(closed),
        "win_rate_%": round(win_rate * 100, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy_per_trade": round(e, 2),
        "profit_factor": round(wins.sum() / abs(losses.sum()), 2) if losses.sum() else float("inf"),
    }


def equity_curve(df: pd.DataFrame, starting_equity: float) -> pd.Series:
    """
    Build a cumulative equity series indexed by exit date.
    """
    closed = df[df["net_pl"].notna()].copy()
    closed["exit_date"] = pd.to_datetime(closed["exit_date"])
    closed = closed.sort_values("exit_date")
    closed["equity"] = starting_equity + closed["net_pl"].cumsum()
    return closed.set_index("exit_date")["equity"]


def drawdown_series(equity: pd.Series) -> pd.DataFrame:
    """
    Compute running peak, drawdown $, and drawdown %.
    """
    peak = equity.cummax()
    dd_dollar = equity - peak
    dd_pct = dd_dollar / peak * 100
    return pd.DataFrame({"equity": equity, "peak": peak, "dd_$": dd_dollar, "dd_%": dd_pct})


def plot_equity_chart(equity: pd.Series, save_path: str | None = None):
    """Plot the equity curve with peak and drawdown shaded."""
    dd = drawdown_series(equity)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})

    ax1.plot(equity.index, equity.values, color="#1e40af", linewidth=2, label="Equity")
    ax1.plot(dd.index, dd["peak"].values, color="#16a34a", linestyle="--",
             linewidth=1, label="Running peak")
    ax1.fill_between(dd.index, dd["peak"].values, equity.values,
                     where=equity < dd["peak"], color="#fee2e2", alpha=0.6,
                     label="Drawdown")
    ax1.set_ylabel("Equity ($)")
    ax1.set_title("Equity Chart — early warning system")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)

    ax2.fill_between(dd.index, dd["dd_%"].values, 0, color="#dc2626", alpha=0.6)
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Date")
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=120, bbox_inches="tight")
        print(f"Saved equity chart to {save_path}")
    else:
        plt.show()
    plt.close()


# -------- Demo --------
if __name__ == "__main__":
    # Build a synthetic trade history
    import numpy as np
    rng = np.random.default_rng(7)
    n = 80

    trades = pd.DataFrame({
        "trade_id": range(1, n + 1),
        "symbol": rng.choice(["AAPL", "MSFT", "TSLA", "JPM", "XOM", "KO"], n),
        "direction": rng.choice(["long", "short"], n, p=[0.7, 0.3]),
        "exit_date": pd.date_range("2024-01-02", periods=n, freq="3D"),
        "net_pl": rng.normal(loc=200, scale=1500, size=n).round(2),
    })

    # Simulate the "day-trades-bleed-money" pattern from the book
    trades.loc[trades["symbol"] == "TSLA", "net_pl"] -= 800

    print("=" * 60)
    print("Overall expectancy")
    print("=" * 60)
    for k, v in expectancy(trades).items():
        print(f"  {k:<22} {v}")

    print()
    print("=" * 60)
    print("Segmented by symbol")
    print("=" * 60)
    print(segment_by_column(trades, "symbol"))

    print()
    print("=" * 60)
    print("Segmented by direction (long vs short bias check)")
    print("=" * 60)
    print(segment_by_column(trades, "direction"))

    eq = equity_curve(trades, starting_equity=100_000)
    plot_equity_chart(eq, save_path="/home/claude/chapter16/images/equity_chart_demo.png")
