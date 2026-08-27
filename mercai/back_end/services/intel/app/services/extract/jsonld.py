"""
Rung 1 -- schema.org/Product in a JSON-LD block. Base confidence 95.

The highest-yield rung by a wide margin, and it runs first for that reason.
Shopify, WooCommerce, Haravan, Sapo and most Next/Nuxt storefronts emit it by
default, because Google Shopping requires it. Measured 2026-08-27: it fired on
36 of 36 real Vietnamese product pages.
"""
import json
import re

from ..money import parse_vnd

CONFIDENCE = 95
MAX_DEPTH = 8

_BLOCK = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)


def _blocks(html):
    for raw in _BLOCK.findall(html or ""):
        try:
            yield json.loads(raw.strip())
        except Exception:
            continue


def _walk(node, depth=0):
    if depth > MAX_DEPTH:
        return
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk(value, depth + 1)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value, depth + 1)


def _products(html):
    for block in _blocks(html):
        for node in _walk(block):
            if not isinstance(node, dict):
                continue
            declared = node.get("@type")
            types = declared if isinstance(declared, list) else [declared]
            if any(str(t).lower() == "product" for t in types if t):
                yield node


def extract(html, adapter=None):
    from . import Candidate

    out = []
    for product in _products(html):
        offers = product.get("offers")
        for offer in (offers if isinstance(offers, list) else [offers]):
            if not isinstance(offer, dict):
                continue
            # `lowPrice` covers AggregateOffer, which means a variant range.
            # The minimum is what a buyer sees first and what a competitor is
            # effectively advertising.
            for key in ("price", "lowPrice"):
                value = offer.get(key)
                if value is None:
                    continue
                price = parse_vnd(value)
                if price is not None:
                    out.append(Candidate(
                        tier="jsonld",
                        confidence=CONFIDENCE,
                        price=price,
                        currency=offer.get("priceCurrency"),
                        evidence=f"offers.{key}={value}",
                    ))
                    break
    return out


def price_range(html):
    """(min, max) when the markup describes a variant range, else (None, None)."""
    for product in _products(html):
        offers = product.get("offers")
        for offer in (offers if isinstance(offers, list) else [offers]):
            if isinstance(offer, dict) and offer.get("lowPrice") is not None:
                return parse_vnd(offer.get("lowPrice")), parse_vnd(offer.get("highPrice"))
    return None, None


def title(html):
    for product in _products(html):
        name = product.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()[:480]
    return None


def availability(html):
    for product in _products(html):
        offers = product.get("offers")
        for offer in (offers if isinstance(offers, list) else [offers]):
            if not isinstance(offer, dict):
                continue
            raw = str(offer.get("availability") or "").lower()
            if "outofstock" in raw or "soldout" in raw:
                return "out_of_stock"
            if "instock" in raw:
                return "in_stock"
    return None
