"""
Rung 3 -- prices embedded in a framework's hydration state. Base confidence 75,
or 90 when an adapter supplies the key path.

THIS RUNG IS WHERE A SILENT WRONG PRICE IS MOST LIKELY, and its design is
shaped entirely around that. A blind walk for keys named "price" will happily
return `originalPrice`, a shipping fee, or a variant that is out of stock --
each of which is a well-formed, in-range, entirely plausible number.

Two rules contain it:
  * an explicit denylist of keys that look like prices and are not the price;
  * an unconfigured walk never scores above 75, which is BELOW the alert
    threshold. It can be shown to a seller with its evidence visible. It cannot
    make the system tell them they are being undercut.
"""
import json
import re

from ..money import parse_vnd

CONFIDENCE_BLIND = 75
CONFIDENCE_CONFIGURED = 90
MAX_DEPTH = 7
MAX_CANDIDATES = 3

_BLOCKS = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
    r'|window\.__NUXT__\s*=\s*(\{.*?\})\s*;'
    r'|window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;',
    re.I | re.S,
)

# Keys that look like a price and are not the one we want.
DENY = re.compile(
    r"original|list|msrp|compare_at|compareat|strike|before|was_|"
    r"shipping|freight|fee|tax|vat|discount|saving|deposit|installment",
    re.I,
)
PRICE_KEY = re.compile(
    r"^(final_|sale_|current_|selling_|special_)?price(_min|_max|min|max)?$", re.I
)


def _payloads(html):
    for groups in _BLOCKS.findall(html or ""):
        blob = next((g for g in groups if g), None)
        if not blob:
            continue
        try:
            yield json.loads(blob.strip())
        except Exception:
            continue


def _walk(node, prefix="", depth=0):
    if depth > MAX_DEPTH:
        return
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, (dict, list)):
                yield from _walk(value, path, depth + 1)
            elif isinstance(value, (int, float, str)):
                yield path, value
    elif isinstance(node, list):
        for index, value in enumerate(node[:20]):
            yield from _walk(value, f"{prefix}[{index}]", depth + 1)


def _at_path(payload, dotted):
    node = payload
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node if isinstance(node, (int, float, str)) else None


def extract(html, adapter=None):
    from . import Candidate

    out = []
    configured = list(getattr(adapter, "state_paths", None) or [])

    for payload in _payloads(html):
        # A configured key path is precise -- it was written by someone who
        # looked at this site's markup, so it outranks the blind walk.
        for dotted in configured:
            value = _at_path(payload, dotted)
            price = parse_vnd(value) if value is not None else None
            if price is not None:
                out.append(Candidate(
                    tier="state", confidence=CONFIDENCE_CONFIGURED, price=price,
                    currency=None, evidence=f"{dotted}={value}",
                ))
        if out:
            continue

        for path, value in _walk(payload):
            leaf = path.rsplit(".", 1)[-1].split("[")[0]
            if DENY.search(path) or not PRICE_KEY.match(leaf):
                continue
            price = parse_vnd(value)
            if price is not None:
                out.append(Candidate(
                    tier="state", confidence=CONFIDENCE_BLIND, price=price,
                    currency=None, evidence=f"{path}={value}",
                ))
            if len(out) >= MAX_CANDIDATES:
                break
    return out[:MAX_CANDIDATES]
