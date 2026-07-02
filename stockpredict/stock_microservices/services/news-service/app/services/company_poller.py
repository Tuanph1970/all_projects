"""services/ CompanyPoller — Stream B pipeline (FR-NEWS-COMPANY, built first).

One tick, two phases:
  A. Ingest — resolve watched symbols, fetch each symbol's news, upsert new items
     (raw, unclassified). Dedup is inherent in upsert (insert-if-absent, EC-N2).
  B. Classify + notify — for every still-unclassified row, classify via ai-insights;
     on success store the labels and, for good/bad only (EC-N8), emit news.company and
     stamp notified. On classifier failure the row stays unclassified and is retried on a
     later tick (EC-N7 / EC-N11).

Every per-symbol / per-item failure is logged and skipped — a single bad symbol, source,
or classifier call never aborts the tick (EC-N7).
"""
from __future__ import annotations

import logging

from prometheus_client import Counter

from app.exceptions import ClassificationError, NewsIngestError

logger = logging.getLogger(__name__)

POLL_ITEMS = Counter(
    "news_company_poll_total", "Company poll items by stage",
    ["stage"],  # fetched | new | classified | notified | errors
)


class CompanyPoller:
    def __init__(
        self,
        *,
        watch_source,
        company_source,
        classifier,
        repo,
        notifier,
        notify_sentiments=("good", "bad"),
    ):
        self._watch = watch_source
        self._company = company_source
        self._classifier = classifier
        self._repo = repo
        self._notifier = notifier
        self._notify = set(notify_sentiments)

    async def tick(self) -> dict:
        stats = {"fetched": 0, "new": 0, "classified": 0, "notified": 0, "errors": 0}

        # ── Phase A: ingest ─────────────────────────────────────────────
        symbols = self._watch.resolve()
        for symbol in symbols:
            try:
                items = self._company.fetch(symbol)
            except (NewsIngestError, Exception) as exc:  # noqa: BLE001 — log-and-continue
                logger.warning("company fetch failed for %s: %s", symbol, exc)
                stats["errors"] += 1
                continue
            for item in items:
                stats["fetched"] += 1
                try:
                    if self._repo.upsert(item):
                        stats["new"] += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("store failed for %s: %s", symbol, exc)
                    stats["errors"] += 1

        # ── Phase B: classify + notify (covers this tick's new rows and any
        #    still-unclassified rows carried over from earlier ticks) ──────
        for row in self._repo.list_new(stream="company"):
            try:
                c = self._classifier.classify(row)  # row duck-types NewsItem for classify
            except ClassificationError as exc:
                logger.info("classify deferred for %s: %s", row.news_id, exc)
                stats["errors"] += 1
                continue
            except Exception as exc:  # noqa: BLE001
                logger.warning("unexpected classify error for %s: %s", row.news_id, exc)
                stats["errors"] += 1
                continue

            self._repo.mark_classified(
                row.news_id, sentiment=c.sentiment, category=c.category, score=c.score
            )
            stats["classified"] += 1

            if c.sentiment in self._notify:
                try:
                    await self._notifier.emit_news_company(
                        news_id=row.news_id,
                        symbol=row.symbol,
                        title=row.title,
                        url=row.url,
                        ts_utc=row.ts_utc,
                        sentiment=c.sentiment,
                        category=c.category,
                        sentiment_score=c.score,
                    )
                    self._repo.mark_notified(row.news_id)
                    stats["notified"] += 1
                except Exception as exc:  # noqa: BLE001 — bus down: leave notified_at NULL
                    logger.warning("notify failed for %s: %s", row.news_id, exc)
                    stats["errors"] += 1

        for stage, n in stats.items():
            if n:
                POLL_ITEMS.labels(stage=stage).inc(n)
        logger.info("company poll tick: %s", stats)
        return stats
