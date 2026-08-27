"""
Rung 4 -- CSS selectors from the host's adapter file. Base confidence 90.

The only per-site rung, and it is DATA rather than code: one YAML file per
host, reviewable in a diff, deployable without shipping Python. That is the
whole answer to "every new source means new selectors" -- it is still true, but
a new source costs a config change instead of a release.

Deliberately absent when no adapter exists, rather than guessing at class
names. A guess here produces a confident wrong number.
"""
from ..money import parse_vnd

CONFIDENCE = 90


def _soup(html):
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover - dependency is declared
        return None
    try:
        return BeautifulSoup(html or "", "lxml")
    except Exception:
        try:
            return BeautifulSoup(html or "", "html.parser")
        except Exception:
            return None


def _text_of(soup, selector):
    if not soup or not selector:
        return None
    try:
        node = soup.select_one(selector)
    except Exception:
        return None
    return node.get_text(" ", strip=True) if node else None


def extract(html, adapter=None):
    from . import Candidate

    selector = getattr(adapter, "price_selector", None)
    if not selector:
        return []

    soup = _soup(html)
    raw = _text_of(soup, selector)
    if not raw:
        return []

    price = parse_vnd(raw)
    if price is None:
        return []
    return [Candidate(
        tier="selectors", confidence=CONFIDENCE, price=price,
        currency=getattr(adapter, "currency", None),
        evidence=f"{selector} -> {raw[:80]}",
    )]


def title(html, adapter=None):
    selector = getattr(adapter, "title_selector", None)
    if not selector:
        return None
    value = _text_of(_soup(html), selector)
    return value[:480] if value else None


def availability(html, adapter=None):
    selector = getattr(adapter, "unavailable_selector", None)
    if not selector:
        return None
    return "out_of_stock" if _text_of(_soup(html), selector) else None
