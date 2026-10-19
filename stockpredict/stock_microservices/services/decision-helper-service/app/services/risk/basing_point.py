"""EM-3 — the basing-point stop engine (E&M Ch 28, Bassetti Ch 28.1).

Bassetti on Ch 28: *"In a book composed of nothing but important chapters this
Chapter 28 might not get the emphasis it deserves… the procedure outlined here
is of absolutely basic importance in analyzing and trading trends."*

The four rules, as he numbers them:

1. A high is made, recognised by no higher prices for the moment.
2. Prices recede and a low is made; watch each later day whose range lies
   **completely outside** the candidate low day's range.
3. When **three such days** are observed before a new low is made, the
   candidate becomes a **basing point** — raise the stop to ``filter_pct``
   under the low of that day.
4. When a new high exceeds the previous high by ``new_high_pct``, a new basing
   point is set at **the low of that new-high day**.

Stops are **never** lowered, even when a later low undercuts an old one.

Why this is not the SWING stop we already ship
----------------------------------------------
`stop_module`'s SWING stop sits at the nearest confirmed pivot, which is
*precisely* the obvious prior low E&M warn about. Bassetti quotes Bruce
Kovner, asked where he puts his stops: *"Where they're hard to get to."* And:
*"locals and hedge funds and those who profit from volatility know that the
previous low is where investors and traders set their stops… if they see an
opportunity to take out an important low they will do it."*

The basing point differs in two ways that matter. It will not trust a low
until **three full days have cleared it**, and it then sits a **filter**
below. Both exist to put the stop somewhere that is not the first place a
probe would look.

Causality
---------
The tracker is fed **one bar at a time** and keeps no reference to the series,
so it cannot read a future bar even by accident. A test asserts that
`update()` contains no indexing, slicing or shifting.
"""
from __future__ import annotations

from typing import Optional

#: Days that must lie completely outside the candidate's range. The book's
#: number (Ch 28: "three full days").
DAYS_AWAY = 3

#: How far below the basing point the stop sits. The book uses 6%; Bassetti
#: writes it as "6% (or x%)", so it is a parameter rather than a constant.
DEFAULT_FILTER_PCT = 6.0

#: Rule 4's threshold: a new high this far beyond the previous high sets a new
#: basing point at that day's low (Ch 28.1).
DEFAULT_NEW_HIGH_PCT = 3.0


class BasingPointTracker:
    """Carries one position's basing point and the stop it implies.

    Call `update()` once per bar, oldest to newest, and read `stop`. The
    return value is the current stop or ``None`` while no basing point has
    been confirmed yet — in which case the caller should keep whatever initial
    stop it set at entry, because E&M's procedure says nothing about the bars
    before the first basing point forms.

    ``use_new_high_rule`` gates rule 4. It is **off** by default, which is
    E&M's own caveat rather than timidity: advancing the stop on new highs as
    well can force a premature exit on a mid-trend blow-off, and Bassetti
    teaches a "simplified teaching version" using only wave lows, leaving the
    full procedure to advanced traders. `EM-3`'s register entry carried the
    caveat forward and asked for the two to be measured separately.
    """

    def __init__(
        self,
        direction: str,
        filter_pct: float = DEFAULT_FILTER_PCT,
        new_high_pct: float = DEFAULT_NEW_HIGH_PCT,
        use_new_high_rule: bool = False,
        days_away: int = DAYS_AWAY,
    ) -> None:
        self.direction = direction
        self.filter_pct = filter_pct
        self.new_high_pct = new_high_pct
        self.use_new_high_rule = use_new_high_rule
        self.days_away = days_away

        self.basing_point: Optional[float] = None
        self.stop: Optional[float] = None

        # Rule 2's state: the candidate extreme and how many days have cleared
        # it so far.
        self.candidate_low: Optional[float] = None
        self.candidate_high: Optional[float] = None
        self._candidate_range: Optional[tuple] = None
        self._days_clear = 0

        # Rule 1 / rule 4's state: the running extreme in the trade's
        # direction, against which a "new high" is judged.
        self._best_high: Optional[float] = None
        self._best_low: Optional[float] = None

    # -- internals ---------------------------------------------------------

    def _long(self) -> bool:
        return self.direction == "LONG"

    def _short(self) -> bool:
        return self.direction == "SHORT"

    def _stop_from(self, basing_point: float) -> float:
        factor = self.filter_pct / 100.0
        if self._long():
            return round(basing_point * (1.0 - factor), 4)
        return round(basing_point * (1.0 + factor), 4)

    def _offer(self, basing_point: float) -> None:
        """Accept a basing point only if its stop is an improvement.

        The inviolable rule: never lowered for a long, never raised for a
        short. A deeper low therefore does not loosen the stop — the filter is
        what carries the position through the probe.
        """
        candidate_stop = self._stop_from(basing_point)
        if self.stop is None:
            self.basing_point, self.stop = basing_point, candidate_stop
            return
        if self._long() and candidate_stop > self.stop:
            self.basing_point, self.stop = basing_point, candidate_stop
        elif self._short() and candidate_stop < self.stop:
            self.basing_point, self.stop = basing_point, candidate_stop

    # -- the public step ---------------------------------------------------

    def update(self, high: float, low: float, close: float) -> Optional[float]:
        """Advance by one bar and return the current stop, if any."""
        if not (self._long() or self._short()):
            return self.stop

        # ---- rule 4: a new high (or new low, short) beyond the threshold --
        if self._long():
            if self.use_new_high_rule and self._best_high is not None:
                if high > self._best_high * (1.0 + self.new_high_pct / 100.0):
                    self._offer(low)
            self._best_high = high if self._best_high is None else max(self._best_high, high)
        else:
            if self.use_new_high_rule and self._best_low is not None:
                if low < self._best_low * (1.0 - self.new_high_pct / 100.0):
                    self._offer(high)
            self._best_low = low if self._best_low is None else min(self._best_low, low)

        # ---- rules 2 and 3: the candidate, and three days completely clear -
        extreme = low if self._long() else high

        fresh = (
            self.candidate_low is None if self._long() else self.candidate_high is None
        ) or (
            (self._long() and extreme < (self.candidate_low or extreme + 1))
            or (self._short() and extreme > (self.candidate_high or extreme - 1))
        )

        if fresh:
            # A new extreme replaces the candidate and the count starts again:
            # Ch 28's "before a new low is made".
            if self._long():
                self.candidate_low = low
            else:
                self.candidate_high = high
            self._candidate_range = (low, high)
            self._days_clear = 0
            return self.stop

        if self._candidate_range is None:
            return self.stop

        c_low, c_high = self._candidate_range
        # "the entire price range for three full days must lie entirely above
        # the high of the low day" — the strict reading, so a day that merely
        # closes higher while still overlapping does not count.
        clear = low > c_high if self._long() else high < c_low

        if clear:
            self._days_clear += 1
            if self._days_clear >= self.days_away:
                confirmed = c_low if self._long() else c_high
                self._offer(confirmed)
                # The cycle repeats. E&M's procedure is: a high is made,
                # prices recede to a low, three days clear it, the stop is
                # raised — and then you wait for the NEXT reaction low and do
                # it again. Holding the same candidate forever would pin the
                # stop to the first basing point of the trade, so a confirmed
                # candidate is retired here and the next bar starts a new one.
                self.candidate_low = None
                self.candidate_high = None
                self._candidate_range = None
                self._days_clear = 0
        else:
            # Not a new extreme, but not clear either: the run of clear days
            # is broken and has to be rebuilt.
            self._days_clear = 0

        return self.stop
