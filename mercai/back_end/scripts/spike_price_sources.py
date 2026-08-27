#!/usr/bin/env python3
"""
Spike: can we reach Vietnamese marketplaces, and does the extraction ladder work?

Two questions, one script. Both are empirical and neither should be answered by
argument:

  Q1  Which sources will actually serve us product data from THIS network?
      The crossmarket_price_analyzer checkpoint (2026-04-28) recorded Tiki
      working, and both Shopee and Lazada refusing -- Shopee with
      `error 90309999`, Lazada with an SPA shell and no product grid. It also
      recorded the hypothesis that was never tested: that the refusals were
      this network's egress IP, not the scrapers. Run this from a different
      network and that hypothesis is settled either way.

  Q2  Does the extraction ladder in docs/ai-features/05-price-intelligence.md
      read real Vietnamese product pages? Pass URLs with --urls to find out.
      This is the phase-1.5 validation gate.

Usage:
    python3 spike_price_sources.py                      # source probes only
    python3 spike_price_sources.py --urls urls.txt      # + ladder on real pages
    python3 spike_price_sources.py --keyword "bat gom"  # probe a real VN term
    python3 spike_price_sources.py --json out.json      # machine-readable too

No dependencies required. Uses httpx when importable, stdlib urllib otherwise.

WHAT THIS SCRIPT CAN AND CANNOT CONCLUDE
    It sends plain HTTP requests. It does NOT drive a browser.
      - A source that WORKS here works with the cheap fetcher, which is the
        best possible outcome: no Playwright, no +400MB Chromium layer.
      - A source that FAILS here has NOT been proven unreachable. It has been
        proven unreachable cheaply. Playwright may still get through -- though
        for Shopee and Lazada the reference project already tried that and was
        refused, so a failure here mostly confirms what is known.
"""

import argparse
import json
import re
import socket
import sys
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlparse

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 20
MAX_BYTES = 3_000_000


# --------------------------------------------------------------------------
# fetch
# --------------------------------------------------------------------------

try:
    import httpx

    def _get(url, headers):
        with httpx.Client(follow_redirects=True, timeout=TIMEOUT) as c:
            r = c.get(url, headers=headers)
            return r.status_code, r.text[:MAX_BYTES], str(r.url)
except ImportError:
    import urllib.request
    import urllib.error

    def _get(url, headers):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read(MAX_BYTES)
                charset = r.headers.get_content_charset() or "utf-8"
                return r.status, raw.decode(charset, "replace"), r.geturl()
        except urllib.error.HTTPError as e:
            raw = e.read(MAX_BYTES)
            return e.code, raw.decode("utf-8", "replace"), url


def fetch(url, extra_headers=None):
    """Returns (status, body, final_url, elapsed_ms, error)."""
    headers = {
        "User-Agent": UA,
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }
    if extra_headers:
        headers.update(extra_headers)
    started = time.monotonic()
    try:
        status, body, final = _get(url, headers)
        return status, body, final, int((time.monotonic() - started) * 1000), None
    except Exception as exc:  # noqa: BLE001 - a spike reports every failure shape
        return None, "", url, int((time.monotonic() - started) * 1000), repr(exc)


def dns_check(url):
    """
    Distinguish "they refused us" from "we never left the building".

    Corporate DNS, pi-hole style filters and container sandboxes commonly
    blackhole a host to 0.0.0.0 or 127.0.0.1, which surfaces as an instant
    ECONNREFUSED. Reporting that as a marketplace block would be exactly the
    wrong conclusion -- it is the difference between "buy residential proxies"
    and "run this from your laptop instead".
    """
    host = urlparse(url).netloc.split(":")[0]
    try:
        ip = socket.gethostbyname(host)
    except OSError as exc:
        return "dns_fail", host, repr(exc)
    if ip.startswith(("0.", "127.")) or ip == "::1":
        return "blackholed", host, ip
    return "ok", host, ip


# --------------------------------------------------------------------------
# Vietnamese price parsing  (docs/ai-features/05-price-intelligence.md section 5)
# --------------------------------------------------------------------------

MIN_VND, MAX_VND = 1_000, 1_000_000_000

_SHORTHAND = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(k|nghin|nghìn|tr|trieu|triệu)\b", re.IGNORECASE
)
# `\b` after `₫` never matches -- `₫` is not a word character, so there is no
# boundary between it and the space that follows. A negative lookahead is what
# this actually needs. Longest currency alternative first, so "185.000 đồng"
# consumes "đồng" rather than matching "đ" and then failing the lookahead.
_CUR = r"(?:₫|VNĐ|VND|đồng|đ)"
_VND_TEXT = re.compile(
    r"(?:₫|VNĐ|VND)\s*([\d.,]{4,})"
    r"|([\d.,]{4,})\s*" + _CUR + r"(?![\w])",
    re.IGNORECASE,
)


