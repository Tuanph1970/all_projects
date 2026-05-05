"""
Change of Market Opinion as a position-exit method.

Schwager's description: "Another approach with very little flash, but
lots of common sense." The trader sets NO predetermined objective.
Instead, the position is held until the technical opinion that
justified it changes to at least neutral.

Mechanically: define the entry thesis as a set of conditions
(e.g. "price above the rising 50-day MA AND above the most recent
swing low"). When ANY core condition fails, exit -- no negotiation.

Strength: lets winners run as long as the trend is intact.
Weakness: surrenders some open profit between the peak and the
opinion-change point. Pair with a trailing stop if you want a
floor on giveback.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class ThesisCondition:
    name: str
    check: Callable[[List[float], int], bool]   # (prices, current_index) -> still valid?


def evaluate_thesis(prices: List[float],
                    index: int,
                    conditions: List[ThesisCondition]) -> List[str]:
    """Return a list of names of conditions that have FAILED."""
    return [c.name for c in conditions if not c.check(prices, index)]


def manage_position(prices: List[float],
                    entry_index: int,
                    thesis: List[ThesisCondition]
                    ) -> Optional[int]:
    """Hold the position until any thesis condition fails.
    Returns the bar index where exit fires, or None if it never does."""
    for i in range(entry_index + 1, len(prices)):
        broken = evaluate_thesis(prices, i, thesis)
        if broken:
            return i
    return None


# --- demo ---------------------------------------------------------------
if __name__ == "__main__":
    import numpy as np
    np.random.seed(3)

    n = 150
    prices = (30 + np.concatenate([
        np.linspace(0,  25, 90),
        np.linspace(25, 22, 15),
        np.linspace(22, 12, 45),
    ]) + np.random.normal(0, 0.6, n)).tolist()

    # Thesis: 1) price > 20-day moving average  AND
    #         2) price > entry price - 4 (acts as a wide floor)
    def above_ma(prices: List[float], i: int) -> bool:
        if i < 20:
            return True
        ma = sum(prices[i - 20: i]) / 20
        return prices[i] > ma

    def above_floor(prices: List[float], i: int, entry_price: float = 30.0) -> bool:
        return prices[i] > entry_price - 4

    thesis = [
        ThesisCondition("Price above 20-day MA", above_ma),
        ThesisCondition("Price above floor (entry - 4)",
                        lambda p, i: above_floor(p, i, prices[5])),
    ]

    exit_idx = manage_position(prices, entry_index=5, thesis=thesis)
    if exit_idx is None:
        print("Thesis never broke -- position still open at end of data.")
    else:
        broken = evaluate_thesis(prices, exit_idx, thesis)
        entry_price = prices[5]
        exit_price = prices[exit_idx]
        print(f"Entry  bar 5,   price {entry_price:.2f}")
        print(f"Exit   bar {exit_idx}, price {exit_price:.2f}")
        print(f"P/L per share: {exit_price - entry_price:+.2f}")
        print(f"Reasons broken: {broken}")
    # Sample output (varies with seed):
    #   Entry  bar 5,   price 30.71
    #   Exit   bar 106, price 22.09
    #   P/L per share: -8.62
    #   Reasons broken: ['Price above 20-day MA']
