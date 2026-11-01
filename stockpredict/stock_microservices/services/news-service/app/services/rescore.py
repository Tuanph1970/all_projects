"""Backlog #113 — re-score news rows classified before #112's fix.

The poller only classifies rows with classified_at IS NULL, so rows scored by
the old pipeline (neutral stored as +0.5, 'good' on routine filings) keep those
values forever. They are identifiable: score_source is NULL on exactly those
rows (#112(d)). This re-classifies them through the same NewsClassifier the
poller uses and writes the result with mark_classified.

What it deliberately does NOT do:
  * notify. It never calls the notifier and never touches notified_at, so
    re-labelling a September story 'good' cannot fire a stale alert.
  * store a non-judgement. If ai-insights answers with score_source
    'template' (no LLM reachable), the row is left as it was and counted as
    deferred — writing it would take it out of the NULL set for good while
    still holding no real score. Re-run later to pick it up.
  * guess at an old upstream. 'unknown' means ai-insights predates #112 and
    does not report provenance; the run stops at once rather than spend calls.

Run inside the news-service container (dry run first; it makes no LLM calls):

    python -m app.services.rescore                    # count only
    python -m app.services.rescore --apply --limit 5  # trial on 5 rows
    python -m app.services.rescore --apply            # the rest

Every applied row is written to an audit CSV (old and new values).
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from app.exceptions import ClassificationError

logger = logging.getLogger(__name__)

AUDIT_FIELDS = (
    "news_id", "symbol", "ts_utc", "title",
    "old_sentiment", "old_score", "old_category",
    "new_sentiment", "new_score", "new_category", "new_score_source",
)


class UpstreamTooOld(RuntimeError):
    """ai-insights did not report score_source — it is not running #112."""


@dataclass
class RescoreStats:
    candidates: int = 0
    rescored: int = 0
    deferred: int = 0   # classifier failed, or answered with a template score
    changed_label: int = 0
    audit_rows: list = field(default_factory=list)


def rescore(
    repo,
    classifier,
    *,
    apply: bool = False,
    limit: Optional[int] = None,
    pause_seconds: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
) -> RescoreStats:
    rows = repo.list_unsourced_scored(stream="company")
    stats = RescoreStats(candidates=len(rows))
    if not apply:
        return stats

    for i, row in enumerate(rows[:limit] if limit is not None else rows):
        if i and pause_seconds:
            sleep(pause_seconds)
        try:
            c = classifier.classify(row)
        except ClassificationError as exc:
            logger.warning("deferred %s: %s", row.news_id, exc)
            stats.deferred += 1
            continue

        if c.score_source == "unknown":
            raise UpstreamTooOld(
                "ai-insights returned no score_source; deploy #112 there before re-scoring"
            )
        if c.score_source == "template":
            logger.warning("deferred %s: no LLM answered (template score)", row.news_id)
            stats.deferred += 1
            continue

        repo.mark_classified(
            row.news_id, sentiment=c.sentiment, category=c.category,
            score=c.score, score_source=c.score_source,
        )
        stats.rescored += 1
        if c.sentiment != row.sentiment:
            stats.changed_label += 1
        stats.audit_rows.append({
            "news_id": row.news_id, "symbol": row.symbol,
            "ts_utc": row.ts_utc.isoformat() if row.ts_utc else "", "title": row.title,
            "old_sentiment": row.sentiment, "old_score": row.sentiment_score,
            "old_category": row.category,
            "new_sentiment": c.sentiment, "new_score": c.score,
            "new_category": c.category, "new_score_source": c.score_source,
        })
    return stats


def _write_audit(path: str, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=AUDIT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="call the LLM and write (default: count only)")
    parser.add_argument("--limit", type=int, default=None, help="re-score at most N rows this run")
    parser.add_argument("--pause", type=float, default=0.5, help="seconds between LLM calls")
    parser.add_argument("--timeout", type=float, default=60.0, help="per-call HTTP timeout")
    parser.add_argument("--audit", default="/tmp/rescore_audit.csv", help="audit CSV path")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from sqlalchemy import create_engine

    from app.config import get_settings
    from app.ingest.classifier import NewsClassifier
    from app.repositories.news_repository import NewsRepository

    settings = get_settings()
    repo = NewsRepository(create_engine(settings.DATABASE_URL))
    classifier = NewsClassifier(
        settings.AI_INSIGHTS_SERVICE_URL, api_prefix=settings.API_PREFIX, timeout=args.timeout,
    )

    try:
        stats = rescore(repo, classifier, apply=args.apply, limit=args.limit, pause_seconds=args.pause)
    except UpstreamTooOld as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        return 2

    if not args.apply:
        print(f"{stats.candidates} rows scored before #112 (score_source NULL). "
              f"Dry run: no LLM calls made. Re-run with --apply (try --limit 5 first).")
        return 0

    _write_audit(args.audit, stats.audit_rows)
    print(f"candidates {stats.candidates} | re-scored {stats.rescored} | "
          f"label changed {stats.changed_label} | deferred {stats.deferred} | audit {args.audit}")
    remaining = stats.candidates - stats.rescored
    if remaining:
        print(f"{remaining} still unscored — re-run to continue (rows already done are skipped).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
