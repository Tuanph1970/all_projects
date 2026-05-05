"""
Chapter 9 — Concept 10: CIC ("Cancel If Close") Anti-Pattern
Compares disciplined GTC stop vs. CIC behavior to show how much worse
the loss becomes when the stop is canceled at the worst possible moment.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StopBehavior:
    initial_stop: float
    discipline: str          # "gtc" or "cic"
    canceled: bool = False
    triggered_at: Optional[float] = None

    def react_to(self, price: float, threshold_for_cic: float = 0.30) -> None:
        # CIC: trader panics when price gets near the stop and CANCELS it.
        if self.discipline == "cic" and not self.canceled and self.triggered_at is None:
            if price - self.initial_stop <= threshold_for_cic and price > self.initial_stop:
                self.canceled = True   # the fatal moment
                return
        # GTC: order is honored unconditionally.
        if not self.canceled and price <= self.initial_stop and self.triggered_at is None:
            self.triggered_at = price


def simulate(prices: List[float], discipline: str) -> StopBehavior:
    s = StopBehavior(initial_stop=48.0, discipline=discipline)
    for p in prices:
        s.react_to(p)
    return s


if __name__ == "__main__":
    prices = [50.0, 49.5, 49.0, 48.5, 48.20, 47.8, 46.0, 44.0, 42.0, 38.0]
    entry = 50.0
    final = prices[-1]

    gtc = simulate(prices, discipline="gtc")
    cic = simulate(prices, discipline="cic")

    gtc_loss = (gtc.triggered_at - entry) if gtc.triggered_at else (final - entry)
    cic_loss = (final - entry) if cic.canceled else (cic.triggered_at - entry)

    print(f"GTC outcome : ${gtc_loss:+.2f}/share  (triggered @ {gtc.triggered_at})")
    print(f"CIC outcome : ${cic_loss:+.2f}/share  (canceled? {cic.canceled})")
    print(f"CIC loss is : {cic_loss / gtc_loss:.1f}x the GTC loss")
