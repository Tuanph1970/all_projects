"""
Chapter 9 — Concept 9: Trailing Stop
Pivot-based trailing stop. Stop only ever moves toward LESS risk.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class TrailingStop:
    initial_stop: float
    n: int = 10
    current_stop: float = field(init=False)
    pivot_low_history: List[float] = field(default_factory=list)
    high_water_mark: float = field(default=float('-inf'))

    def __post_init__(self):
        self.current_stop = self.initial_stop

    def _is_relative_low(self, lows: List[float], i: int) -> bool:
        if i < self.n or i + self.n >= len(lows):
            return False
        window = lows[i - self.n: i + self.n + 1]
        return lows[i] == min(window) and window.count(lows[i]) == 1

    def update(self, lows: List[float], highs: List[float]) -> None:
        if highs:
            self.high_water_mark = max(self.high_water_mark, max(highs))
        for i in range(self.n, len(lows) - self.n):
            if self._is_relative_low(lows, i):
                pivot = lows[i]
                if pivot > self.current_stop and self.high_water_mark > pivot:
                    self.current_stop = pivot
                    if pivot not in self.pivot_low_history:
                        self.pivot_low_history.append(pivot)

    def stopped_out(self, current_close: float) -> bool:
        return current_close < self.current_stop


if __name__ == "__main__":
    lows = [46, 47, 48, 49, 50, 46, 48, 49, 50, 51, 52, 53, 54, 52,
            53, 54, 55, 56, 57, 58, 59, 58, 57, 56, 58, 60, 62, 64,
            66, 65, 64, 66, 68, 70, 68, 67, 66, 65, 64, 63]
    highs = [v + 2 for v in lows]
    ts = TrailingStop(initial_stop=46.0, n=5)
    ts.update(lows, highs)
    print("Pivot history:", ts.pivot_low_history)
    print(f"Current stop: ${ts.current_stop:.2f}")
    print("Stopped out today?", ts.stopped_out(current_close=lows[-1]))
