"""
Chapter 9 — Concept 2: GTC (Good-Till-Canceled) Stop Order
Simulate a resting GTC stop across a multi-day price series, including
overnight gaps that a day-only stop would miss entirely.
"""
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class GTCStopOrder:
    side: str            # "sell" or "buy"
    stop_price: float
    quantity: int
    active: bool = True
    fill_price: Optional[float] = None
    fill_day: Optional[int] = None

    def check(self, day: int, day_low: float, day_high: float) -> bool:
        if not self.active:
            return False
        if self.side == "sell" and day_low <= self.stop_price:
            self.fill_price = min(self.stop_price, day_high)
            self.fill_day, self.active = day, False
            return True
        if self.side == "buy" and day_high >= self.stop_price:
            self.fill_price = max(self.stop_price, day_low)
            self.fill_day, self.active = day, False
            return True
        return False


def simulate(prices: List[Tuple[float, float]], stop: GTCStopOrder) -> None:
    for day, (lo, hi) in enumerate(prices, start=1):
        if stop.check(day, lo, hi):
            print(f"Day {day}: STOP TRIGGERED at ${stop.fill_price:.2f}")
            return
    print("Stop never triggered, GTC order still resting.")


if __name__ == "__main__":
    series = [(49.5, 50.6), (49.8, 50.9), (49.0, 50.4), (48.9, 50.1),
              (49.1, 50.3), (48.8, 49.7), (48.5, 49.4), (48.3, 49.0),
              (48.4, 49.2), (48.6, 49.5), (48.2, 49.0), (48.0, 48.9),
              (48.1, 48.8), (47.20, 47.90)]    # gap-down on day 14
    sell_stop = GTCStopOrder(side="sell", stop_price=48.00, quantity=200)
    simulate(series, sell_stop)
