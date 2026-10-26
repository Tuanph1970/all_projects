"""ingest/ operator corrections to a parsed TCBS mail (Backlog #55).

The preview screen used to offer one remedy for a misparsed call: untick it. That loses
the call entirely — the mail stores a recommendation the watchlist never sees — so a
wrong ticker was effectively a dropped call. This applies the operator's corrections to
the parse result on the way to storage.

Three rules it exists to enforce:

1. **Raw is untouched (EC-B2).** A correction never edits `raw_content`; it edits the
   *interpretation*. The archive stays byte-identical, so a parser fix is still
   replayable over it.

2. **Every correction is recorded (EC-B2 again, from the other side).** Because
   extraction is a re-runnable pass, a reparse re-derives whatever the parser reads
   today and would silently revert a human's fix. Each overridden field is therefore
   named on the stored row, so a later pass can leave it alone and a reader can see
   that a person intervened.

3. **A correction that does not match its target is refused, loudly (EC-B10).** The
   payload carries both the row's index and the symbol the operator was looking at. If
   those disagree with the parse, the whole save is rejected rather than applying an
   edit to the wrong call — a half-corrected session is worse than an uncorrected one.

`label_verbatim` is not correctable by design: EC-B4 keeps exactly what TCBS wrote, and
a correction changes our normalisation, never the source phrase. The verbatim label is
what makes a correction auditable afterwards.
"""
from __future__ import annotations

import logging
import re
from dataclasses import replace
from typing import Iterable, Optional

from app.ingest.tcb_mail_parser import ACTIONS, ParsedMail

logger = logging.getLogger(__name__)

# The fields an operator may override. Deliberately narrow: these are the three that
# decide what reaches the watchlist and what the scorer measures.
CORRECTABLE = ("symbol", "action", "target_price")

# VN tickers are 3 letters; derivative/fund codes run longer, so this is a shape check
# rather than a whitelist — the point is to refuse free text, not to police listings.
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{3,12}$")


class CorrectionError(ValueError):
    """A correction that cannot be applied safely. The caller turns this into a 422."""


def apply_corrections(parsed: ParsedMail, corrections: Optional[Iterable]) -> ParsedMail:
    """Return a copy of `parsed` with the operator's corrections applied.

    `corrections` are objects carrying `index`, `from_symbol`, and any of
    `symbol` / `action` / `target_price`. A field left None means "leave it alone",
    which is what lets the UI send only what actually changed.
    """
    if not corrections:
        return parsed

    recos = list(parsed.recos)
    seen: set[int] = set()

    for c in corrections:
        index = c.index
        if index in seen:
            # Two edits to one row cannot both be "the" correction, and silently taking
            # the last would make the result depend on payload order.
            raise CorrectionError(f"two corrections target recommendation {index}")
        seen.add(index)
        if not 0 <= index < len(recos):
            raise CorrectionError(
                f"correction targets recommendation {index}, but the mail parsed "
                f"{len(recos)}")

        target = recos[index]
        # The guard that makes an index safe to trust. The preview and the save parse
        # the same text with a different reference date, so re-deriving the list is not
        # guaranteed to produce the same order; if it ever does not, this refuses rather
        # than moving a ticker onto someone else's call.
        if (c.from_symbol or "").strip().upper() != (target.symbol or "").upper():
            raise CorrectionError(
                f"correction for {c.from_symbol!r} does not match recommendation "
                f"{index}, which parsed as {target.symbol!r} — the mail may have been "
                f"edited since the preview; parse it again")

        changes: dict = {}
        if c.symbol is not None:
            symbol = c.symbol.strip().upper()
            if not _SYMBOL_RE.match(symbol):
                raise CorrectionError(f"{c.symbol!r} is not a usable ticker")
            if symbol != target.symbol.upper():
                changes["symbol"] = symbol
        if c.action is not None:
            action = c.action.strip().upper() or None
            if action is not None and action not in ACTIONS:
                raise CorrectionError(
                    f"{c.action!r} is not a recognised action; expected one of "
                    f"{', '.join(ACTIONS)} (or empty to leave it unknown)")
            if action != target.action:
                changes["action"] = action
        if c.target_price is not None:
            price = float(c.target_price)
            if price <= 0:
                raise CorrectionError("a target price must be positive")
            if price != target.target_price:
                changes["target_price"] = price

        if not changes:
            # Echoing a value back unchanged is not an error — the UI sends whatever is
            # in its inputs — but it must not be recorded as a human correction, or the
            # audit trail stops meaning anything.
            continue

        recos[index] = replace(
            target,
            **changes,
            corrected_fields=tuple(sorted(set(target.corrected_fields) | set(changes))),
        )
        logger.info("operator corrected recommendation %s (%s): %s",
                    index, target.symbol, ", ".join(sorted(changes)))

    return replace(parsed, recos=recos)
