"""
Chapter 17 - Concept 3: Money Management
========================================
Position sizing and risk adjustment based on:
  - Per-trade risk cap (% of equity)
  - Total portfolio risk cap
  - Behavioral correction in losing streaks (reduce size, tighten stops)
  - Gradual scaling up in winning periods (NOT a sudden jump)

The book teaches: when going badly, cut size and tighten stops;
when going well, do NOT suddenly increase size or take riskier setups.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RiskPolicy:
    base_risk_per_trade_pct: float = 1.0      # 1% of equity per trade
    max_total_risk_pct: float = 25.0          # 25% across all open positions
    max_single_market_pct: float = 5.0        # cap per symbol
    drawdown_threshold_pct: float = 10.0      # when drawdown > this, downshift
    drawdown_size_multiplier: float = 0.5     # cut size in half during slumps
    drawdown_stop_tightener: float = 0.7      # tighten stop distance to 70%
    growth_size_multiplier_step: float = 0.1  # 10% size up per equity milestone


@dataclass
class Account:
    starting_equity: float
    current_equity: float
    peak_equity: float
    open_risk: float = 0.0                    # sum of $ at risk on open positions

    def drawdown_pct(self) -> float:
        if self.peak_equity == 0:
            return 0.0
        return max(0.0, (self.peak_equity - self.current_equity)
                   / self.peak_equity * 100)

    def equity_growth_pct(self) -> float:
        if self.starting_equity == 0:
            return 0.0
        return (self.current_equity - self.starting_equity) \
            / self.starting_equity * 100


def position_size(account: Account, policy: RiskPolicy,
                  entry_price: float, stop_price: float,
                  in_drawdown: Optional[bool] = None) -> dict:
    """
    Compute share count using fixed-fractional risk sizing,
    with a behavioral overlay for drawdown periods.

    Returns dict with shares, dollar risk, and notes.
    """
    if entry_price <= 0 or stop_price <= 0:
        raise ValueError("Prices must be positive")
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share == 0:
        raise ValueError("Stop equal to entry — risk_per_share is 0")

    # Adaptive risk percent
    risk_pct = policy.base_risk_per_trade_pct
    notes = []

    dd = account.drawdown_pct()
    is_dd = in_drawdown if in_drawdown is not None \
        else dd >= policy.drawdown_threshold_pct

    if is_dd:
        risk_pct *= policy.drawdown_size_multiplier
        notes.append(f"Drawdown {dd:.1f}% — risk halved to {risk_pct:.2f}%")
    else:
        # Gradual scale-up — NOT a sudden jump.
        growth = account.equity_growth_pct()
        steps = int(max(0, growth) // 10)        # one step per 10% growth
        if steps > 0:
            scale = 1.0 + steps * policy.growth_size_multiplier_step
            scale = min(scale, 1.5)              # cap at 50% above base
            risk_pct *= scale
            notes.append(f"Equity +{growth:.1f}% → "
                         f"gradual size scale x{scale:.2f}")

    dollar_risk_target = account.current_equity * risk_pct / 100

    # Total portfolio risk check
    remaining_capacity = (
        account.current_equity * policy.max_total_risk_pct / 100
        - account.open_risk
    )
    if remaining_capacity <= 0:
        notes.append("Portfolio risk cap reached — no new positions allowed.")
        return {"shares": 0, "dollar_risk": 0, "notes": notes}

    dollar_risk = min(dollar_risk_target, remaining_capacity)
    if dollar_risk < dollar_risk_target:
        notes.append(f"Risk capped by portfolio cap "
                     f"(${remaining_capacity:.2f} remaining)")

    shares = int(dollar_risk // risk_per_share)
    return {
        "shares": shares,
        "dollar_risk": shares * risk_per_share,
        "risk_per_share": risk_per_share,
        "applied_risk_pct": risk_pct,
        "notes": notes,
    }


def liquidate_losers_first_priority(open_positions: list[dict]) -> list[dict]:
    """
    Lefèvre/Schwager rule: when you must reduce exposure,
    cut LOSERS first, never the winners.
    Sorts list with biggest losers first.
    """
    return sorted(open_positions,
                  key=lambda p: p["unrealized_pnl"])  # most negative first


# ─── DEMO ────────────────────────────────────────────────────────
if __name__ == "__main__":
    policy = RiskPolicy()

    # Scenario A: Healthy account, 15% growth
    acct = Account(starting_equity=100_000,
                   current_equity=115_000, peak_equity=115_000)
    sizing = position_size(acct, policy, entry_price=50, stop_price=47)
    print("Scenario A — equity +15%:")
    for k, v in sizing.items():
        print(f"  {k}: {v}")

    # Scenario B: 12% drawdown
    acct2 = Account(starting_equity=100_000, current_equity=88_000,
                    peak_equity=100_000)
    sizing2 = position_size(acct2, policy, entry_price=50, stop_price=47)
    print("\nScenario B — drawdown 12%:")
    for k, v in sizing2.items():
        print(f"  {k}: {v}")

    # Scenario C: liquidation order during a slump
    open_pos = [
        {"symbol": "AAA", "unrealized_pnl": -800},
        {"symbol": "BBB", "unrealized_pnl": +1200},
        {"symbol": "CCC", "unrealized_pnl": -2200},
        {"symbol": "DDD", "unrealized_pnl": +400},
    ]
    print("\nScenario C — cut losers first (in priority order):")
    for p in liquidate_losers_first_priority(open_pos):
        print(f"  {p['symbol']}: ${p['unrealized_pnl']:+}")
