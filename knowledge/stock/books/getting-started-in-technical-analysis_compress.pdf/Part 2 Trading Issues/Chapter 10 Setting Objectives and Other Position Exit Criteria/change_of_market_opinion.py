"""
Change of Market Opinion — Chapter 10, Concept 7
==================================================
The non-mechanical exit: maintain the position until the
trader's informed market opinion shifts to at least neutral.

Schwager: "This is another approach with very little flash,
but lots of common sense."

Unlike Concepts 1-6, this is inherently subjective. The code
here provides a FRAMEWORK for structuring and tracking opinion
changes — checklist-based conviction scoring that makes the
subjective process more disciplined.

The module also provides a synthesis function that combines
ALL Chapter 10 exit methods into a unified decision framework.

This module provides:
  - Conviction scoring framework
  - Opinion change detection
  - Exit decision synthesis (all Ch. 10 methods combined)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from enum import Enum


class MarketOpinion(Enum):
    """Schwager's opinion spectrum for position management."""
    STRONGLY_BULLISH = "strongly_bullish"
    BULLISH = "bullish"
    MODERATELY_BULLISH = "moderately_bullish"
    NEUTRAL = "neutral"
    MODERATELY_BEARISH = "moderately_bearish"
    BEARISH = "bearish"
    STRONGLY_BEARISH = "strongly_bearish"

    @property
    def is_bullish(self) -> bool:
        return self in (
            MarketOpinion.STRONGLY_BULLISH,
            MarketOpinion.BULLISH,
            MarketOpinion.MODERATELY_BULLISH,
        )

    @property
    def is_bearish(self) -> bool:
        return self in (
            MarketOpinion.STRONGLY_BEARISH,
            MarketOpinion.BEARISH,
            MarketOpinion.MODERATELY_BEARISH,
        )

    @property
    def is_neutral(self) -> bool:
        return self == MarketOpinion.NEUTRAL


@dataclass
class ConvictionFactor:
    """A single factor contributing to the trader's conviction."""
    name: str
    status: str  # 'supporting', 'neutral', 'opposing'
    weight: float = 1.0  # Relative importance (0.5 to 2.0)
    notes: str = ""

    @property
    def score(self) -> float:
        """Returns +1 (supporting), 0 (neutral), or -1 (opposing), weighted."""
        base = {'supporting': 1.0, 'neutral': 0.0, 'opposing': -1.0}
        return base.get(self.status, 0.0) * self.weight


@dataclass
class ConvictionAssessment:
    """
    Structured assessment of current market conviction.
    
    This framework converts the subjective "change of market
    opinion" concept into a disciplined checklist process.
    The trader scores each factor, and the aggregate determines
    whether opinion has shifted to neutral.
    """
    factors: List[ConvictionFactor]
    position_direction: str = 'long'  # 'long' or 'short'

    @property
    def raw_score(self) -> float:
        """Sum of all factor scores. Positive = bullish, negative = bearish."""
        return sum(f.score for f in self.factors)

    @property
    def max_possible(self) -> float:
        return sum(f.weight for f in self.factors)

    @property
    def conviction_pct(self) -> float:
        """Conviction as percentage (0-100). 50 = neutral."""
        if self.max_possible == 0:
            return 50.0
        normalized = (self.raw_score / self.max_possible + 1) / 2 * 100
        return max(0.0, min(100.0, normalized))

    @property
    def opinion(self) -> MarketOpinion:
        """Map conviction percentage to opinion category."""
        pct = self.conviction_pct
        if pct >= 80:
            return MarketOpinion.STRONGLY_BULLISH
        elif pct >= 65:
            return MarketOpinion.BULLISH
        elif pct >= 55:
            return MarketOpinion.MODERATELY_BULLISH
        elif pct >= 45:
            return MarketOpinion.NEUTRAL
        elif pct >= 35:
            return MarketOpinion.MODERATELY_BEARISH
        elif pct >= 20:
            return MarketOpinion.BEARISH
        return MarketOpinion.STRONGLY_BEARISH

    @property
    def should_exit(self) -> bool:
        """
        Schwager: exit when opinion changes to 'at least neutral.'
        
        For longs: exit if opinion is neutral or bearish.
        For shorts: exit if opinion is neutral or bullish.
        """
        opinion = self.opinion
        if self.position_direction == 'long':
            return opinion.is_neutral or opinion.is_bearish
        else:
            return opinion.is_neutral or opinion.is_bullish

    @property
    def should_reverse(self) -> bool:
        """
        Ch. 11: "the truly skilled trader will be able to do
        a 180-degree turn, reversing a position."
        
        Only suggest reversal when conviction is strongly
        opposite to current position.
        """
        opinion = self.opinion
        if self.position_direction == 'long':
            return opinion in (MarketOpinion.BEARISH,
                             MarketOpinion.STRONGLY_BEARISH)
        else:
            return opinion in (MarketOpinion.BULLISH,
                             MarketOpinion.STRONGLY_BULLISH)

    def summary(self) -> str:
        """Human-readable assessment summary."""
        supporting = [f for f in self.factors if f.status == 'supporting']
        opposing = [f for f in self.factors if f.status == 'opposing']
        neutral = [f for f in self.factors if f.status == 'neutral']

        lines = [
            f"Conviction: {self.conviction_pct:.0f}% → {self.opinion.value}",
            f"Position: {self.position_direction}",
            f"Supporting factors ({len(supporting)}): "
            + ", ".join(f.name for f in supporting),
            f"Opposing factors ({len(opposing)}): "
            + ", ".join(f.name for f in opposing),
            f"Neutral factors ({len(neutral)}): "
            + ", ".join(f.name for f in neutral),
        ]

        if self.should_reverse:
            lines.append("→ REVERSE POSITION (Ch. 11: 180° turn)")
        elif self.should_exit:
            lines.append("→ EXIT POSITION (opinion at neutral or opposing)")
        else:
            lines.append("→ HOLD POSITION (conviction intact)")

        return "\n".join(lines)


