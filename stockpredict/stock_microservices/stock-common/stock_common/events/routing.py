"""Topic routing keys and the patterns that subscribe to them — defined ONCE.

Tech Debt "EventBus underused" / Phase 4 "Event-driven price alerts".

WHY THIS MODULE EXISTS. The price-alert path was fully built: stock-data-service
published `stock.price.updated.<SYMBOL>` per symbol, portfolio-service declared a
durable queue, subscribed, and had tests. It delivered nothing for its entire
life, because the consumer bound the pattern `stock.price.updated` — no wildcard
— and on an AMQP topic exchange that matches only the exact key. The extra
`.ACB` word meant every message was dropped by the exchange.

Measured 2026-11-02 against the live broker, publishing `stock.price.updated.ACB`:

    binding stock.price.updated     -> 0 received   (what shipped)
    binding stock.price.updated.#   -> 1 received
    binding stock.price.updated.*   -> 1 received

Nothing failed, nothing logged, the queue had a healthy consumer and zero
messages — the two sides each spelled the convention separately and disagreed by
one word. So the convention now lives here and both sides import it: a publisher
key and its subscription pattern cannot drift apart if there is only one of each.
"""
from __future__ import annotations

import re

from stock_common.events.models import DomainEvents

#: Pattern a consumer must bind to receive per-symbol price updates.
#: `#` (zero-or-more words) rather than `*` (exactly one) deliberately: it also
#: matches a bare `stock.price.updated` should any publisher ever omit the
#: symbol, so this pattern cannot miss a message for a reason that is invisible.
PRICE_UPDATED_PATTERN = f"{DomainEvents.STOCK_PRICE_UPDATED}.#"


def price_updated_routing_key(symbol: str) -> str:
    """The routing key for one symbol's price update.

    Per-symbol by design — it is what lets a future consumer subscribe to a
    single ticker instead of filtering the whole market in application code.
    """
    return f"{DomainEvents.STOCK_PRICE_UPDATED}.{symbol.strip().upper()}"


def topic_matches(pattern: str, routing_key: str) -> bool:
    """AMQP topic-exchange match: `*` is exactly one word, `#` is zero or more.

    Implemented here so a test can assert publisher/consumer compatibility
    without a broker. Reasoning about the rule is what went wrong the first
    time; this makes it checkable.
    """
    parts = []
    for word in pattern.split("."):
        if word == "*":
            parts.append(r"[^.]+")
        elif word == "#":
            parts.append(r".*")
        else:
            parts.append(re.escape(word))
    # `a.#` must match `a` as well as `a.b`, so fold the separator into the
    # wildcard rather than requiring a dot before it.
    regex = r"\.".join(parts).replace(r"\.(?:.*)", r"(?:\..*)?").replace(r"\..*", r"(?:\..*)?")
    return re.fullmatch(regex, routing_key) is not None
