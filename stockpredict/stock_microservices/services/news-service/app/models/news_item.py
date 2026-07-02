"""Source-agnostic normalized news item + the dedupe-key derivation (SRS §4.2).

Every ingest adapter (company_source, macro_feeds) emits `NewsItem`s; the rest of the
pipeline is source-agnostic. `news_id()` is a PURE function of source fields — no clock,
no randomness (NFR-N2) — so the same source entry always maps to the same key (EC-N2).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewsItem:
    source: str
    stream: str            # "company" | "macro"
    symbol: str | None
    ts_utc: datetime       # tz-aware UTC (EC-N6)
    title: str
    body: str | None
    url: str | None
    lang: str | None
    raw_json: str
    guid: str | None = None  # source-provided stable id; preferred dedupe basis when present

    def _primary_key(self) -> str:
        """First available of guid / url / (symbol‖title‖date) — FR-NEWS-DEDUP."""
        if self.guid:
            return self.guid
        if self.url:
            return self.url
        day = self.ts_utc.date().isoformat() if self.ts_utc is not None else ""
        return f"{self.symbol or ''}|{self.title}|{day}"

    def news_id(self) -> str:
        digest = hashlib.sha256(f"{self.source}|{self._primary_key()}".encode("utf-8"))
        return digest.hexdigest()  # 64 hex chars -> String(64)
