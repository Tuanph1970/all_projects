"""services/ PollerScheduler — a non-overlapping async poll loop (FR-NEWS-SCHED, NFR-N6).

Mirrors the decision-helper custom async scheduler idiom (no Celery/APScheduler). A slow
tick defers the next one rather than overlapping: the loop awaits `tick()` fully, then
waits the interval (interruptible by stop()). Errors in a tick are logged and the loop
continues.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class PollerScheduler:
    def __init__(self, poller, interval_seconds: float, *, name: str = "poller"):
        self._poller = poller
        self._interval = interval_seconds
        self._name = name
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name=f"news-scheduler-{self._name}")
        logger.info("scheduler %s started (interval=%ss)", self._name, self._interval)

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                await self._poller.tick()
            except Exception:  # noqa: BLE001 — never let a bad tick kill the loop
                logger.exception("scheduler %s tick failed", self._name)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval)
            except asyncio.TimeoutError:
                pass  # interval elapsed -> next tick

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None
        logger.info("scheduler %s stopped", self._name)