def parse_vnd(text):
    """
    Vietnamese price string -> int VND, or None.

    The trap this exists for: float("1.250.000") raises, and float("1.250")
    returns 1.25 -- an error of one thousand times that still looks like a
    plausible price. Separators are resolved by position, never by locale guess.
    """
    if text is None:
        return None
    s = str(text).strip()

    m = _SHORTHAND.search(s)
    if m:
        try:
            base = Decimal(m.group(1).replace(",", "."))
        except InvalidOperation:
            return None
        mult = 1_000 if m.group(2).lower().startswith(("k", "ngh")) else 1_000_000
        return _band(int(base * mult))

    digits = re.sub(r"[^\d.,]", "", s)
    if not digits:
        return None

    has_dot, has_comma = "." in digits, "," in digits
    if has_dot and has_comma:
        # The LAST separator is the decimal point; the other groups thousands.
        dec = "." if digits.rfind(".") > digits.rfind(",") else ","
        grp = "," if dec == "." else "."
        digits = digits.replace(grp, "").replace(dec, ".")
    elif has_dot or has_comma:
        sep = "." if has_dot else ","
        parts = digits.split(sep)
        # Groups of exactly three after the first -> it is a thousands separator.
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            digits = "".join(parts)
        else:
            digits = digits.replace(sep, ".")

    try:
        value = Decimal(digits)
    except InvalidOperation:
        return None

    # VND carries no minor units in practice; a fraction means we misparsed.
    if value != value.to_integral_value():
        return None
    return _band(int(value))


def _band(v):
    return v if MIN_VND <= v <= MAX_VND else None


# --------------------------------------------------------------------------
# The extraction ladder
# --------------------------------------------------------------------------

BAD_KEY = re.compile(
    r"original|list|msrp|compare_at|strike|before|shipping|fee|tax|discount", re.I
)
PRICE_KEY = re.compile(
    r"^(final_|sale_|current_|selling_)?price(_min|_max|Min|Max)?$|^price$", re.I
)
_LD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_STATE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>'
    r'|window\.__NUXT__\s*=\s*(\{.*?\});'
    r'|window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
    re.I | re.S,
)
_META = [
    (r'<meta[^>]+property=["\']product:price:amount["\'][^>]+content=["\']([^"\']+)', "product:price:amount"),
    (r'<meta[^>]+property=["\']og:price:amount["\'][^>]+content=["\']([^"\']+)', "og:price:amount"),
    (r'<meta[^>]+itemprop=["\']price["\'][^>]+content=["\']([^"\']+)', "itemprop=price"),
    (r'itemprop=["\']price["\'][^>]+content=["\']([^"\']+)', "itemprop=price(attr)"),
]


def _snippet(body, needle, width=70):
    i = body.find(str(needle))
    if i < 0:
        return None
    return re.sub(r"\s+", " ", body[max(0, i - width) : i + width]).strip()


def tier_jsonld(body):
    out = []
    for block in _LD.findall(body):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        for node in _walk_nodes(data):
            if not isinstance(node, dict):
                continue
            t = node.get("@type")
            types = t if isinstance(t, list) else [t]
            if not any(str(x).lower() == "product" for x in types if x):
                continue
            offers = node.get("offers")
            for off in offers if isinstance(offers, list) else [offers]:
                if not isinstance(off, dict):
                    continue
                for key in ("price", "lowPrice"):
                    if off.get(key) is not None:
                        v = parse_vnd(off[key])
                        if v:
                            out.append(("jsonld", 95, v, off.get("priceCurrency"),
                                        f"offers.{key}={off[key]}"))
                            break
    return out


def _walk_nodes(o, depth=0):
    if depth > 8:
        return
    yield o
    if isinstance(o, dict):
        for v in o.values():
            yield from _walk_nodes(v, depth + 1)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_nodes(v, depth + 1)


def tier_meta(body):
    for pattern, label in _META:
        m = re.search(pattern, body, re.I)
        if m:
            v = parse_vnd(m.group(1))
            if v:
                return [("meta", 90, v, None, f"{label}={m.group(1)}")]
    return []