def build_default_checklist(position: str = 'long') -> List[ConvictionFactor]:
    """
    Create a default conviction checklist using Chapter 10's
    exit methods as factors.
    
    Each factor starts as 'supporting' (the trade was entered
    for a reason). The trader updates each factor as conditions
    change.
    
    Parameters
    ----------
    position : str
        'long' or 'short'.
        
    Returns
    -------
    list of ConvictionFactor
    """
    return [
        ConvictionFactor(
            name="Trend direction",
            status="supporting",
            weight=2.0,
            notes="Is the primary trend still in your favor? (Ch. 3)"
        ),
        ConvictionFactor(
            name="Chart pattern structure",
            status="supporting",
            weight=1.5,
            notes="Are chart-based objectives still valid? (Ch. 10 Concept 1)"
        ),
        ConvictionFactor(
            name="Support/resistance context",
            status="supporting",
            weight=1.0,
            notes="Is price approaching or respecting key S/R? (Ch. 10 Concept 3)"
        ),
        ConvictionFactor(
            name="Momentum (RSI/oscillators)",
            status="supporting",
            weight=1.0,
            notes="OB/OS condition? Divergence? (Ch. 10 Concept 4)"
        ),
        ConvictionFactor(
            name="Sentiment",
            status="neutral",
            weight=0.5,
            notes="Contrary opinion at extreme? (Ch. 10 Concept 5)"
        ),
        ConvictionFactor(
            name="Volume confirmation",
            status="supporting",
            weight=0.5,
            notes="Volume supporting the move or diverging?"
        ),
        ConvictionFactor(
            name="Failed signal risk",
            status="supporting",
            weight=2.0,
            notes="Any signs of a failed breakout? (Ch. 11)"
        ),
        ConvictionFactor(
            name="Higher timeframe alignment",
            status="supporting",
            weight=1.5,
            notes="Weekly/monthly trend supportive? (Ch. 7 Multi-TF)"
        ),
    ]


@dataclass
class ExitDecision:
    """
    Synthesized exit decision combining all Chapter 10 methods.
    
    This is the culmination of the chapter: no single method
    is sufficient, but combined they form a complete framework.
    """
    method_signals: Dict[str, str]  # method_name → 'exit' | 'hold' | 'caution'
    conviction: ConvictionAssessment
    trailing_stop_hit: bool
    final_action: str  # 'hold', 'partial_exit', 'full_exit', 'reverse'
    reasoning: str

    def summary(self) -> str:
        lines = ["=== Exit Decision Synthesis ==="]
        for method, signal in self.method_signals.items():
            icon = {"exit": "EXIT", "hold": "HOLD", "caution": "CAUTION"}
            lines.append(f"  [{icon.get(signal, '?')}] {method}")
        lines.append(f"\n  Conviction: {self.conviction.conviction_pct:.0f}%"
                     f" ({self.conviction.opinion.value})")
        lines.append(f"  Trailing stop: {'HIT' if self.trailing_stop_hit else 'intact'}")
        lines.append(f"\n  → {self.final_action.upper()}: {self.reasoning}")
        return "\n".join(lines)


