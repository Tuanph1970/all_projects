"""ingest/ NewsClassifier — sentiment + category for a company NewsItem (FR-NEWS-CLASSIFY).

Sentiment and score come from ai-insights-service's NewsAnalysis endpoint — the LLM does
the hard, Vietnamese-capable work (EC-N5); we do not host a model here. ai-insights'
NewsAnalysisResponse exposes NO category, so `category` is derived locally by a lightweight
keyword rule over the closed company vocab (SRS Appendix A). That is a tag, not a model —
the classifier itself stays with ai-insights.

Any error/timeout raises ClassificationError; the poller then stores the item unclassified
and retries on a later tick (EC-N7). Only new items are classified (EC-N11), enforced by
the caller.
"""
from __future__ import annotations

import logging
from typing import NamedTuple, Optional

import httpx

from app.exceptions import ClassificationError
from app.models.news_item import NewsItem

logger = logging.getLogger(__name__)


class Classification(NamedTuple):
    sentiment: str   # "good" | "bad" | "neutral"
    category: str    # closed company vocab (SRS Appendix A)
    score: float     # [-1, 1]
    # Backlog #112(d). How `score` was obtained, straight from ai-insights:
    # 'model' | 'label_fallback' | 'keyword_fallback' | 'template', or 'unknown'
    # when the upstream does not report it. Stored so a row scored while no LLM
    # was reachable is distinguishable from a real judgement — without it, the
    # corpus silently mixes the two and cannot be audited afterwards.
    score_source: str = "unknown"


_GOOD = {"bullish", "positive", "good", "up"}
_BAD = {"bearish", "negative", "bad", "down"}

# Closed company-news category vocab (SRS Appendix A). ai-insights now returns a
# `category`; we accept it when it is in this set, else derive one locally.
_CATEGORIES = frozenset(
    {"new_product", "new_tech", "management", "regulatory", "earnings", "partnership", "other"}
)

# Keyword -> category, checked in order (first match wins). Lowercased substring match
# over title+body; covers EN and common VN terms for VN company news.
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("new_product", ("new product", "product line", "launch", "ra mắt", "sản phẩm")),
    ("new_tech", ("technology", "tech ", " ai", "ai ", "platform", "công nghệ")),
    ("management", ("ceo", "chairman", "appoint", "resign", "board", "management",
                    "lãnh đạo", "bổ nhiệm", "từ chức")),
    ("regulatory", ("regulat", "license", "licence", "fine", "fined", "lawsuit", "ssc",
                    "quy định", "xử phạt", "giấy phép")),
    ("earnings", ("earnings", "revenue", "profit", "quarter", "q1", "q2", "q3", "q4",
                  "lợi nhuận", "doanh thu", "kết quả kinh doanh")),
    ("partnership", ("partner", "partnership", "cooperat", "agreement", "hợp tác", "ký kết")),
]


def _map_sentiment(raw) -> str:
    s = (raw or "").strip().lower()
    if s in _GOOD:
        return "good"
    if s in _BAD:
        return "bad"
    return "neutral"


def _clamp_score(raw) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return max(-1.0, min(1.0, v))


def _derive_category(title: str, body: Optional[str]) -> str:
    text = f"{title or ''} {body or ''}".lower()
    for category, keywords in _CATEGORY_RULES:
        if any(k in text for k in keywords):
            return category
    return "other"


class NewsClassifier:
    def __init__(
        self,
        base_url: str,
        *,
        api_prefix: str = "stock_helper",
        client: Optional[httpx.Client] = None,
        timeout: float = 10.0,
    ):
        self._base = base_url.rstrip("/")
        self._prefix = api_prefix
        self._client = client
        self._timeout = timeout

    def classify(self, item: NewsItem) -> Classification:
        url = f"{self._base}/{self._prefix}/api/v2/ai/news-analysis"
        payload = {
            "symbol": item.symbol or "",
            "news_items": [
                {
                    "title": item.title or "",
                    "content": item.body or "",
                    "source": item.url or "",
                    "date": item.ts_utc.isoformat() if item.ts_utc else "",
                }
            ],
        }
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.post(url, json=payload)
        except Exception as exc:  # noqa: BLE001 — treat any transport failure as classifier down
            raise ClassificationError(f"ai-insights unavailable: {exc}") from exc
        finally:
            if self._client is None:
                client.close()

        if resp.status_code != 200:
            raise ClassificationError(f"ai-insights returned {resp.status_code}")

        data = resp.json() or {}
        # Prefer ai-insights' category (LLM-assigned); fall back to a local keyword scan
        # when it is absent or outside the closed vocab.
        category = data.get("category")
        if not isinstance(category, str) or category not in _CATEGORIES:
            category = _derive_category(item.title, item.body)
        # An upstream that does not report provenance yields "unknown" rather
        # than a cheerful "model": asserting a provenance we have no evidence
        # for is the over-claim this field exists to prevent.
        source = data.get("score_source")
        return Classification(
            sentiment=_map_sentiment(data.get("overall_sentiment")),
            category=category,
            score=_clamp_score(data.get("sentiment_score")),
            score_source=source if isinstance(source, str) and source else "unknown",
        )