def tier_state(body):
    out = []
    for groups in _STATE.findall(body):
        blob = next((g for g in groups if g), None)
        if not blob:
            continue
        try:
            data = json.loads(blob.strip())
        except Exception:
            continue
        for path, val in _walk_kv(data):
            leaf = path.rsplit(".", 1)[-1]
            if BAD_KEY.search(path) or not PRICE_KEY.match(leaf):
                continue
            v = parse_vnd(val)
            if v:
                out.append(("state", 75, v, None, f"{path}={val}"))
    return out[:3]


def _walk_kv(o, prefix="", depth=0):
    if depth > 7:
        return
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                yield from _walk_kv(v, p, depth + 1)
            elif isinstance(v, (int, float, str)):
                yield p, v
    elif isinstance(o, list):
        for i, v in enumerate(o[:20]):
            yield from _walk_kv(v, f"{prefix}[{i}]", depth + 1)


def tier_text(body):
    # Strip the machinery so we only see what a person would see.
    visible = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", body, flags=re.I | re.S)
    visible = re.sub(r"<(del|s)\b.*?</\1>", " ", visible, flags=re.I | re.S)
    visible = re.sub(r"<[^>]+>", " ", visible)
    for m in _VND_TEXT.finditer(visible):
        raw = m.group(1) or m.group(2)
        v = parse_vnd(raw)
        if v:
            return [("text", 55, v, "VND", f"visible '{m.group(0).strip()[:40]}'")]
    return []


def run_ladder(body):
    """All tiers run, then reconcile (design doc section 4.6)."""
    cands = tier_jsonld(body) + tier_meta(body) + tier_state(body) + tier_text(body)
    if not cands:
        return None
    cands.sort(key=lambda c: -c[1])
    top = cands[0]
    tier, conf, price, cur, ev = top
    flag = ""
    if len(cands) > 1:
        second = cands[1]
        delta = abs(price - second[2]) / max(price, 1)
        if delta <= 0.005:
            conf = 99
            flag = f"agrees with {second[0]}"
        else:
            conf = max(conf - 25, 0)
            flag = f"CONFLICT {second[0]}={second[2]:,}"
    return {
        "tier": tier, "confidence": conf, "price_vnd": price,
        "currency": cur or "VND", "evidence": ev, "flag": flag,
        "tiers_matched": sorted({c[0] for c in cands}),
    }


def detect_js_required(body, result):
    if result:
        return False
    if len(body) < 200_000 and re.search(
        r'<div id=["\'](root|app|__next)["\']\s*>\s*</div>|__NEXT_DATA__|window\.__NUXT__',
        body, re.I,
    ):
        return True
    return len(body) < 30_000


# --------------------------------------------------------------------------
# Model tokens — the matcher that only some categories permit
# --------------------------------------------------------------------------
#
# Measured 2026-08-27 on real Tiki audio titles: three of four amplifiers matched
# exactly across differently-worded listings with no scoring at all, and zero of
# three ceramics titles produced a token.
#
# That asymmetry is the point. "Nobsound MS-10D MKIII" and "Ampli đèn Nobsound
# MS-10D MKIII chính hãng" share a globally unique identifier; two Bát Tràng
# bowls share only the words every Bát Tràng bowl uses. Electronics get exact
# matching for free; artisan goods need the seller to declare the pairing.

_CAND = re.compile(r"[A-Za-z0-9]+(?:[-–.][A-Za-z0-9]+)*")
_UNIT = re.compile(
    r"^\d+(?:\.\d+)?(cm|mm|m|w|kg|g|ml|l|gb|tb|inch|k|hz|khz|v|a)$", re.I
)
_NOISE = ("BT", "USB", "HDMI", "WIFI", "MP3", "MP4", "TYPE-C", "AUX", "RCA", "IPX")


def model_tokens(title):
    """
    Alphanumeric model identifiers in a product title.

    Deliberately strict -- >=2 letters AND >=2 digits. A token this shape is
    almost never a coincidence, which is what lets a match on it skip scoring
    entirely. Missing a model is cheap (fall back to a declared pairing);
    inventing one is not.

    Known misses, both real: names without digits ("JBL Grip JBLGRIP") and
    models spaced apart from their series ("Redmi Buds 8 Active").
    """
    out = set()
    for mm in _CAND.finditer(title or ""):
        t = mm.group(0).replace("–", "-").upper().strip(".-")
        if len(t) < 4 or _UNIT.match(t):
            continue
        if sum(c.isalpha() for c in t) < 2 or sum(c.isdigit() for c in t) < 2:
            continue
        if t.startswith(_NOISE):
            continue
        out.add(t)
    return out


# --------------------------------------------------------------------------
# Q1 — source probes
# --------------------------------------------------------------------------

