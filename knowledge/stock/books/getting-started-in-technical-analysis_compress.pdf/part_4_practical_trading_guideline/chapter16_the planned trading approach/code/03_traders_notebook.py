"""
Chapter 16 — Trader's Notebook (Step Five)
============================================
The notebook is a structured ledger of every trade taken. This module
implements it as a pandas-backed class with the columns Schwager describes.
"""

import pandas as pd
from datetime import date
from pathlib import Path


COLUMNS = [
    "trade_id",
    "entry_date",
    "symbol",
    "direction",          # 'long' or 'short'
    "entry_price",
    "shares",
    "initial_stop",
    "current_stop",
    "implied_risk_pct",   # vs equity at entry
    "implied_risk_dollar",
    "objective_price",
    "objective_pct",
    "exit_date",
    "exit_price",
    "net_pl",             # after commission
    "reason_entry",
    "hindsight_note",
]


class TraderNotebook:
    """A simple persistent trader's notebook."""

    def __init__(self, path: str | Path = "trader_notebook.csv"):
        self.path = Path(path)
        if self.path.exists():
            self.df = pd.read_csv(self.path)
        else:
            self.df = pd.DataFrame(columns=COLUMNS)

    def open_trade(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        shares: int,
        initial_stop: float,
        equity_at_entry: float,
        objective_price: float | None = None,
        reason_entry: str = "",
    ) -> int:
        """Record a newly opened trade and return its ID."""
        risk_per_unit = abs(entry_price - initial_stop)
        risk_dollar = shares * risk_per_unit
        risk_pct = risk_dollar / equity_at_entry * 100

        objective_pct = (
            (objective_price - entry_price) / entry_price * 100
            if objective_price else None
        )

        next_id = int(self.df["trade_id"].max() + 1) if len(self.df) else 1

        new_row = {
            "trade_id": next_id,
            "entry_date": date.today().isoformat(),
            "symbol": symbol.upper(),
            "direction": direction,
            "entry_price": entry_price,
            "shares": shares,
            "initial_stop": initial_stop,
            "current_stop": initial_stop,
            "implied_risk_pct": round(risk_pct, 3),
            "implied_risk_dollar": round(risk_dollar, 2),
            "objective_price": objective_price,
            "objective_pct": round(objective_pct, 2) if objective_pct else None,
            "exit_date": None,
            "exit_price": None,
            "net_pl": None,
            "reason_entry": reason_entry,
            "hindsight_note": None,
        }
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        return next_id

    def update_stop(self, trade_id: int, new_stop: float):
        """Tighten a stop. Refuses to widen (Schwager's rule: only reduce risk)."""
        idx = self.df[self.df["trade_id"] == trade_id].index[0]
        row = self.df.loc[idx]
        if row["direction"] == "long" and new_stop < row["current_stop"]:
            raise ValueError("Long: refusing to LOWER the stop (would increase risk).")
        if row["direction"] == "short" and new_stop > row["current_stop"]:
            raise ValueError("Short: refusing to RAISE the stop (would increase risk).")
        self.df.loc[idx, "current_stop"] = new_stop
        # Recompute implied risk
        risk_per_unit = abs(row["entry_price"] - new_stop)
        new_risk = row["shares"] * risk_per_unit
        self.df.loc[idx, "implied_risk_dollar"] = round(new_risk, 2)

    def close_trade(self, trade_id: int, exit_price: float, commission: float = 0.0, hindsight_note: str = ""):
        """Record exit and compute net P&L."""
        idx = self.df[self.df["trade_id"] == trade_id].index[0]
        row = self.df.loc[idx]

        gross = (exit_price - row["entry_price"]) * row["shares"]
        if row["direction"] == "short":
            gross = -gross

        self.df.loc[idx, "exit_date"] = date.today().isoformat()
        self.df.loc[idx, "exit_price"] = exit_price
        self.df.loc[idx, "net_pl"] = round(gross - commission, 2)
        self.df.loc[idx, "hindsight_note"] = hindsight_note

    def open_positions(self) -> pd.DataFrame:
        return self.df[self.df["exit_date"].isna()].copy()

    def total_open_risk(self) -> float:
        return self.open_positions()["implied_risk_dollar"].sum()

    def save(self):
        self.df.to_csv(self.path, index=False)


# -------- Demo --------
if __name__ == "__main__":
    nb = TraderNotebook("/tmp/demo_notebook.csv")
    equity = 100_000

    tid1 = nb.open_trade(
        symbol="AAPL", direction="long",
        entry_price=175, shares=200,
        initial_stop=168, equity_at_entry=equity,
        objective_price=190,
        reason_entry="cup-and-handle breakout, rising volume",
    )

    tid2 = nb.open_trade(
        symbol="JPM", direction="short",
        entry_price=155, shares=400,
        initial_stop=160, equity_at_entry=equity,
        objective_price=145,
        reason_entry="head-and-shoulders top, neckline broken",
    )

    print("Open positions:")
    print(nb.open_positions()[["symbol", "direction", "entry_price", "current_stop", "implied_risk_dollar"]])
    print(f"\nTotal open risk: ${nb.total_open_risk():,.0f}  ({nb.total_open_risk()/equity*100:.1f}% of equity)")

    # Trail the AAPL stop up
    nb.update_stop(tid1, new_stop=178)
    print("\nAfter trailing AAPL stop to 178:")
    print(nb.open_positions()[["symbol", "current_stop", "implied_risk_dollar"]])

    # Close both
    nb.close_trade(tid1, exit_price=188.50, commission=20, hindsight_note="rode it well; stop trailing worked")
    nb.close_trade(tid2, exit_price=147.00, commission=20, hindsight_note="cover at first signs of buyers stepping in")

    print("\nFinal notebook:")
    print(nb.df[["trade_id", "symbol", "direction", "net_pl", "hindsight_note"]])
