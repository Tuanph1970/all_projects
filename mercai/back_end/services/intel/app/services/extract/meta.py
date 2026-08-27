"""
Rung 2 -- Open Graph and microdata meta tags. Base confidence 90.

Nearly free once the document is in hand, and it catches an older generation of
templates that predate JSON-LD. Its real value is as a second opinion: when it
agrees with rung 1 the reconciler promotes confidence to 99.
"""
import re

from ..money import parse_vnd

CONFIDENCE = 90

_PATTERNS = [
    (r'<meta[^>]+property=["\']product:price:amount["\'][^>]+content=["\']([^"\']+)',
     "product:price:amount"),
    (r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']product:price:amount["\']',
     "product:price:amount"),
    (r'<meta[^>]+property=["\']og:price:amount["\'][^>]+content=["\']([^"\']+)',
     "og:price:amount"),
    (r'<meta[^>]+itemprop=["\']price["\'][^>]+content=["\']([^"\']+)', "itemprop=price"),
    (r'itemprop=["\']price["\'][^>]+content=["\']([^"\']+)', "itemprop=price"),
]

_CURRENCY = re.compile(
    r'(?:product|og):price:currency["\'][^>]+content=["\']([A-Z]{3})', re.I
)
_TITLE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', re.I
)


def extract(html, adapter=None):
    from . import Candidate

    currency_match = _CURRENCY.search(html or "")
    currency = currency_match.group(1).upper() if currency_match else None

    for pattern, label in _PATTERNS:
        match = re.search(pattern, html or "", re.I)
        if not match:
            continue
        price = parse_vnd(match.group(1))
        if price is not None:
            return [Candidate(
                tier="meta", confidence=CONFIDENCE, price=price,
                currency=currency, evidence=f"{label}={match.group(1)}",
            )]
    return []


def title(html):
    match = _TITLE.search(html or "")
    return match.group(1).strip()[:480] if match else None