def probe_tiki(keyword):
    """Undocumented REST API, no auth. Confirmed working in the reference project."""
    url = (f"https://tiki.vn/api/v2/products?q={quote(keyword)}"
           f"&limit=20&sort=top_seller")
    dns = dns_check(url)
    status, body, _, ms, err = fetch(url, {"Accept": "application/json"})
    r = {"source": "tiki.vn", "method": "plain HTTP JSON API", "status": status,
         "ms": ms, "error": err, "items": 0, "sample": None, "dns": dns}
    if dns[0] != "ok":
        r["verdict"], r["error"] = "LOCAL", _dns_msg(dns)
        return r
    if err or status != 200:
        r["verdict"] = "FAIL"
        return r
    try:
        data = json.loads(body).get("data") or []
    except Exception:
        r["verdict"] = "FAIL"
        r["error"] = "response was not JSON"
        return r
    rows = [d for d in data if d.get("price")]
    r["items"] = len(rows)
    if rows:
        r["sample"] = f"{rows[0].get('name','?')[:52]} @ {int(rows[0]['price']):,}₫"
    r["verdict"] = "OK" if rows else "EMPTY"
    return r


def probe_shopee(keyword):
    """
    /api/v4/search/search_items. Prices come back in micro-VND (raw / 100000).

    The reference project got `error 90309999` here even through Playwright with
    stealth patches -- detection is server-side (TLS fingerprint / IP reputation),
    so a plain request failing is expected and confirms rather than discovers.
    """
    url = (f"https://shopee.vn/api/v4/search/search_items?by=relevancy"
           f"&keyword={quote(keyword)}&limit=20&newest=0&order=desc"
           f"&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2")
    dns = dns_check(url)
    status, body, _, ms, err = fetch(url, {
        "Accept": "application/json",
        "Referer": f"https://shopee.vn/search?keyword={quote(keyword)}",
        "X-Requested-With": "XMLHttpRequest",
        "X-API-SOURCE": "pc",
    })
    r = {"source": "shopee.vn", "method": "plain HTTP internal API", "status": status,
         "ms": ms, "error": err, "items": 0, "sample": None, "dns": dns}
    if dns[0] != "ok":
        r["verdict"], r["error"] = "LOCAL", _dns_msg(dns)
        return r
    if err or status is None:
        r["verdict"] = "FAIL"
        return r
    if "90309999" in body:
        r["verdict"] = "BLOCKED"
        r["error"] = "anti-bot rejection (error 90309999) — matches the 2026-04-28 finding"
        return r
    if status != 200:
        r["verdict"] = "BLOCKED" if status in (403, 429) else "FAIL"
        r["error"] = r["error"] or f"HTTP {status}"
        return r
    try:
        items = json.loads(body).get("items") or []
    except Exception:
        r["verdict"] = "BLOCKED"
        r["error"] = "response was not JSON (likely a challenge page)"
        return r
    rows = [i.get("item_basic", {}) for i in items]
    rows = [b for b in rows if b.get("price")]
    r["items"] = len(rows)
    if rows:
        vnd = int(rows[0]["price"]) // 100_000       # micro-VND -> VND
        r["sample"] = f"{rows[0].get('name','?')[:52]} @ {vnd:,}₫"
    r["verdict"] = "OK" if rows else "EMPTY"
    return r


def probe_lazada(keyword):
    """
    Catalog search page. SPA -- the reference project found the initial HTML is an
    app shell with an empty JSON-LD block, product cards rendered client-side.
    If a grid marker shows up in raw HTML here, that is genuinely new information.
    """
    url = f"https://www.lazada.vn/catalog/?q={quote(keyword)}"
    dns = dns_check(url)
    status, body, final, ms, err = fetch(url)
    r = {"source": "lazada.vn", "method": "plain HTTP HTML", "status": status,
         "ms": ms, "error": err, "items": 0, "sample": None, "dns": dns}
    if dns[0] != "ok":
        r["verdict"], r["error"] = "LOCAL", _dns_msg(dns)
        return r
    if err or status != 200:
        r["verdict"] = "FAIL"
        return r
    if any(x in final.lower() for x in ("captcha", "punish", "_____tmd_____")):
        r["verdict"] = "BLOCKED"
        r["error"] = f"redirected to a challenge: {final[:80]}"
        return r
    markers = [m for m in ("data-qa-locator=\"product-item\"", "Bm3ON",
                           "data-tracking=\"product-card\"") if m in body]
    ladder = run_ladder(body)
    if markers:
        r["items"] = body.count(markers[0])
        r["sample"] = f"grid marker '{markers[0]}' present"
        r["verdict"] = "OK"
    elif ladder:
        r["sample"] = f"no grid, but ladder found {ladder['price_vnd']:,}₫ via {ladder['tier']}"
        r["verdict"] = "PARTIAL"
    else:
        r["verdict"] = "BLOCKED"
        r["error"] = ("SPA shell, no product grid in raw HTML — matches the "
                      "2026-04-28 finding")
    return r


