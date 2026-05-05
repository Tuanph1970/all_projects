"""
Chapter 9 — Concept 3: Trend Line Stop
Place the protective stop just beyond a fitted trend line.
Earliest warning of trend reversal, but most prone to false signals.
"""
import numpy as np
from dataclasses import dataclass


@dataclass
class TrendLineStop:
    pivot_dates: list   # day indices of lows
    pivot_prices: list  # corresponding low prices
    buffer: float = 0.005   # 0.5% buffer below line

    def slope_intercept(self):
        x = np.array(self.pivot_dates, dtype=float)
        y = np.array(self.pivot_prices, dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        return slope, intercept

    def line_value(self, day: int) -> float:
        m, b = self.slope_intercept()
        return m * day + b

    def stop_for(self, day: int) -> float:
        return self.line_value(day) * (1 - self.buffer)


if __name__ == "__main__":
    tl = TrendLineStop(pivot_dates=[10, 70, 130], pivot_prices=[40.0, 44.0, 48.0])
    today = 190
    print(f"Trend line at day {today}: ${tl.line_value(today):.2f}")
    print(f"Suggested stop:           ${tl.stop_for(today):.2f}")
