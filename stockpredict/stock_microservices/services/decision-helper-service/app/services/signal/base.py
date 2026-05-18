"""Shared types for the signal engine pipeline (F-013 / F-014 / F-015)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class OHLCVBar:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "OHLCVBar":
        return cls(
            date=d["date"] if isinstance(d["date"], date) else date.fromisoformat(d["date"]),
            open=float(d.get("open") or d.get("close")),
            high=float(d.get("high") or d.get("close")),
            low=float(d.get("low") or d.get("close")),
            close=float(d["close"]),
            volume=int(d.get("volume") or 0),
        )


@dataclass
class RawSignal:
    """Output of one signal detector before confirmation."""
    kind: str                             # MA_CROSS | N_DAY_BREAKOUT | SR_BOUNCE | SR_BREAKOUT
    direction: str                        # LONG | SHORT
    confidence: float                     # 0..1
    bar_date: date
    trigger_price: float                  # price that triggered the signal
    evidence: Dict[str, Any] = field(default_factory=dict)


def _sma(closes: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average — returns a list of same length, None for warm-up bars."""
    result: List[Optional[float]] = []
    window: List[float] = []
    for c in closes:
        window.append(c)
        if len(window) >= period:
            result.append(sum(window[-period:]) / period)
        else:
            result.append(None)
    return result