OTHER_HOSTS = [
    # Ordinary storefronts, not marketplaces. They matter because Mercai is no
    # longer ceramics-only, and because these are the sites where the
    # site-agnostic rungs of the ladder are supposed to pay off.
    ("sendo.vn", "https://www.sendo.vn/tim-kiem?q={kw}"),
    ("fptshop.com.vn", "https://fptshop.com.vn/tim-kiem?q={kw}"),
    ("dienmayxanh.com", "https://www.dienmayxanh.com/tim-kiem?key={kw}"),
    ("thegioididong.com", "https://www.thegioididong.com/tim-kiem?key={kw}"),
]


def probe_generic(host, template, keyword):
    """Can we reach it, and does its raw HTML carry anything the ladder can read?"""
    url = template.format(kw=quote(keyword))
    dns = dns_check(url)
    r = {"source": host, "method": "plain HTTP HTML", "status": None, "ms": 0,
         "error": None, "items": 0, "sample": None, "dns": dns}
    if dns[0] != "ok":
        r["verdict"], r["error"] = "LOCAL", _dns_msg(dns)
        return r
    status, body, _, ms, err = fetch(url)
    r.update(status=status, ms=ms, error=err)
    if err or status != 200:
        r["verdict"] = "FAIL"
        return r
    lad = run_ladder(body)
    if lad:
        r["items"] = 1
        r["sample"] = (f"ladder read {lad['price_vnd']:,}₫ via {lad['tier']} "
                       f"(conf {lad['confidence']})")
        r["verdict"] = "OK" if lad["confidence"] >= 90 else "PARTIAL"
    else:
        r["verdict"] = "BLOCKED" if detect_js_required(body, lad) else "EMPTY"
        r["error"] = ("listing renders client-side — product pages may still work, "
                      "test them with --urls")
    return r


# --------------------------------------------------------------------------
# Q2b — the validation gate, against ground truth
# --------------------------------------------------------------------------
#
# The plain --urls mode reports what the ladder read but cannot say whether it
# read CORRECTLY -- it has no ground truth, so it can only ask a human to check
# by eye. Tiki closes that gap: its JSON API returns the authoritative price for
# a product AND the path to that product's HTML page. Reading the page with the
# ladder and comparing against the API is a real check, run at whatever sample
# size we like.
#
# That only covers hosts with an API. For everywhere else the strongest
# available signal is still cross-tier agreement (section 4.6), which is
# weaker: two tiers can agree on the same wrong number if they both read the
# same misplaced element.

GATE_MIN_HIGH_CONFIDENCE_PCT = 70
GATE_CONFIDENCE = 90
POLITE_DELAY_SECONDS = 2.5


def tiki_truth_set(keywords, want):
    """
    Product pages with a known-correct price, from Tiki's own API.

    Sampled ROUND-ROBIN across the keywords, not keyword-by-keyword. Filling
    the quota from the first keyword before moving on is the obvious
    implementation and it is wrong: it silently produces a sample from one
    category, and a gate that only ever tested tableware would pass while
    saying nothing about the rest of the catalogue.
    """
    pools = []
    for keyword in keywords:
        url = (f"https://tiki.vn/api/v2/products?q={quote(keyword)}"
               f"&limit=20&sort=top_seller")
        status, body, _, _, err = fetch(url, {"Accept": "application/json"})
        if err or status != 200:
            pools.append((keyword, []))
            continue
        try:
            data = json.loads(body).get("data") or []
        except Exception:
            data = []
        pools.append((keyword, [r for r in data
                                if r.get("url_path") and r.get("price")]))

    seen, out = set(), []
    depth = 0
    while len(out) < want and any(depth < len(rows) for _, rows in pools):
        for keyword, rows in pools:
            if len(out) >= want or depth >= len(rows):
                continue
            row = rows[depth]
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            out.append({
                "url": f"https://tiki.vn/{row['url_path']}",
                "truth": int(row["price"]),
                "name": row.get("name", "")[:60],
                "keyword": keyword,
            })
        depth += 1
    return out


