"""News-service exceptions (NFR-N3).

Routes map these to HTTP; pollers swallow-and-log them (log-and-continue, EC-N7).
"""
from __future__ import annotations


class NewsIngestError(Exception):
    """Base for all news-ingestion errors."""


class SourceUnavailableError(NewsIngestError):
    """An external source/feed/upstream returned no usable data (non-200, empty, timeout)."""


class ClassificationError(NewsIngestError):
    """The ai-insights classifier could not classify an item (error/timeout).

    The item is stored unclassified and retried on a later tick (EC-N7); it is not
    notified until classified.
    """
