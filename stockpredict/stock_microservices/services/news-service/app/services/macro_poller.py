"""services/ MacroPoller — Stream A pipeline (FR-NEWS-MACRO).

One tick: read the macro feeds/APIs, upsert new items (dedup, EC-N2), and tag each with
its macro category via mark_classified(sentiment=None, category=...). Tagging inline keeps
macro rows out of the company classifier's list_new(stream="company") and records that the
item is processed. Stream A is store + tag (+ bridge in N13) — NO notification.

Per-item failures are logged and skipped; a feed outage never aborts the tick (EC-N7).
"""
from __future__ import annotations

import logging

from prometheus_client import Counter

logger = logging.getLogger(__name__)

MACRO_ITEMS = Counter(
    "news_macro_poll_total", "Macro poll items by stage",
    ["stage"],  # fetched | new | tagged | bridged | errors
)


class MacroPoller:
    def __init__(self, *, macro_source, repo, bridge=None):
        self._macro = macro_source
        self._repo = repo
        self._bridge = bridge  # optional event-reaction bridge (N13)

    async def tick(self) -> dict:
        stats = {"fetched": 0, "new": 0, "tagged": 0, "bridged": 0, "errors": 0}
        try:
            tagged = self._macro.fetch_all()
        except Exception as exc:  # noqa: BLE001 — whole-sweep failure
            logger.warning("macro fetch_all failed: %s", exc)
            stats["errors"] += 1
            return stats

        for ti in tagged:
            stats["fetched"] += 1
            try:
                if not self._repo.upsert(ti.item):
                    continue  # already seen (EC-N2)
                stats["new"] += 1
                self._repo.mark_classified(
                    ti.item.news_id(), sentiment=None, category=ti.category, score=None
                )
                stats["tagged"] += 1
                if self._bridge is not None and self._bridge.maybe_bridge(ti):
                    self._repo.mark_bridged(ti.item.news_id())
                    stats["bridged"] += 1
            except Exception as exc:  # noqa: BLE001 — per-item, log-and-continue
                logger.warning("macro item store/tag failed for %s: %s",
                               ti.item.news_id(), exc)
                stats["errors"] += 1

        for stage, n in stats.items():
            if n:
                MACRO_ITEMS.labels(stage=stage).inc(n)
        logger.info("macro poll tick: %s", stats)
        return stats