def synthesize_exit_decision(
    method_signals: Dict[str, str],
    conviction: ConvictionAssessment,
    trailing_stop_hit: bool = False,
) -> ExitDecision:
    """
    Combine all Chapter 10 exit methods into a unified decision.
    
    Decision hierarchy:
    1. Trailing stop hit → full exit (mechanical override)
    2. Conviction at neutral/opposing → full exit or reverse
    3. Multiple methods signaling exit → partial exit
    4. Single method signaling → caution, hold with awareness
    5. All methods holding → hold
    
    Parameters
    ----------
    method_signals : dict
        Each Chapter 10 method's current signal.
        Keys: method names. Values: 'exit', 'hold', 'caution'.
    conviction : ConvictionAssessment
        Current conviction assessment.
    trailing_stop_hit : bool
        Whether the trailing stop has been triggered.
        
    Returns
    -------
    ExitDecision
    """
    exit_count = sum(1 for s in method_signals.values() if s == 'exit')
    caution_count = sum(1 for s in method_signals.values() if s == 'caution')

    # Priority 1: Trailing stop = immediate mechanical exit
    if trailing_stop_hit:
        return ExitDecision(
            method_signals=method_signals,
            conviction=conviction,
            trailing_stop_hit=True,
            final_action='full_exit',
            reasoning="Trailing stop triggered — mechanical exit overrides all.",
        )

    # Priority 2: Conviction collapsed → exit or reverse
    if conviction.should_reverse:
        return ExitDecision(
            method_signals=method_signals,
            conviction=conviction,
            trailing_stop_hit=False,
            final_action='reverse',
            reasoning=(
                f"Conviction at {conviction.conviction_pct:.0f}% "
                f"({conviction.opinion.value}). Ch. 11: "
                f"'the truly skilled trader will do a 180-degree turn.'"
            ),
        )

    if conviction.should_exit:
        return ExitDecision(
            method_signals=method_signals,
            conviction=conviction,
            trailing_stop_hit=False,
            final_action='full_exit',
            reasoning=(
                f"Opinion shifted to {conviction.opinion.value}. "
                f"Ch. 10: 'maintain position until opinion changes "
                f"to at least neutral.'"
            ),
        )

    # Priority 3: Multiple methods signaling exit
    if exit_count >= 2:
        return ExitDecision(
            method_signals=method_signals,
            conviction=conviction,
            trailing_stop_hit=False,
            final_action='partial_exit',
            reasoning=(
                f"{exit_count} exit methods triggered (confluence). "
                f"Take partial profits, trail the remainder."
            ),
        )

    # Priority 4: Single method or caution signals
    if exit_count == 1 or caution_count >= 2:
        return ExitDecision(
            method_signals=method_signals,
            conviction=conviction,
            trailing_stop_hit=False,
            final_action='partial_exit',
            reasoning=(
                "Some exit signals present. Consider partial "
                "profit-taking; tighten trailing stop."
            ),
        )

    # Priority 5: All clear
    return ExitDecision(
        method_signals=method_signals,
        conviction=conviction,
        trailing_stop_hit=False,
        final_action='hold',
        reasoning="No exit signals. Conviction intact. Hold position.",
    )


# --- Example usage ---
if __name__ == "__main__":
    print("=== Scenario 1: Strong Conviction — Hold ===")
    factors = build_default_checklist('long')
    assessment = ConvictionAssessment(factors, 'long')
    print(assessment.summary())
    print()

    print("=== Scenario 2: Doubt Creeping In — Exit ===")
    factors2 = build_default_checklist('long')
    factors2[0].status = 'neutral'     # Trend unclear
    factors2[2].status = 'opposing'    # At resistance
    factors2[3].status = 'opposing'    # RSI overbought
    factors2[4].status = 'opposing'    # Sentiment extreme
    factors2[6].status = 'neutral'     # Failed signal risk unclear
    assessment2 = ConvictionAssessment(factors2, 'long')
    print(assessment2.summary())
    print()

    print("=== Scenario 3: Full Reversal — 180° Turn ===")
    factors3 = build_default_checklist('long')
    for f in factors3:
        f.status = 'opposing'
    factors3[4].status = 'opposing'
    assessment3 = ConvictionAssessment(factors3, 'long')
    print(assessment3.summary())
    print()

    print("=== Scenario 4: Synthesized Exit Decision ===")
    method_signals = {
        'Chart-based objective': 'exit',       # Target hit
        'Measured move': 'exit',               # MM target reached
        'S/R objective': 'caution',            # Near resistance
        'OB/OS oscillator': 'exit',            # RSI overbought
        'Contrary opinion': 'caution',         # Sentiment high
        'Trailing stop': 'hold',               # Not yet triggered
    }
    decision = synthesize_exit_decision(
        method_signals=method_signals,
        conviction=assessment2,
        trailing_stop_hit=False,
    )
    print(decision.summary())
