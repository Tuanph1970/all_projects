"""features/ — news as model covariates: decayed INTENSITY and decayed POLARITY.

Backlog #106. Pure: no I/O, no database, no clock — so it is testable offline the
way event-reaction-lib and darts_trainer are. The repository/endpoint layer feeds
it rows and reindexes the result; everything causal about the design lives here.

FOUR DECISIONS THAT MATTER, in the order they bite.

1. INTENSITY AND POLARITY ARE SEPARATE SERIES, never one field. A single
   "sentiment" column with "normal" in the middle cannot distinguish NO news from
   NEUTRAL news, and both are ~0 for most rows. Attention is often the more
   predictive half, so article volume gets its own series and keeps its meaning
   when polarity is undefined.

2. THE IMPULSE DECAYS. News is not one bar. Without decay the series is almost
   all zeros and a sequence model has nothing to learn from. An exponential decay
   with a half-life in CALENDAR days (not trading days — news ages over a
   weekend) is applied recursively, so each date depends only on dates before it.

3. PUBLICATION TIME, AND AFTER-CLOSE ITEMS BELONG TO THE NEXT SESSION. Getting
   this wrong is leakage, not an off-by-one: an item published at 16:00 after the
   15:00 ICT close could not have informed that session's price. Items published
   DURING or before a session are attributed to it, which is sound because the
   features at t are used to predict t+1.

4. POLARITY ONLY AVERAGES SCORES WE CAN VOUCH FOR. After #112, score_source
   records how each score was obtained. Rows scored by the pre-#112 ternary carry
   score_source NULL and hold the old constants (neutral stored as +0.5), and
   'template' rows were never judged at all. Feeding either to a model would be
   feeding known-bad numbers, so both are excluded from POLARITY while still
   counting toward INTENSITY — an article existed, whatever we know about its
   tone. See docs/backlog108_news_sentiment_validation.md and Backlog #113.

PAST COVARIATES ONLY. These are observations of what has already been published;
there is no sense in which tomorrow's news intensity is known today, so they must
never be offered as future covariates (#104/#105, CLAUDE.md C1).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable, Optional, Sequence

# The VN cash market closes at 15:00 ICT = 08:00 UTC. An item stamped at or after
# this time is attributed to the NEXT calendar date (decision 3 above).
VN_CLOSE_UTC = time(8, 0)

# Default half-life. #106 called for ~3-10 days; 5 keeps a week-old story at
# roughly a quarter of its initial weight, which matches how long a VN company
# story stays in view without making the series a near-constant.
DEFAULT_HALFLIFE_DAYS = 5.0

# score_source values whose magnitude is not trustworthy for polarity.
# None  — scored before #112 by the ternary; neutral was stored as +0.5.
# 'template' — no model answered; the value is a constant, not a judgement.
UNTRUSTED_SCORE_SOURCES = frozenset({None, "", "template"})

# Below this decayed weight the memory is empty rather than "slightly positive",
# so polarity reports exactly 0.0 instead of dividing two vanishing numbers.
_EPS = 1e-9


@dataclass(frozen=True)
class NewsItemPoint:
    """One stored news item, reduced to what the features need."""
    ts_utc: datetime
    sentiment_score: Optional[float] = None
    score_source: Optional[str] = None


@dataclass(frozen=True)
class NewsFeatureRow:
    date: date
    article_count: int      # items attributed to this date, undecayed
    scored_count: int       # of those, how many carried a trustworthy score
    intensity: float        # decayed article count
    polarity: float         # decayed mean trustworthy score, in [-1, 1]


def session_date_for(ts_utc: datetime, *, close_utc: time = VN_CLOSE_UTC) -> date:
    """The session an item can first have informed.

    At or after the close, the next calendar date — the item could not have moved
    the session that had already ended. Naive timestamps are read as UTC, which is
    what the store holds.
    """
    if ts_utc.tzinfo is None:
        ts = ts_utc.replace(tzinfo=timezone.utc)
    else:
        ts = ts_utc.astimezone(timezone.utc)
    d = ts.date()
    return d + timedelta(days=1) if ts.timetz().replace(tzinfo=None) >= close_utc else d


def is_trustworthy_score(score: Optional[float], score_source: Optional[str]) -> bool:
    """Whether a stored score may contribute to POLARITY (decision 4)."""
    if score is None:
        return False
    return score_source not in UNTRUSTED_SCORE_SOURCES


def daily_news_features(
    items: Iterable[NewsItemPoint],
    *,
    start: date,
    end: date,
    halflife_days: float = DEFAULT_HALFLIFE_DAYS,
    close_utc: time = VN_CLOSE_UTC,
    warmup_days: int = 0,
) -> list[NewsFeatureRow]:
    """One row per calendar date in [start, end], oldest first.

    `warmup_days` lets the caller pass items from before `start` so the decayed
    state is already running at the first returned row, instead of starting from
    an artificial zero. Rows before `start` are computed and then dropped.

    Raises ValueError on a non-positive half-life, rather than producing a series
    whose decay factor is undefined.
    """
    if halflife_days <= 0:
        raise ValueError(f"halflife_days must be positive, got {halflife_days!r}")
    if end < start:
        raise ValueError(f"end {end} precedes start {start}")

    decay = 0.5 ** (1.0 / halflife_days)

    first = start - timedelta(days=max(0, int(warmup_days)))
    counts: dict[date, int] = {}
    scored: dict[date, int] = {}
    sums: dict[date, float] = {}
    for it in items:
        d = session_date_for(it.ts_utc, close_utc=close_utc)
        if d < first or d > end:
            continue
        counts[d] = counts.get(d, 0) + 1
        if is_trustworthy_score(it.sentiment_score, it.score_source):
            scored[d] = scored.get(d, 0) + 1
            sums[d] = sums.get(d, 0.0) + float(it.sentiment_score)

    rows: list[NewsFeatureRow] = []
    dec_count = 0.0          # decayed count of all articles -> intensity
    dec_scored = 0.0         # decayed count of trustworthy scores -> polarity denominator
    dec_sum = 0.0            # decayed sum of trustworthy scores -> polarity numerator

    d = first
    while d <= end:
        # Decay yesterday's memory, then add today's arrivals. In this order the
        # value at d depends only on dates <= d, which is what keeps it causal.
        dec_count = dec_count * decay + counts.get(d, 0)
        dec_scored = dec_scored * decay + scored.get(d, 0)
        dec_sum = dec_sum * decay + sums.get(d, 0.0)

        polarity = (dec_sum / dec_scored) if dec_scored > _EPS else 0.0
        if d >= start:
            rows.append(NewsFeatureRow(
                date=d,
                article_count=counts.get(d, 0),
                scored_count=scored.get(d, 0),
                intensity=dec_count,
                polarity=max(-1.0, min(1.0, polarity)),
            ))
        d += timedelta(days=1)

    return rows


def rows_to_payload(rows: Sequence[NewsFeatureRow]) -> list[dict]:
    """JSON-ready rows. Floats are rounded to 6dp: the series is a model input,
    not a measurement, and full binary noise in the wire format helps nobody."""
    return [
        {
            "date": r.date.isoformat(),
            "article_count": r.article_count,
            "scored_count": r.scored_count,
            "intensity": round(r.intensity, 6),
            "polarity": round(r.polarity, 6),
        }
        for r in rows
    ]


def halflife_from_decay(decay: float) -> float:
    """Inverse of the decay factor, for reporting the effective half-life."""
    if not 0 < decay < 1:
        raise ValueError("decay must lie strictly between 0 and 1")
    return -1.0 / math.log2(decay)
