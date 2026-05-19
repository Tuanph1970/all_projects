"""F-080 — In-process alert pub/sub broker.

One AlertBroker singleton lives for the lifetime of the process.
Each SSE connection subscribes a Queue; the scheduler publishes into it
when a BUY or SELL_SHORT recommendation fires.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)


class AlertBroker:
    def __init__(self) -> None:
        self._queues: Dict[int, Set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, user_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._queues[user_id].add(q)
        logger.debug("AlertBroker: subscribe user=%d (total=%d)", user_id, self.subscriber_count)
        return q

    def unsubscribe(self, user_id: int, queue: asyncio.Queue) -> None:
        self._queues[user_id].discard(queue)
        logger.debug("AlertBroker: unsubscribe user=%d (total=%d)", user_id, self.subscriber_count)

    async def publish(self, user_id: int, payload: Dict[str, Any]) -> None:
        """Broadcast payload to every SSE client connected for user_id."""
        queues = list(self._queues.get(user_id, set()))
        if not queues:
            return
        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("AlertBroker: queue full for user=%d, alert dropped", user_id)

    @property
    def subscriber_count(self) -> int:
        return sum(len(qs) for qs in self._queues.values())


# Module-level singleton — imported by routes and scheduler
alert_broker = AlertBroker()
