"""
Contrary Opinion as a position-exit input.

Theory: when the large majority of speculators are bullish, those who
wanted to be long already are. The pool of incremental buyers is small,
so the market is vulnerable to a downside reaction. The reverse holds
for extreme bearish sentiment.

Sources of sentiment data: bulls/bears surveys, advisor newsletter
counts, put/call ratios, etc.

The Achilles' heel: sentiment can stay extreme for a long time while
the trend continues. So Schwager recommends contrary opinion as a
SUPPLEMENTARY input, never the sole exit trigger -- usually paired
with a sensitive technical confirmation (e.g. a thrust day in the
opposite direction).
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class SentimentReading:
    day: int
    pct_bulls: float       # 0 to 100
    price: float


def find_extremes(readings: List[SentimentReading],
                  bull_threshold: float = 80.0,
                  bear_threshold: float = 20.0
                  ) -> Tuple[List[SentimentReading], List[SentimentReading]]:
    bull_extremes = [r for r in readings if r.pct_bulls >= bull_threshold]
    bear_extremes = [r for r in readings if r.pct_bulls <= bear_threshold]
    return bull_extremes, bear_extremes


def contrary_exit_signal(readings: List[SentimentReading],
                         position: str,
                         confirm_with_price_reversal: bool = True,
                         reversal_lookback: int = 3,
                         bull_threshold: float = 80.0,
                         bear_threshold: float = 20.0) -> Optional[int]:
    """Return the day-index where a contrary-opinion exit fires for the
    current `position` ('long' or 'short'), or None.

    With `confirm_with_price_reversal=True`, the signal also requires
    that the most recent `reversal_lookback` bars show a price reversal
    in the appropriate direction -- a basic safety net against staying
    short too long while sentiment grinds higher.
    """
    if len(readings) < reversal_lookback + 1:
        return None

    for i in range(reversal_lookback, len(readings)):
        r = readings[i]
        if position == "long" and r.pct_bulls >= bull_threshold:
            if not confirm_with_price_reversal or \
               r.price < readings[i - reversal_lookback].price:
                return r.day
        elif position == "short" and r.pct_bulls <= bear_threshold:
            if not confirm_with_price_reversal or \
               r.price > readings[i - reversal_lookback].price:
                return r.day
    return None


# --- demo ---------------------------------------------------------------
if __name__ == "__main__":
    # Numeric example: 8 weeks of weekly sentiment readings.
    # Sentiment surges to 88% bulls in week 5 while price has just turned
    # over from 105 to 102 -- contrary opinion + confirmation -> exit long.
    readings = [
        SentimentReading(day=1,  pct_bulls=55, price=92.0),
        SentimentReading(day=8,  pct_bulls=62, price=96.0),
        SentimentReading(day=15, pct_bulls=70, price=100.0),
        SentimentReading(day=22, pct_bulls=78, price=104.0),
        SentimentReading(day=29, pct_bulls=85, price=105.5),
        SentimentReading(day=36, pct_bulls=88, price=102.0),  # extreme + reversal
        SentimentReading(day=43, pct_bulls=80, price=98.0),
        SentimentReading(day=50, pct_bulls=65, price=92.0),
    ]

    bulls, bears = find_extremes(readings)
    print(f"Bullish-extreme readings: {[r.day for r in bulls]}")
    print(f"Bearish-extreme readings: {[r.day for r in bears]}")

    exit_day = contrary_exit_signal(readings, position="long",
                                    confirm_with_price_reversal=True,
                                    reversal_lookback=2)
    print(f"\nLong-exit signal fires on day: {exit_day}")
    # Sample output:
    #   Bullish-extreme readings: [29, 36, 43]
    #   Bearish-extreme readings: []
    #   Long-exit signal fires on day: 36
