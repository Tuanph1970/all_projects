"""
Vietnamese price strings -> Decimal.

Its own module with its own tests, because this is where quiet, systematic
errors live. The separator rule below is the whole reason: `float("1.250.000")`
raises, and `float("1.250")` returns 1.25 -- an error of one thousand times
that still looks like a plausible price in some other currency, and would sail
through any range check written for VND.

See docs/ai-features/05-price-intelligence.md section 5.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

# A VND price below this is almost certainly a misparse; above it, a typo or a
# unit confusion. Both are recorded as `implausible` rather than trusted.
MIN_VND = 1_000
MAX_VND = 1_000_000_000

_SHORTHAND = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(k|nghin|nghìn|tr|trieu|triệu)\b", re.IGNORECASE
)

# `\b` after `₫` never matches -- `₫` is not a word character, so there is no
# boundary between it and the space that follows. A negative lookahead is what
# this needs. Longest currency alternative first, so "185.000 đồng" consumes
# "đồng" rather than matching "đ" and then failing the lookahead.
_CUR = r"(?:₫|VNĐ|VND|đồng|đ)"
VND_IN_TEXT = re.compile(
    r"(?:₫|VNĐ|VND)\s*([\d.,]{4,})"
    r"|([\d.,]{4,})\s*" + _CUR + r"(?![\w])",
    re.IGNORECASE,
)


def parse_vnd(text) -> Optional[Decimal]:
    """
    A Vietnamese price string as a Decimal, or None if it cannot be trusted.

    Returning None rather than a best guess is deliberate: a missing price is a
    gap the seller can see, and a wrong one is a pricing decision made on our
    say-so.
    """
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None

    shorthand = _SHORTHAND.search(raw)
    if shorthand:
        try:
            base = Decimal(shorthand.group(1).replace(",", "."))
        except InvalidOperation:
            return None
        unit = shorthand.group(2).lower()
        multiplier = 1_000 if unit.startswith(("k", "ngh")) else 1_000_000
        return _band(base * multiplier)

    if _is_negative(raw):
        # A minus in front of the number means a discount amount ("Giảm
        # -50.000₫"), not a price. Stripping it silently turns a saving into a
        # competitor's price, which is precisely the wrong-element failure this
        # module exists to prevent.
        return None

    digits = re.sub(r"[^\d.,]", "", raw)
    if not digits:
        return None

    has_dot, has_comma = "." in digits, "," in digits
    if has_dot and has_comma:
        # Whichever separator comes LAST is the decimal point; the other groups
        # thousands. This is locale-agnostic on purpose -- the same page can
        # carry both conventions.
        decimal_sep = "." if digits.rfind(".") > digits.rfind(",") else ","
        group_sep = "," if decimal_sep == "." else "."
        digits = digits.replace(group_sep, "").replace(decimal_sep, ".")
    elif has_dot or has_comma:
        sep = "." if has_dot else ","
        parts = digits.split(sep)
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            digits = "".join(parts)          # groups of three -> thousands
        else:
            digits = digits.replace(sep, ".")

    try:
        value = Decimal(digits)
    except InvalidOperation:
        return None

    # VND carries no minor units in practice. A fractional result means the
    # separator rule above picked wrong, so refuse rather than round.
    if value != value.to_integral_value():
        return None
    return _band(value)


# Currency marks and spaces may sit between a minus sign and its digits.
_SIGN_GAP = re.compile(r"^[\s₫đ]*$", re.IGNORECASE)


def _is_negative(raw: str) -> bool:
    """
    A minus immediately before the FIRST digit, and only there.

    Scoped that tightly on purpose: `₫250.000 - ₫500.000` is a variant range,
    a completely normal way for a Vietnamese storefront to write two prices,
    and rejecting it would throw away a legitimate reading.
    """
    match = re.search(r"\d", raw)
    if not match:
        return False
    head = raw[: match.start()]
    minus = head.rfind("-")
    return minus != -1 and bool(_SIGN_GAP.match(head[minus + 1:]))


def _band(value: Decimal) -> Optional[Decimal]:
    value = value.to_integral_value()
    if MIN_VND <= value <= MAX_VND:
        return value
    return None


def is_plausible(value, history=()) -> bool:
    """
    A magnitude check against a comparable's own past observations.

    This is the one that catches a site redesign silently repointing a selector
    at the wrong element -- the failure mode most likely to survive every other
    guard, because the new number is well-formed and in range. Needs a few
    observations before it can say anything, so it passes by default.
    """
    if value is None:
        return False
    if not MIN_VND <= Decimal(value) <= MAX_VND:
        return False

    prices = sorted(Decimal(p) for p in history if p is not None)
    if len(prices) < 3:
        return True
    median = prices[len(prices) // 2]
    if median <= 0:
        return True
    return median / 20 <= Decimal(value) <= median * 20
