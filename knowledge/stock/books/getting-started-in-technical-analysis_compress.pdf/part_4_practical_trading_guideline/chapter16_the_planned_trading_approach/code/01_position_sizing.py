"""
Chapter 16 — Risk Control: Position Sizing & Maximum Risk Per Trade
====================================================================
Implements the core risk-control rules from Schwager's planned trading approach.
Treat every trade through the lens of: "What's the max I can lose, in dollars?"
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class RiskConfig:
    """Risk-control configuration for an account."""
    account_equity: float
    max_risk_per_trade_pct: float = 0.02       # 2% — Schwager suggests cap at ~3%, never above 7%
    max_open_risk_pct: float = 0.30            # cumulative implied risk cap (25-35% guidance)
    correlation_leverage_factor: float = 0.5   # cut size in half if heavily correlated to existing position


def position_size(
    entry: float,
    stop: float,
    equity: float,
    risk_pct: float = 0.02,
    direction: Literal["long", "short"] = "long",
) -> dict:
    """
    Calculate the max number of shares/contracts using fixed-fractional risk.

    shares = (equity * risk_pct) / |entry - stop|

    Returns a dict with the size, dollar risk, and a sanity flag.
    """
    if entry <= 0 or stop <= 0:
        raise ValueError("Entry and stop prices must be positive.")

    risk_per_unit = abs(entry - stop)
    if risk_per_unit == 0:
        raise ValueError("Entry equals stop — no risk distance defined.")

    # For longs the stop should be below entry; for shorts above. Warn if reversed.
    if direction == "long" and stop >= entry:
        raise ValueError("Long stop must be BELOW entry.")
    if direction == "short" and stop <= entry:
        raise ValueError("Short stop must be ABOVE entry.")

    dollar_budget = equity * risk_pct
    shares = int(dollar_budget // risk_per_unit)  # always round DOWN — never exceed risk
    actual_dollar_risk = shares * risk_per_unit

    return {
        "shares": shares,
        "dollar_budget": round(dollar_budget, 2),
        "actual_dollar_risk": round(actual_dollar_risk, 2),
        "risk_per_unit": round(risk_per_unit, 4),
        "capital_required": round(shares * entry, 2),
        "risk_pct_actual": round(actual_dollar_risk / equity * 100, 3),
    }


def total_open_risk(open_positions: list[dict]) -> float:
    """Sum the implied dollar risk across every open position."""
    return sum(p["shares"] * abs(p["entry"] - p["current_stop"]) for p in open_positions)


def can_add_new_position(
    proposed_risk: float, open_positions: list[dict], cfg: RiskConfig
) -> tuple[bool, str]:
    """
    Check whether adding a new trade would push cumulative open risk over the cap.
    Returns (allowed, reason).
    """
    current = total_open_risk(open_positions)
    after = current + proposed_risk
    cap = cfg.account_equity * cfg.max_open_risk_pct

    if after > cap:
        return False, (
            f"BLOCKED — adding ${proposed_risk:,.0f} would push open risk to "
            f"${after:,.0f} ({after/cfg.account_equity*100:.1f}%), over the "
            f"{cfg.max_open_risk_pct*100:.0f}% cap."
        )
    return True, f"OK — open risk after entry: ${after:,.0f} ({after/cfg.account_equity*100:.1f}%)."


# -------- Demo --------
if __name__ == "__main__":
    cfg = RiskConfig(account_equity=100_000, max_risk_per_trade_pct=0.03)

    print("=" * 60)
    print("Position sizing — TSLA long, entry $200, stop $190")
    print("=" * 60)
    sized = position_size(entry=200, stop=190, equity=cfg.account_equity, risk_pct=0.03)
    for k, v in sized.items():
        print(f"  {k:<22}  {v}")

    print()
    print("=" * 60)
    print("Cumulative open-risk check")
    print("=" * 60)
    open_book = [
        {"symbol": "AAPL", "shares": 200, "entry": 175, "current_stop": 168},
        {"symbol": "JPM",  "shares": 400, "entry": 155, "current_stop": 160},  # short
    ]
    print(f"  Current open risk: ${total_open_risk(open_book):,.0f}")

    ok, msg = can_add_new_position(sized["actual_dollar_risk"], open_book, cfg)
    print(f"  {msg}")
