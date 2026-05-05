"""
Chapter 9 — Concept 8: Money Stop
Use only when every meaningful technical level is too far away to fit
within the trader's max-risk-per-trade budget.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class StopDecision:
    entry_price: float
    technical_stop: Optional[float]
    account_equity: float
    max_risk_pct: float = 0.02
    money_stop_pct: float = 0.03

    @property
    def max_dollar_risk(self) -> float:
        return self.account_equity * self.max_risk_pct

    def technical_risk(self) -> Optional[float]:
        if self.technical_stop is None:
            return None
        return self.entry_price - self.technical_stop

    def decide(self) -> dict:
        tr = self.technical_risk()
        if tr is not None and tr <= self.max_dollar_risk / 100:
            return {"type": "technical", "stop": self.technical_stop}
        money_stop = self.entry_price * (1 - self.money_stop_pct)
        return {"type": "money", "stop": money_stop}


if __name__ == "__main__":
    sd = StopDecision(entry_price=80.0, technical_stop=65.0,
                      account_equity=50_000)
    decision = sd.decide()
    print(f"Use {decision['type']} stop at ${decision['stop']:.2f}")