def run_gate(keywords, want, delay=POLITE_DELAY_SECONDS):
    import time

    print(f"\n\033[1mPhase 1.5 — validation gate\033[0m")
    print(f"    Ground truth from Tiki's API; the ladder reads the HTML page.")
    print(f"    Gate: >={GATE_MIN_HIGH_CONFIDENCE_PCT}% at confidence >={GATE_CONFIDENCE}, "
          f"and ZERO wrong at that confidence.\n")

    targets = tiki_truth_set(keywords, want)
    if not targets:
        print("  could not build a truth set — is tiki.vn reachable from here?")
        return {"targets": 0}
    print(f"  {len(targets)} products with known prices. "
          f"Fetching each page, {delay}s apart.\n")

    rows = []
    for i, target in enumerate(targets):
        if i:
            time.sleep(delay)
        status, body, _, ms, err = fetch(target["url"])
        row = {**target, "http": status, "ms": ms}
        if err or status != 200:
            row["outcome"] = "http_error"
            rows.append(row)
            print(f"  \033[31m✗\033[0m HTTP {status or '-'}  {target['name'][:48]}")
            continue

        lad = run_ladder(body)
        if lad is None:
            row["outcome"] = ("js_required" if detect_js_required(body, lad)
                              else "no_price_found")
            rows.append(row)
            print(f"  \033[33m~\033[0m {row['outcome']:<14} {target['name'][:48]}")
            continue

        row.update(lad)
        correct = lad["price_vnd"] == target["truth"]
        row["outcome"] = "correct" if correct else "wrong"
        rows.append(row)

        mark = "\033[32m✓\033[0m" if correct else "\033[31m✗ WRONG\033[0m"
        print(f"  {mark} {lad['price_vnd']:>10,}₫ (truth {target['truth']:>10,}₫) "
              f"conf={lad['confidence']:<3} {lad['tier']:<7} {target['name'][:40]}")
        if not correct:
            print(f"        \033[31mevidence: {lad['evidence'][:88]}\033[0m")

    # ---- verdict ----
    n = len(rows)
    high = [r for r in rows if r.get("confidence", 0) >= GATE_CONFIDENCE]
    wrong_high = [r for r in high if r["outcome"] == "wrong"]
    correct_high = [r for r in high if r["outcome"] == "correct"]
    pct = len(high) / n * 100 if n else 0

    print(f"\n  {'─' * 66}")
    print(f"  read at confidence >={GATE_CONFIDENCE}:  {len(high)}/{n}  ({pct:.0f}%)"
          f"   {'\033[32mPASS\033[0m' if pct >= GATE_MIN_HIGH_CONFIDENCE_PCT else '\033[31mFAIL\033[0m'}"
          f"  (need >={GATE_MIN_HIGH_CONFIDENCE_PCT}%)")
    print(f"  WRONG at confidence >={GATE_CONFIDENCE}: {len(wrong_high)}"
          f"          {'\033[32mPASS\033[0m' if not wrong_high else '\033[31mFAIL\033[0m'}"
          f"  (need 0 — this one is a blocker, not a target)")
    print(f"  correct at high confidence:  {len(correct_high)}")

    by_keyword = {}
    for r in rows:
        by_keyword.setdefault(r["keyword"], []).append(r)
    print(f"\n  sample spread (a one-category sample is not a gate):")
    for keyword, group in sorted(by_keyword.items()):
        ok = sum(1 for r in group if r["outcome"] == "correct")
        print(f"    {keyword:<22} {len(group):>3}   correct: {ok}/{len(group)}")

    by_tier = {}
    for r in rows:
        by_tier.setdefault(r.get("tier", r["outcome"]), []).append(r)
    print(f"\n  which rung did the work:")
    for tier, group in sorted(by_tier.items(), key=lambda kv: -len(kv[1])):
        ok = sum(1 for r in group if r["outcome"] == "correct")
        print(f"    {tier:<16} {len(group):>3}   correct: {ok}/{len(group)}")

    passed = pct >= GATE_MIN_HIGH_CONFIDENCE_PCT and not wrong_high
    print(f"\n  \033[1mGATE {'PASSED' if passed else 'NOT PASSED'}\033[0m — "
          f"{'phase 2 may proceed' if passed else 'do not build the fetcher yet'}\n")
    return {"rows": rows, "high": len(high), "wrong_high": len(wrong_high),
            "total": n, "passed": passed}


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def _dns_msg(dns):
    kind, host, detail = dns
    if kind == "blackholed":
        return (f"{host} resolves to {detail} — YOUR network is blackholing it, so the "
                f"marketplace never saw this request. Inconclusive: re-run elsewhere.")
    return f"{host} did not resolve ({detail}). Inconclusive: local DNS problem."


