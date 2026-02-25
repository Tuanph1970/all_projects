"""Tests for QueryUnderstandingService."""
import pytest
from app.domain.services.query_understanding import QueryUnderstandingService


class TestQueryUnderstandingService:
    def setup_method(self):
        self.service = QueryUnderstandingService()

    def test_parse_basic_query(self):
        result = self.service.parse("What is trading psychology?")
        assert result.raw_query == "What is trading psychology?"
        assert "trading" in result.keywords
        assert "psychology" in result.keywords
        # Stop words should be filtered
        assert "what" not in result.keywords
        assert "is" not in result.keywords

    def test_parse_empty_query(self):
        result = self.service.parse("")
        assert result.keywords == ()
        assert result.intent == "general"

    def test_parse_whitespace_query(self):
        result = self.service.parse("   ")
        assert result.keywords == ()

    def test_detect_comparison_intent(self):
        result = self.service.parse("Compare trading and investing")
        assert result.intent == "comparison"

    def test_detect_definition_intent(self):
        result = self.service.parse("What is risk management?")
        assert result.intent == "definition"

    def test_detect_howto_intent(self):
        result = self.service.parse("How to manage risk in trading?")
        assert result.intent == "howto"

    def test_detect_general_intent(self):
        result = self.service.parse("Tell me about stocks")
        assert result.intent == "general"

    def test_vietnamese_query(self):
        result = self.service.parse("Tâm lý giao dịch là gì?")
        assert result.intent == "definition"  # "là gì" detected
        assert len(result.keywords) > 0

    def test_keywords_deduplicated(self):
        result = self.service.parse("trading trading analysis")
        keywords = list(result.keywords)
        assert keywords.count("trading") == 1

    def test_to_search_string(self):
        result = self.service.parse("trading psychology basics")
        search_str = result.to_search_string()
        assert "trading" in search_str
        assert "psychology" in search_str
