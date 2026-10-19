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


# ---------------------------------------------------------------------------
# Backlog #80 — proportional transaction costs
# ---------------------------------------------------------------------------

def trade_cost(
    notional: float,
    side: str,
    commission_pct: float,
    sell_tax_pct: float = 0.0,
    flat_fee: float = 0.0,
) -> float:
    """Cost of one side of a trade, as money.

    Backlog #80. The harness used to charge a **flat fee per trade**, and on
    its own defaults that produced commission of 1.8x the gross result it was
    supposed to measure — so every A/B run through it was arbitrated by the
    cost model rather than by the thing under test. A flat fee is also simply
    wrong for the market this platform trades: Vietnamese brokerage is a
    percentage of turnover, and the sell side additionally pays a transfer
    tax on proceeds.

    Args:
        notional: shares x fill price, i.e. the turnover of this side.
        side: 'BUY' | 'SELL_SHORT' | 'SELL' | 'COVER'. The tax applies only to
            the side that receives proceeds.
        commission_pct: brokerage, percent of turnover (VN brokers are
            typically 0.15-0.35).
        sell_tax_pct: percent of proceeds, charged on disposal only (VN: 0.1).
        flat_fee: a per-side fixed fee, kept for brokers that have one and so
            that the old flat model remains expressible.

    Costs are positive numbers; the caller subtracts them.
    """
    if notional <= 0:
        return max(0.0, flat_fee)

    cost = notional * max(0.0, commission_pct) / 100.0 + max(0.0, flat_fee)
    if side in ("SELL", "COVER"):
        cost += notional * max(0.0, sell_tax_pct) / 100.0
    return cost
