"""
Chapter 9 — Concept 6: Wide-Ranging Day Stop
A bar whose true range is much larger than recent average. Stop is set
at the bar's true low (long) or true high (short) — using prior close to
account for gaps.
"""
from dataclasses import dataclass


@dataclass
class Bar:
    high: float
    low: float
    close: float


def true_range(today: Bar, prev_close: float) -> float:
    return max(today.high, prev_close) - min(today.low, prev_close)


def true_low(today: Bar, prev_close: float) -> float:
    return min(today.low, prev_close)


def is_wide_ranging(today: Bar, prev_close: float,
                    avg_range: float, multiple: float = 2.0) -> bool:
    return true_range(today, prev_close) >= multiple * avg_range


def long_stop_after_wrd(wrd: Bar, prev_close: float) -> float:
    return true_low(wrd, prev_close)


if __name__ == "__main__":
    avg_tr = 1.50
    prev_close = 49.20
    today = Bar(high=52.0, low=48.0, close=51.6)

    if is_wide_ranging(today, prev_close, avg_tr):
        stop = long_stop_after_wrd(today, prev_close)
        print(f"Wide-ranging day detected. Long stop: ${stop:.2f}")
    else:
        print("Not wide-ranging; use a different stop technique.")
