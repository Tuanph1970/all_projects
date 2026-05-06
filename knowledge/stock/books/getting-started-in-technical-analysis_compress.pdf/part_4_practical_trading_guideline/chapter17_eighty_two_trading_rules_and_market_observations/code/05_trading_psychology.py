"""
Chapter 17 - Concept 5: Trading Psychology Heuristics
=====================================================
Practical helpers for the behavioral side of the chapter:
  - Detect "winners feel right early" — flag a trade as suspect
    if it goes underwater immediately
  - Quantify the Friday-close vs Monday-open spread to validate
    the "decide on Friday" rule
  - A simple intraday-decision filter: if you must trade midday,
    log it and rate yourself later
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DecisionContext(Enum):
    PLANNED_END_OF_DAY = "planned_eod"
    INTRADAY_IMPULSE = "intraday_impulse"
    FRIDAY_CLOSE = "friday_close"


@dataclass
class TradeOutcomeFlag:
    in_profit_first_day: bool
    underwater_first_day: bool
    decision_context: DecisionContext
    note: str = ""


def early_assessment(entry_price: float, day1_close: float,
                     direction: str) -> TradeOutcomeFlag:
    """
    Schwager: 'Winning trades tend to be ahead right from the start.'
    Use day-1 result as an early-warning signal — not a hard exit rule.
    """
    sign = 1 if direction == "long" else -1
    move = sign * (day1_close - entry_price)
    if move > 0:
        return TradeOutcomeFlag(
            in_profit_first_day=True, underwater_first_day=False,
            decision_context=DecisionContext.PLANNED_END_OF_DAY,
            note="Trade in profit day 1 — consistent with winner profile.")
    if move < 0:
        return TradeOutcomeFlag(
            in_profit_first_day=False, underwater_first_day=True,
            decision_context=DecisionContext.PLANNED_END_OF_DAY,
            note=("Trade underwater on day 1. "
                  "Tighten stop and watch for premise-broken signals."))
    return TradeOutcomeFlag(
        in_profit_first_day=False, underwater_first_day=False,
        decision_context=DecisionContext.PLANNED_END_OF_DAY,
        note="Trade flat on day 1 — no signal either way.")


@dataclass
class FridayMondayStudy:
    """
    Compare your win rate when entering at Friday close vs Monday open.
    Schwager claims Friday close gives clearer signals — verify with data.
    """
    friday_entries: list[float] = field(default_factory=list)
    monday_entries: list[float] = field(default_factory=list)

    def record(self, weekday_label: str, pnl: float) -> None:
        if weekday_label.lower() == "friday":
            self.friday_entries.append(pnl)
        elif weekday_label.lower() == "monday":
            self.monday_entries.append(pnl)

    def summary(self) -> dict:
        def stats(lst: list[float]) -> dict:
            if not lst:
                return {"count": 0, "win_rate": 0, "avg_pnl": 0}
            wins = sum(1 for x in lst if x > 0)
            return {
                "count": len(lst),
                "win_rate": wins / len(lst) * 100,
                "avg_pnl": sum(lst) / len(lst),
            }
        return {
            "friday": stats(self.friday_entries),
            "monday": stats(self.monday_entries),
        }


@dataclass
class IntradayDecisionLog:
    """
    Force a moment of friction before any intraday decision.
    Logging it makes the trader confront the rule honestly.
    """
    entries: list[dict] = field(default_factory=list)

    def log(self, symbol: str, decision: str, rationale: str) -> None:
        self.entries.append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "symbol": symbol,
            "decision": decision,
            "rationale": rationale,
            "outcome": None,           # filled in after market close
            "would_have_done_at_eod": None,
        })

    def review(self, idx: int, outcome_pnl: float,
               would_have_done_at_eod: bool) -> None:
        e = self.entries[idx]
        e["outcome"] = outcome_pnl
        e["would_have_done_at_eod"] = would_have_done_at_eod

    def stats(self) -> dict:
        reviewed = [e for e in self.entries if e["outcome"] is not None]
        if not reviewed:
            return {"reviewed": 0}
        winners = [e for e in reviewed if e["outcome"] > 0]
        unique_to_intraday = [
            e for e in reviewed if not e["would_have_done_at_eod"]
        ]
        return {
            "reviewed": len(reviewed),
            "win_rate_pct": len(winners) / len(reviewed) * 100,
            "avg_pnl": sum(e["outcome"] for e in reviewed) / len(reviewed),
            "intraday_only_count": len(unique_to_intraday),
            "intraday_only_pnl": (
                sum(e["outcome"] for e in unique_to_intraday)
                / max(len(unique_to_intraday), 1)
            ),
        }


# ─── DEMO ────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Early assessment
    flag = early_assessment(entry_price=100, day1_close=98, direction="long")
    print("Day-1 flag:", flag.note)

    # 2. Friday vs Monday study
    study = FridayMondayStudy()
    for pnl in [120, 80, -30, 200, 150, 60, -20, 90, 110]:
        study.record("friday", pnl)
    for pnl in [-50, 40, -100, 30, -20, 80, -60, 20]:
        study.record("monday", pnl)
    print("\nFri/Mon study:", study.summary())

    # 3. Intraday log
    log = IntradayDecisionLog()
    log.log("AAPL", "bought 50 shares", "felt the pullback was over")
    log.log("MSFT", "sold half", "afternoon weakness")
    log.review(0, outcome_pnl=-200, would_have_done_at_eod=False)
    log.review(1, outcome_pnl=+30, would_have_done_at_eod=True)
    print("\nIntraday-decision audit:", log.stats())