VERDICT_NOTE = {
    "OK": "usable with the cheap fetcher — no browser needed",
    "PARTIAL": "reachable, but the data is not where we need it",
    "EMPTY": "reachable, returned no priced items for this keyword",
    "BLOCKED": "refused us; see error",
    "FAIL": "could not complete the request",
    "LOCAL": "never left this network — says nothing about the source",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keyword", default="bat gom bat trang",
                    help="search term for the source probes")
    ap.add_argument("--urls", help="file of product URLs, one per line, for the ladder")
    ap.add_argument("--json", help="also write results here")
    ap.add_argument("--skip-probes", action="store_true")
    ap.add_argument("--all-hosts", action="store_true",
                    help="also probe ordinary VN retailers, not just the marketplaces")
    ap.add_argument("--self-test", action="store_true",
                    help="run the parser/ladder/model-token assertions and exit")
    ap.add_argument("--gate", action="store_true",
                    help="phase 1.5: check the ladder against Tiki's authoritative prices")
    ap.add_argument("--gate-n", type=int, default=20,
                    help="how many products to check in --gate mode")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.gate:
        keywords = ["bát gốm sứ", "ấm chén trà", "amply bluetooth", "loa bluetooth",
                    "tai nghe bluetooth", "đĩa gốm sứ"]
        result = run_gate(keywords, args.gate_n)
        if args.json:
            with open(args.json, "w") as fh:
                json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
            print(f"  wrote {args.json}\n")
        return 0 if result.get("passed") else 1

    results = {"keyword": args.keyword, "probes": [], "ladder": []}

    if not args.skip_probes:
        print(f"\n\033[1mQ1 — which sources serve us data from this network?\033[0m")
        print(f"    keyword: {args.keyword!r}\n")
        probes = [lambda k: probe_tiki(k), lambda k: probe_shopee(k),
                  lambda k: probe_lazada(k)]
        if args.all_hosts:
            probes += [(lambda h, t: (lambda k: probe_generic(h, t, k)))(h, t)
                       for h, t in OTHER_HOSTS]
        for fn in probes:
            r = fn(args.keyword)
            results["probes"].append(r)
            mark = {"OK": "\033[32m PASS \033[0m", "PARTIAL": "\033[33m PART \033[0m",
                    "EMPTY": "\033[33m EMPTY\033[0m", "BLOCKED": "\033[31m BLOCK\033[0m",
                    "FAIL": "\033[31m FAIL \033[0m",
                    "LOCAL": "\033[35m LOCAL\033[0m"}[r["verdict"]]
            print(f"  [{mark}] {r['source']:<14} {r['method']:<28} "
                  f"{str(r['status'] or '-'):>4}  {r['ms']:>5}ms  items={r['items']}")
            if r["sample"]:
                print(f"           └─ {r['sample']}")
            if r["error"]:
                print(f"           └─ \033[2m{r['error']}\033[0m")

        local = [r["source"] for r in results["probes"] if r["verdict"] == "LOCAL"]
        if local:
            print(f"\n  \033[35mNever left this network: {', '.join(local)}.\033[0m")
            print("  Those rows prove nothing about the marketplaces. Re-run from a network")
            print("  without DNS filtering before concluding anything about anti-bot.")
        print()

    if args.urls:
        try:
            urls = [l.strip() for l in open(args.urls) if l.strip()
                    and not l.startswith("#")]
        except OSError as exc:
            print(f"could not read {args.urls}: {exc}", file=sys.stderr)
            return 2

        print(f"\033[1mQ2 — does the extraction ladder read real pages?\033[0m")
        print(f"    {len(urls)} URLs. Gate: >=70% at confidence >=90, "
              f"and ZERO wrong prices at confidence >=90.\n")
        high = wrong_candidates = 0
        for url in urls:
            host = urlparse(url).netloc
            status, body, _, ms, err = fetch(url)
            row = {"url": url, "host": host, "status": status, "ms": ms, "error": err}
            if err or status != 200:
                row["verdict"] = "http_error"
                print(f"  \033[31m✗\033[0m {host:<20} HTTP {status or '-'}  {err or ''}")
            else:
                lad = run_ladder(body)
                if lad is None:
                    row["verdict"] = ("js_required" if detect_js_required(body, lad)
                                      else "no_price_found")
                    print(f"  \033[31m✗\033[0m {host:<20} {row['verdict']}  "
                          f"({len(body):,} bytes)")
                else:
                    row.update(lad)
                    row["verdict"] = "ok"
                    if lad["confidence"] >= 90:
                        high += 1
                        wrong_candidates += 1
                    colour = "\033[32m" if lad["confidence"] >= 90 else "\033[33m"
                    print(f"  {colour}✓\033[0m {host:<20} "
                          f"{lad['price_vnd']:>12,}₫  conf={lad['confidence']:<3} "
                          f"via {lad['tier']:<8} [{'+'.join(lad['tiers_matched'])}] {ms:>5}ms")
                    print(f"      \033[2m{lad['evidence'][:100]}\033[0m")
                    if lad["flag"]:
                        # Agreement is confirmation, not a warning -- rendering
                        # both the same way trains the reader to skip the line
                        # that actually matters.
                        confirming = lad["flag"].startswith("agrees")
                        icon, colour = ("✓", "\033[32m") if confirming else ("⚠", "\033[33m")
                        print(f"      {colour}{icon} {lad['flag']}\033[0m")
            results["ladder"].append(row)

        n = len(urls)
        pct = (high / n * 100) if n else 0
        gate = "\033[32mgate met\033[0m" if pct >= 70 else "\033[31mgate NOT met\033[0m"
        print(f"\n  {high}/{n} at confidence >=90 ({pct:.0f}%) — {gate}")
        if wrong_candidates:
            print(f"  \033[1mNow check every one of those {wrong_candidates} by eye.\033[0m "
                  f"One wrong price at confidence >=90 blocks phase 2, regardless of the "
                  f"percentage above.\n  The script cannot judge this — it has no ground truth.")
        print()

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)
        print(f"  wrote {args.json}\n")
    return 0


