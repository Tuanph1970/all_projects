"""Domain service for understanding user queries."""
import re

from app.domain.value_objects.search_query import SearchQuery

# Common Vietnamese and English stop words to filter out
STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "must", "need", "dare",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "not", "only", "same", "so", "than", "too", "very", "just", "because",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "she", "her",
    "it", "its", "they", "them", "their", "and", "but", "or", "if",
    # Vietnamese
    "là", "của", "và", "có", "được", "cho", "trong", "này", "đó",
    "với", "từ", "các", "một", "không", "như", "để", "về", "theo",
    "khi", "tại", "hay", "hoặc", "cũng", "đã", "sẽ", "đang",
    "gì", "nào", "nên", "thì", "mà", "vì", "bởi", "ai",
})


class QueryUnderstandingService:
    """Extracts keywords, entities, and intent from user questions."""

    def parse(self, raw_query: str) -> SearchQuery:
        """Parse a raw user query into a structured SearchQuery."""
        if not raw_query or not raw_query.strip():
            return SearchQuery(raw_query="", keywords=(), intent="general")

        cleaned = raw_query.strip()
        intent = self._detect_intent(cleaned)
        keywords = self._extract_keywords(cleaned)

        return SearchQuery(
            raw_query=cleaned,
            keywords=tuple(keywords),
            intent=intent,
        )

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        # Remove special characters but keep Vietnamese diacritics
        words = re.findall(r'[\w\u00C0-\u024F\u1E00-\u1EFF]+', text.lower())
        # Filter stop words and short words
        keywords = [w for w in words if w not in STOP_WORDS and len(w) > 1]
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        return unique

    def _detect_intent(self, text: str) -> str:
        """Detect the intent of the query."""
        lower = text.lower()
        if any(w in lower for w in ["so sánh", "compare", "versus", "vs", "khác nhau"]):
            return "comparison"
        if any(w in lower for w in ["định nghĩa", "define", "what is", "là gì"]):
            return "definition"
        if any(w in lower for w in ["cách", "how to", "làm thế nào", "hướng dẫn"]):
            return "howto"
        return "general"
