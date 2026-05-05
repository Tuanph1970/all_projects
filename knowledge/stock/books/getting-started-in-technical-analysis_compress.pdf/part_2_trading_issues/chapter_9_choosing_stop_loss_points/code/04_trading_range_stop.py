"""
Chapter 9 — Concept 4: Trading Range Stop
After a breakout from a range, place the stop near the midpoint or
opposite end (NOT the near edge — that gets hit by routine pullbacks).
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass
class TradingRangeStop:
    range_low: float
    range_high: float
    entry_price: float
    account_equity: float
    max_risk_pct: float = 0.02

    @property
    def midpoint(self) -> float:
        return (self.range_low + self.range_high) / 2

    def candidate_stops(self, side: str = "long") -> dict:
        if side == "long":
            return {"near_edge": self.range_high,
                    "midpoint":  self.midpoint,
                    "far_edge":  self.range_low}
        return {"near_edge": self.range_low,
                "midpoint":  self.midpoint,
                "far_edge":  self.range_high}

    def pick_stop(self, side: str = "long") -> Tuple[str, float, int]:
        max_dollar_risk = self.account_equity * self.max_risk_pct
        chosen = None
        for label, stop in self.candidate_stops(side).items():
            if label == "near_edge":          # skip per Schwager
                continue
            risk = abs(self.entry_price - stop)
            if risk == 0:
                continue
            shares = int(max_dollar_risk // risk)
            chosen = (label, stop, shares)
            if label == "midpoint":           # midpoint is recommended default
                break
        return chosen


if __name__ == "__main__":
    trs = TradingRangeStop(range_low=42.0, range_high=48.0,
                           entry_price=49.5, account_equity=100_000)
    label, stop, qty = trs.pick_stop()
    print(f"Chosen stop: {label} @ ${stop:.2f}  →  size {qty} shares")
