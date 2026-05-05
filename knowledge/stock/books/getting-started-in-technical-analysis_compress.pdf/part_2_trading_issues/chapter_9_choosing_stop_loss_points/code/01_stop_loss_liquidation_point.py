"""
Chapter 9 — Concept 1: Stop-Loss Liquidation Point
A predetermined exit price set BEFORE trade entry, sized using the
trader's max-risk-per-trade rule.
"""
from dataclasses import dataclass


@dataclass
class StopLossPlan:
    entry_price: float
    stop_price: float
    account_equity: float
    max_risk_pct: float = 0.02   # 2% rule

    def risk_per_share(self) -> float:
        return self.entry_price - self.stop_price

    def max_position_size(self) -> int:
        risk_dollars = self.account_equity * self.max_risk_pct
        rps = self.risk_per_share()
        if rps <= 0:
            raise ValueError("Stop must be below entry for a long position.")
        return int(risk_dollars // rps)

    def should_liquidate(self, current_price: float) -> bool:
        return current_price <= self.stop_price


if __name__ == "__main__":
    plan = StopLossPlan(entry_price=50.0, stop_price=48.0, account_equity=100_000)
    print(f"Risk per share : ${plan.risk_per_share():.2f}")
    print(f"Max shares     : {plan.max_position_size()}")
    print(f"Hit @ $47.95?  : {plan.should_liquidate(47.95)}")
