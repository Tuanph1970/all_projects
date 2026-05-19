"""F-052 — Slippage + commissions model (Schwager Ch 15).

Adverse slippage is applied at every fill:
  BUY / SELL_SHORT: pay a higher price  (bps added)
  SELL / COVER:     receive a lower price (bps subtracted)
"""
from __future__ import annotations


def apply_slippage(price: float, side: str, bps: float) -> float:
    """Return the fill price after slippage.

    Args:
        price: Nominal fill price (close of signal bar).
        side:  'BUY' | 'SELL_SHORT' | 'SELL' | 'COVER'.
        bps:   Slippage in basis points (e.g. 5 = 0.05 %).
    """
    factor = bps / 10_000.0
    if side in ("BUY", "SELL_SHORT"):
        return price * (1.0 + factor)
    return price * (1.0 - factor)
