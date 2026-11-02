"""Publisher keys and consumer patterns must be compatible — checked, not assumed.

The price-alert path shipped fully built and delivered nothing for its entire
life: the publisher sent `stock.price.updated.<SYMBOL>`, the consumer bound
`stock.price.updated`, and on a topic exchange the extra word means no match.
Nothing failed, nothing logged, the queue had a live consumer and zero messages.

Measured against the live broker on 2026-11-02, publishing
`stock.price.updated.ACB`: the shipped binding received 0, `.#` and `.*` each
received 1. These tests encode the AMQP rule so the same disagreement cannot
recur without failing here first.
"""
from __future__ import annotations

import pytest

from stock_common.events.models import DomainEvents
from stock_common.events.routing import (
    PRICE_UPDATED_PATTERN,
    price_updated_routing_key,
    topic_matches,
)


# ---------------------------------------------------------------------------
# the invariant that was violated
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("symbol", ["ACB", "POW", "VNM", "DPG"])
def test_the_subscription_pattern_matches_the_published_key(symbol):
    """THE regression guard. One definition each, asserted compatible."""
    assert topic_matches(PRICE_UPDATED_PATTERN, price_updated_routing_key(symbol))


def test_the_pattern_that_shipped_would_fail_this_test():
    """Guards the guard: if topic_matches were too permissive the test above
    would pass for any pattern, including the broken one. Verified against the
    real broker — this binding received 0 of 1 messages."""
    assert not topic_matches("stock.price.updated", price_updated_routing_key("ACB"))


def test_the_pattern_also_matches_a_key_with_no_symbol():
    """`#` not `*`, so a publisher that omits the symbol is still heard rather
    than silently dropped — the failure mode this whole module exists for."""
    assert topic_matches(PRICE_UPDATED_PATTERN, DomainEvents.STOCK_PRICE_UPDATED)


def test_the_pattern_does_not_swallow_unrelated_events():
    """A wildcard wide enough to catch everything would be its own bug."""
    for other in ("stock.volume.updated.ACB", "portfolio.alert.triggered",
                  "stock.price.deleted.ACB", "news.company"):
        assert not topic_matches(PRICE_UPDATED_PATTERN, other), other


# ---------------------------------------------------------------------------
# the routing key
# ---------------------------------------------------------------------------

def test_the_key_is_per_symbol_so_a_consumer_can_take_one_ticker():
    assert price_updated_routing_key("ACB") == "stock.price.updated.ACB"
    assert price_updated_routing_key("acb") == "stock.price.updated.ACB"
    assert price_updated_routing_key("  pow  ") == "stock.price.updated.POW"


def test_a_single_symbol_subscription_is_possible():
    """What the per-symbol key buys, and why the publisher should not be
    'simplified' to the bare event name."""
    key = price_updated_routing_key("ACB")
    assert topic_matches("stock.price.updated.ACB", key)
    assert not topic_matches("stock.price.updated.POW", key)


# ---------------------------------------------------------------------------
# topic_matches itself — it is only useful if it is the real rule
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pattern,key,expected", [
    ("a.b.c", "a.b.c", True),
    ("a.b.c", "a.b.d", False),
    ("a.*.c", "a.b.c", True),
    ("a.*.c", "a.b.x.c", False),          # * is exactly one word
    ("a.*", "a.b", True),
    ("a.*", "a", False),                  # * requires a word
    ("a.*", "a.b.c", False),
    ("a.#", "a", True),                   # # is zero or more
    ("a.#", "a.b", True),
    ("a.#", "a.b.c.d", True),
    ("a.#", "b.a", False),
    ("#", "anything.at.all", True),
    ("a.b", "a", False),
    ("a.b", "a.b.c", False),
])
def test_topic_match_follows_the_amqp_rule(pattern, key, expected):
    assert topic_matches(pattern, key) is expected
