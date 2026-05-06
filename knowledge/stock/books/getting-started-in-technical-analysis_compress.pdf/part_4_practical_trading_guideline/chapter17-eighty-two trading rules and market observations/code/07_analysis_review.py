"""
Chapter 17 - Concept 7: Analysis & Review
=========================================
Implements three durable artifacts the chapter prescribes:
  - Trader's Diary: per-trade rationale + lessons (filled at entry,
    revisited at exit)
  - Patterns Chart Book: noteworthy chart patterns logged + their
    eventual outcomes
  - Trading Rules Doc: living playbook reviewed every quarter

Plus a simple scheduler that nags the trader when reviews are overdue.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import json
from pathlib import Path


class ReviewKind(Enum):
    DAILY_CHARTS = "daily_charts"
    LONG_TERM_CHARTS = "long_term_charts"   # every 2-4 weeks
    RULES = "rules"                          # quarterly
    DIARY = "diary"                          # quarterly
    PATTERNS_BOOK = "patterns_book"          # quarterly


REVIEW_INTERVALS = {
    ReviewKind.DAILY_CHARTS: timedelta(days=1),
    ReviewKind.LONG_TERM_CHARTS: timedelta(days=21),
    ReviewKind.RULES: timedelta(days=90),
    ReviewKind.DIARY: timedelta(days=90),
    ReviewKind.PATTERNS_BOOK: timedelta(days=90),
}


@dataclass
class DiaryEntry:
    """A trader's-diary entry. Fill `reasons` and `intended_*` AT ENTRY."""
    symbol: str
    direction: str
    entry_date: str
    entry_price: float
    intended_stop: float
    intended_objective: Optional[float]
    reasons: str                              # written before the trade
    pattern_tags: list[str] = field(default_factory=list)
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    net_pnl: Optional[float] = None
    lessons: str = ""                         # filled at exit / review
    mistakes: list[str] = field(default_factory=list)


@dataclass
class PatternEntry:
    """A pattern-chart-book entry. Predict at observation, follow up later."""
    pattern_id: str
    observation_date: str
    symbol: str
    pattern_description: str
    predicted_resolution: str                 # what you THINK will happen
    actual_resolution: Optional[str] = None   # filled in at follow-up
    follow_up_date: Optional[str] = None


@dataclass
class TradersJournal:
    """Persists the three artifacts to disk as JSON for durability."""
    storage_path: Path
    diary: list[DiaryEntry] = field(default_factory=list)
    patterns: list[PatternEntry] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    last_review: dict = field(default_factory=dict)  # {ReviewKind.value: iso}

    def add_trade(self, e: DiaryEntry) -> None:
        self.diary.append(e)
        self.save()

    def close_trade(self, symbol: str, exit_date: str,
                    exit_price: float, net_pnl: float,
                    lessons: str, mistakes: Optional[list[str]] = None) -> None:
        # Match the most recent open entry for the symbol
        for e in reversed(self.diary):
            if e.symbol == symbol and e.exit_date is None:
                e.exit_date = exit_date
                e.exit_price = exit_price
                e.net_pnl = net_pnl
                e.lessons = lessons
                e.mistakes = mistakes or []
                self.save()
                return

    def add_pattern(self, p: PatternEntry) -> None:
        self.patterns.append(p)
        self.save()

    def follow_up_pattern(self, pattern_id: str, follow_up_date: str,
                          actual_resolution: str) -> None:
        for p in self.patterns:
            if p.pattern_id == pattern_id:
                p.follow_up_date = follow_up_date
                p.actual_resolution = actual_resolution
                self.save()
                return

    def mark_review(self, kind: ReviewKind) -> None:
        self.last_review[kind.value] = datetime.now().isoformat()
        self.save()

    def overdue_reviews(self) -> list[ReviewKind]:
        now = datetime.now()
        result = []
        for kind, interval in REVIEW_INTERVALS.items():
            last_iso = self.last_review.get(kind.value)
            if last_iso is None:
                result.append(kind)
                continue
            if datetime.fromisoformat(last_iso) + interval < now:
                result.append(kind)
        return result

    # ── Pattern statistics ─────────────────────────────────────
    def pattern_accuracy(self) -> dict:
        """How often does my reading of patterns match the outcome?"""
        followed = [p for p in self.patterns if p.actual_resolution]
        if not followed:
            return {"reviewed": 0, "accuracy_pct": 0}
        correct = sum(1 for p in followed
                      if p.predicted_resolution.lower()
                      in p.actual_resolution.lower())
        return {
            "reviewed": len(followed),
            "accuracy_pct": correct / len(followed) * 100,
        }

    # ── Persistence ────────────────────────────────────────────
    def save(self) -> None:
        data = {
            "diary": [asdict(d) for d in self.diary],
            "patterns": [asdict(p) for p in self.patterns],
            "rules": self.rules,
            "last_review": self.last_review,
        }
        self.storage_path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path) -> "TradersJournal":
        if not path.exists():
            j = cls(storage_path=path)
            j.save()
            return j
        d = json.loads(path.read_text())
        j = cls(storage_path=path)
        j.diary = [DiaryEntry(**e) for e in d.get("diary", [])]
        j.patterns = [PatternEntry(**e) for e in d.get("patterns", [])]
        j.rules = d.get("rules", [])
        j.last_review = d.get("last_review", {})
        return j


# ─── DEMO ────────────────────────────────────────────────────────
if __name__ == "__main__":
    journal = TradersJournal(storage_path=Path("/tmp/journal.json"))

    # 1. Log a trade at entry — reasons written BEFORE outcome is known
    journal.add_trade(DiaryEntry(
        symbol="AAPL",
        direction="long",
        entry_date="2024-09-12",
        entry_price=220.50,
        intended_stop=212.00,
        intended_objective=240.00,
        reasons=("Bull flag breakout above $219 after 3-week consolidation; "
                 "above 50DMA; volume confirming."),
        pattern_tags=["bull_flag", "trend_continuation"],
    ))

    # 2. Note an interesting pattern in another stock
    journal.add_pattern(PatternEntry(
        pattern_id="P-2024-09-12-NVDA",
        observation_date="2024-09-12",
        symbol="NVDA",
        pattern_description="Wide-ranging down day after 80% advance",
        predicted_resolution="Trend reversal — multi-week downside follow-through",
    ))

    # 3. Quarterly: close the trade and write what you learned
    journal.close_trade(
        symbol="AAPL",
        exit_date="2024-10-15",
        exit_price=235.00,
        net_pnl=14.50 * 100,
        lessons="Letting trailing stop run worked. Initial objective at $240 would have caused premature exit.",
        mistakes=["Sized 20% smaller than rules called for — left money on table."],
    )

    # 4. Follow up the pattern observation
    journal.follow_up_pattern(
        pattern_id="P-2024-09-12-NVDA",
        follow_up_date="2024-10-15",
        actual_resolution="Trend reversal confirmed — declined 22% over 4 weeks",
    )

    # 5. Check the review schedule
    print("Overdue reviews:")
    for kind in journal.overdue_reviews():
        print(f"  - {kind.value}")
    journal.mark_review(ReviewKind.DAILY_CHARTS)

    # 6. How accurate are my pattern predictions?
    print("\nPattern accuracy:", journal.pattern_accuracy())

    print(f"\nJournal persisted at {journal.storage_path}")
