"""F-065 — Schwager Ch 17 advisory rules engine (simplified).

Codifies the most impactful trading rules from Schwager's
'Getting Started in Technical Analysis', Chapter 17.

Each rule is evaluated against the current recommendation context and
returns a RuleAdvisory indicating whether the rule was triggered.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.discipline.checks import DisciplineViolation


@dataclass
class RuleAdvisory:
    rule_id: str
    rule_text: str
    chapter: str
    triggered: bool
    severity: str       # "INFO" | "WARNING"
    detail: str = ""


# ---------------------------------------------------------------------------
# Rule catalogue (10 key Ch 17 rules)
# ---------------------------------------------------------------------------

_RULES = [
    {"id": "R-01", "text": "Always use a protective stop-loss on every trade.", "chapter": "Ch 8, 9"},
    {"id": "R-02", "text": "Never add to a losing position (no averaging down).", "chapter": "Ch 17"},
    {"id": "R-03", "text": "Never widen a stop once it has been placed.", "chapter": "Ch 9"},
    {"id": "R-04", "text": "Plan every trade: define entry, stop, and target before entering.", "chapter": "Ch 16"},
    {"id": "R-05", "text": "Reduce position size after a losing streak.", "chapter": "Ch 16"},
    {"id": "R-06", "text": "Aim for at least a 2:1 reward-to-risk ratio.", "chapter": "Ch 14"},
    {"id": "R-07", "text": "Let profits run; cut losses quickly.", "chapter": "Ch 16"},
    {"id": "R-08", "text": "Trade with the trend; use range strategies in sideways markets.", "chapter": "Ch 5, 6"},
    {"id": "R-09", "text": "Don't over-trade; fewer high-quality setups beat many marginal ones.", "chapter": "Ch 17"},
    {"id": "R-10", "text": "If the market does not act as expected after entry, exit quickly.", "chapter": "Ch 11"},
]


def evaluate_rules(
    action: str,
    stop_price: Optional[float],
    target_price: Optional[float],
    entry_price: Optional[float],
    direction: Optional[str],
    regime: Optional[str],
    recent_losses: int,
    loss_streak_threshold: int,
    violations: List[DisciplineViolation],
) -> List[RuleAdvisory]:
    """Evaluate all 10 rules against the current recommendation context."""
    advisories: List[RuleAdvisory] = []
    is_entry = action in ("BUY", "SELL_SHORT")

    # Precompute reward:risk
    rrr: Optional[float] = None
    if is_entry and entry_price and stop_price and target_price:
        risk = abs(entry_price - stop_price)
        reward = abs(target_price - entry_price)
        if risk > 0:
            rrr = reward / risk

    # R-01: stop on every trade
    triggered = is_entry and stop_price is None
    advisories.append(RuleAdvisory(
        rule_id="R-01",
        rule_text=_RULES[0]["text"],
        chapter=_RULES[0]["chapter"],
        triggered=triggered,
        severity="WARNING" if triggered else "INFO",
        detail="No stop set on entry" if triggered else "",
    ))

    # R-02: no averaging down (already captured in violations)
    triggered = any(v.rule_id == "F-061" for v in violations)
    advisories.append(RuleAdvisory(
        rule_id="R-02",
        rule_text=_RULES[1]["text"],
        chapter=_RULES[1]["chapter"],
        triggered=triggered,
        severity="WARNING" if triggered else "INFO",
        detail="Averaging down detected" if triggered else "",
    ))

    # R-03: no stop widening
    triggered = any(v.rule_id == "F-062" for v in violations)
    advisories.append(RuleAdvisory(
        rule_id="R-03",
        rule_text=_RULES[2]["text"],
        chapter=_RULES[2]["chapter"],
        triggered=triggered,
        severity="WARNING" if triggered else "INFO",
        detail="Stop was widened" if triggered else "",
    ))

    # R-04: plan before trade
    triggered = is_entry and (stop_price is None or target_price is None)
    advisories.append(RuleAdvisory(
        rule_id="R-04",
        rule_text=_RULES[3]["text"],
        chapter=_RULES[3]["chapter"],
        triggered=triggered,
        severity="WARNING" if triggered else "INFO",
        detail="Entry without complete stop/target plan" if triggered else "",
    ))

    # R-05: reduce size after loss streak
    triggered = recent_losses >= loss_streak_threshold
    advisories.append(RuleAdvisory(
        rule_id="R-05",
        rule_text=_RULES[4]["text"],
        chapter=_RULES[4]["chapter"],
        triggered=triggered,
        severity="WARNING" if triggered else "INFO",
        detail=f"{recent_losses} consecutive losses" if triggered else "",
    ))

    # R-06: minimum 2:1 R:R
    triggered = is_entry and rrr is not None and rrr < 1.5
    advisories.append(RuleAdvisory(
        rule_id="R-06",
        rule_text=_RULES[5]["text"],
        chapter=_RULES[5]["chapter"],
        triggered=triggered,
        severity="INFO",
        detail=f"R:R = {rrr:.2f}:1 (below 2:1 target)" if triggered else "",
    ))

    # R-07: let profits run (informational — no automatic check possible)
    advisories.append(RuleAdvisory(
        rule_id="R-07",
        rule_text=_RULES[6]["text"],
        chapter=_RULES[6]["chapter"],
        triggered=False,
        severity="INFO",
        detail="",
    ))

    # R-08: trade with the trend
    against_trend = False
    if regime and direction and is_entry:
        against_trend = (
            (regime == "TREND_UP" and direction == "SHORT")
            or (regime == "TREND_DOWN" and direction == "LONG")
        )
    advisories.append(RuleAdvisory(
        rule_id="R-08",
        rule_text=_RULES[7]["text"],
        chapter=_RULES[7]["chapter"],
        triggered=against_trend,
        severity="INFO",
        detail=f"Trading {direction} against {regime} regime" if against_trend else "",
    ))

    # R-09: don't over-trade (informational — no per-bar count available here)
    advisories.append(RuleAdvisory(
        rule_id="R-09",
        rule_text=_RULES[8]["text"],
        chapter=_RULES[8]["chapter"],
        triggered=False,
        severity="INFO",
        detail="",
    ))

    # R-10: failed signal / unexpected action (informational)
    advisories.append(RuleAdvisory(
        rule_id="R-10",
        rule_text=_RULES[9]["text"],
        chapter=_RULES[9]["chapter"],
        triggered=False,
        severity="INFO",
        detail="",
    ))

    return advisories