def self_test():
    """Assertions for every rule this script encodes. No network."""
    checks = []

    def eq(label, got, want):
        checks.append((label, got == want, f"{got!r} != {want!r}"))

    for text, want in [
        ("1.250.000₫", 1_250_000), ("₫1,250,000", 1_250_000), ("1.250.000 đ", 1_250_000),
        ("250000 VND", 250_000), ("250k", 250_000), ("1,2 triệu", 1_200_000),
        ("1.2tr", 1_200_000), ("35 nghìn", 35_000), ("185000", 185_000),
        ("0", None), ("2.000.000.000", None), ("1.234,50", None),
    ]:
        eq(f"parse_vnd({text!r})", parse_vnd(text), want)

    for text in ["185.000₫", "185.000 đ", "185.000 đồng", "₫185.000",
                 "185,000 VND", "185.000VNĐ"]:
        got = tier_text(f"<body><span>{text}</span></body>")
        eq(f"tier_text({text!r})", got[0][2] if got else None, 185_000)

    ld = ('<script type="application/ld+json">{"@type":"Product","offers":'
          '{"price":"185000","priceCurrency":"VND"}}</script>'
          '<meta property="product:price:amount" content="185000">')
    eq("cross-tier agreement -> 99", run_ladder(ld)["confidence"], 99)
    eq("cross-tier conflict -> downgrade",
       run_ladder(ld.replace('content="185000"', 'content="999000"'))["confidence"], 70)
    eq("strike-through skipped",
       run_ladder("<del>250.000₫</del><span>185.000₫</span>")["price_vnd"], 185_000)
    eq("originalPrice excluded",
       run_ladder('<script id="__NEXT_DATA__">{"p":{"price":185000,'
                  '"originalPrice":250000}}</script>')["price_vnd"], 185_000)
    eq("js_required detected",
       detect_js_required('<div id="__next"></div>', None), True)

    eq("model token, hyphenated",
       model_tokens("Nobsound MS-10D MKIII"), {"MS-10D"})
    eq("model token, dotted",
       model_tokens("FX-Audio XL-2.1BL Bluetooth 4.0"), {"XL-2.1BL"})
    eq("model tokens, two in one title",
       model_tokens("JOYO JBA-10 & JBA-35 Loa"), {"JBA-10", "JBA-35"})
    eq("ceramics yield no model token",
       model_tokens("Bát ăn cơm gốm sứ Bát Tràng men lam cao cấp 15cm"), set())
    eq("units are not models", model_tokens("loa 15cm 200w"), set())
    eq("differently-worded listings still join",
       model_tokens("Bộ Amplifier Nobsound MS-10D MKIII Cao Cấp")
       & model_tokens("Ampli đèn Nobsound MS-10D MKIII chính hãng"), {"MS-10D"})

    bad = [(l, why) for l, ok, why in checks if not ok]
    for label, ok, _ in checks:
        print(f"  {'\033[32mok  \033[0m' if ok else '\033[31mFAIL\033[0m'} {label}")
    print(f"\n  {len(checks) - len(bad)}/{len(checks)} passed")
    for label, why in bad:
        print(f"    {label}: {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
