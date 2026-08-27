"""
Rung 5 -- a currency pattern in the visible text. Base confidence 55.

Last resort, and never trusted alone. Its confidence sits far below the alert
threshold on purpose: this rung exists so a seller sees SOMETHING with an
honest "we are not sure we read this correctly" marker, rather than a blank
where a competitor's price should be.

The two filters below are what stop it being actively misleading: struck-out
prices are removed before matching, and a match near the <h1> is preferred over
one further down, because a product page's first price is usually the product's.
"""
import re

from ..money import VND_IN_TEXT, parse_vnd

CONFIDENCE = 55

_STRIP_TAGS = re.compile(r"<(script|style|noscript|template)\b.*?</\1>", re.I | re.S)
# A struck-through price is the OLD price. Reading it as the current one is the
# single most likely way this rung produces a plausible wrong number.
_STRIP_STRIKE = re.compile(
    r"<(del|s|strike)\b.*?</\1>"
    r'|<[^>]+class=["\'][^"\']*(original|old-price|price-old|strike|line-through|'
    r'compare)[^"\']*["\'][^>]*>.*?</[^>]+>',
    re.I | re.S,
)
_TAGS = re.compile(r"<[^>]+>")


def _visible(html):
    cleaned = _STRIP_TAGS.sub(" ", html or "")
    cleaned = _STRIP_STRIKE.sub(" ", cleaned)
    return _TAGS.sub(" ", cleaned)


def extract(html, adapter=None):
    from . import Candidate

    body = html or ""
    heading = body.lower().find("<h1")
    if heading > 0:
        # Prefer the region around the product title over the whole document,
        # which on a real page also contains related products and a footer.
        window = _visible(body[heading:heading + 12_000])
        found = _first(window)
        if found:
            return found

    return _first(_visible(body)) or []


def _first(text_blob):
    from . import Candidate

    for match in VND_IN_TEXT.finditer(text_blob):
        raw = match.group(1) or match.group(2)
        price = parse_vnd(raw)
        if price is not None:
            return [Candidate(
                tier="text", confidence=CONFIDENCE, price=price, currency="VND",
                evidence=f"visible text {match.group(0).strip()[:60]!r}",
            )]
    return None
