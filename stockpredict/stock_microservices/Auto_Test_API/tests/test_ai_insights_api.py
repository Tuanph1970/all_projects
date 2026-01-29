"""
AI Insights API Tests

Tests for AI Insights Service:
- POST /insights/insight - Generate AI insight
- GET /insights/insight/{symbol} - Get insight (GET)
- POST /insights/compare - Compare stocks
- POST /insights/news-analysis - Analyze news impact
- POST /insights/ask - Ask question
- GET /insights/market-overview - Market overview
- GET /insights/capabilities - Get AI capabilities
- POST /insights/batch - Batch insights
- GET /insights/trending - Trending topics
- POST /insights/portfolio-insight - Portfolio insights
- GET /insights/sectors - Sector insights
"""
import sys
import os
from datetime import datetime
from typing import Tuple, Optional
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from utils.http_client import (
    APIClient,
    print_test_result,
    print_section,
    print_summary,
)


class TestAIInsightsAPI:
    """AI Insights API Test Suite"""

    def __init__(self, base_url: str = None, verbose: bool = True):
        self.base_url = base_url or settings.BASE_URL
        self.client = APIClient(self.base_url, verbose=verbose)
        self.test_results = []
        self.test_symbol = settings.TEST_STOCK_SYMBOL
        self.test_symbols = settings.TEST_STOCK_SYMBOLS
        self.access_token: Optional[str] = None

    def _record_result(self, test_name: str, passed: bool, message: str = ""):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        print_test_result(test_name, passed, message)
        return passed

    def _authenticate(self) -> bool:
        """Authenticate for protected endpoints"""
        if self.access_token:
            return True

        unique_id = str(uuid.uuid4())[:8]
        email = f"insights_test_{unique_id}@stockhelper.com"
        password = "TestPass@123"

        self.client.post("/auth/register", json={
            "email": email,
            "username": f"insights_test_{unique_id}",
            "password": password
        })

        response = self.client.post("/auth/login", json={
            "email": email,
            "password": password
        })

        if response.success:
            self.access_token = response.data.get("access_token")
            self.client.set_auth_tokens(self.access_token)
            return True
        return False

    # =========================================================================
    # TEST: AI Capabilities
    # =========================================================================
    def test_get_capabilities(self) -> bool:
        """Test getting AI capabilities"""
        print_section("TEST: Get AI Capabilities")

        response = self.client.get("/insights/capabilities")

        if response.success:
            data = response.data
            passed = isinstance(data, (list, dict))
            return self._record_result(
                "Get AI capabilities",
                passed,
                "Capabilities retrieved"
            )
        else:
            return self._record_result(
                "Get AI capabilities",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Generate Insight
    # =========================================================================
    def test_generate_insight_post(self) -> bool:
        """Test generating AI insight via POST"""
        print_section("TEST: Generate Insight (POST)")

        response = self.client.post("/insights/insight", json={
            "symbol": self.test_symbol,
            "insight_type": "analysis",
            "additional_context": "Focus on short-term outlook"
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            data = response.data
            return self._record_result(
                f"Generate insight for {self.test_symbol}",
                True,
                "Insight generated"
            )
        else:
            # AI service may fail due to API key issues
            return self._record_result(
                f"Generate insight for {self.test_symbol}",
                False,
                response.error or "Failed (may need API key)"
            )

    def test_generate_insight_get(self) -> bool:
        """Test getting AI insight via GET"""
        print_section("TEST: Get Insight (GET)")

        response = self.client.get(f"/insights/insight/{self.test_symbol}", params={
            "insight_type": "overview"
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            return self._record_result(
                f"Get insight for {self.test_symbol}",
                True,
                "Insight retrieved"
            )
        else:
            return self._record_result(
                f"Get insight for {self.test_symbol}",
                False,
                response.error or "Failed (may need API key)"
            )

    # =========================================================================
    # TEST: Stock Comparison
    # =========================================================================
    def test_compare_stocks(self) -> bool:
        """Test comparing stocks with AI"""
        print_section("TEST: Compare Stocks with AI")

        response = self.client.post("/insights/compare", json={
            "symbols": self.test_symbols[:3],
            "focus": "investment potential"
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            return self._record_result(
                f"Compare {', '.join(self.test_symbols[:3])}",
                True,
                "Comparison completed"
            )
        else:
            return self._record_result(
                "Compare stocks with AI",
                False,
                response.error or "Failed (may need API key)"
            )

    # =========================================================================
    # TEST: News Analysis
    # =========================================================================
    def test_news_analysis(self) -> bool:
        """Test analyzing news impact"""
        print_section("TEST: News Analysis")

        response = self.client.post("/insights/news-analysis", json={
            "symbol": self.test_symbol,
            "news_items": [
                {
                    "title": "Company reports strong quarterly earnings",
                    "content": "The company exceeded analyst expectations...",
                    "source": "Test News"
                }
            ]
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            return self._record_result(
                f"Analyze news impact for {self.test_symbol}",
                True,
                "Analysis completed"
            )
        else:
            return self._record_result(
                f"Analyze news impact for {self.test_symbol}",
                False,
                response.error or "Failed (may need API key)"
            )

    # =========================================================================
    # TEST: Ask Question
    # =========================================================================
    def test_ask_question(self) -> bool:
        """Test asking a question to AI"""
        print_section("TEST: Ask Question")

        response = self.client.post("/insights/ask", json={
            "question": f"What are the key factors affecting {self.test_symbol} stock price?",
            "context": "Vietnamese stock market",
            "symbols": [self.test_symbol]
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            return self._record_result(
                "Ask question to AI",
                True,
                "Answer received"
            )
        else:
            return self._record_result(
                "Ask question to AI",
                False,
                response.error or "Failed (may need API key)"
            )

    # =========================================================================
    # TEST: Market Overview
    # =========================================================================
    def test_market_overview(self) -> bool:
        """Test getting market overview"""
        print_section("TEST: Market Overview")

        response = self.client.get("/insights/market-overview", params={
            "focus": "general"
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            return self._record_result(
                "Get market overview",
                True,
                "Overview retrieved"
            )
        else:
            return self._record_result(
                "Get market overview",
                False,
                response.error or "Failed (may need API key)"
            )

    # =========================================================================
    # TEST: Batch Insights
    # =========================================================================
    def test_batch_insights(self) -> bool:
        """Test getting batch insights"""
        print_section("TEST: Batch Insights")

        response = self.client.post("/insights/batch", json={
            "symbols": self.test_symbols[:3],
            "insight_type": "summary",
            "include_comparison": True
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            return self._record_result(
                f"Batch insights for {len(self.test_symbols[:3])} stocks",
                True,
                "Insights generated"
            )
        else:
            return self._record_result(
                "Batch insights",
                False,
                response.error or "Failed (may need API key)"
            )

    # =========================================================================
    # TEST: Trending Topics
    # =========================================================================
    def test_trending_topics(self) -> bool:
        """Test getting trending topics"""
        print_section("TEST: Trending Topics")

        response = self.client.get("/insights/trending")

        if response.success:
            data = response.data
            passed = isinstance(data, (list, dict))
            return self._record_result(
                "Get trending topics",
                passed,
                "Topics retrieved"
            )
        else:
            return self._record_result(
                "Get trending topics",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Portfolio Insight
    # =========================================================================
    def test_portfolio_insight(self) -> bool:
        """Test getting portfolio insights"""
        print_section("TEST: Portfolio Insight")

        if not self._authenticate():
            return self._record_result("Portfolio insight", False, "Authentication failed")

        response = self.client.post("/insights/portfolio-insight", json={
            "holdings": [
                {"symbol": "VNM", "quantity": 100, "average_price": 80000},
                {"symbol": "FPT", "quantity": 50, "average_price": 95000},
                {"symbol": "VCB", "quantity": 200, "average_price": 85000}
            ]
        }, timeout=settings.LONG_REQUEST_TIMEOUT)

        if response.success:
            return self._record_result(
                "Get portfolio insight",
                True,
                "Insight generated"
            )
        else:
            return self._record_result(
                "Get portfolio insight",
                False,
                response.error or "Failed (may need API key)"
            )

    # =========================================================================
    # TEST: Sector Insights
    # =========================================================================
    def test_sector_insights(self) -> bool:
        """Test getting sector insights"""
        print_section("TEST: Sector Insights")

        response = self.client.get("/insights/sectors")

        if response.success:
            return self._record_result(
                "Get sector insights",
                True,
                "Insights retrieved"
            )
        else:
            return self._record_result(
                "Get sector insights",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    def run_all_tests(self) -> Tuple[int, int, int]:
        """Run all AI insights tests"""
        print_section("AI INSIGHTS API TESTS")
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("[Note: Some tests may fail if AI API keys are not configured]")

        tests = [
            # Capabilities Tests
            self.test_get_capabilities,

            # Insight Generation Tests
            self.test_generate_insight_post,
            self.test_generate_insight_get,

            # Comparison Tests
            self.test_compare_stocks,

            # News Analysis Tests
            self.test_news_analysis,

            # Question Tests
            self.test_ask_question,

            # Market Overview Tests
            self.test_market_overview,

            # Batch Tests
            self.test_batch_insights,

            # Trending Tests
            self.test_trending_topics,

            # Portfolio Tests
            self.test_portfolio_insight,

            # Sector Tests
            self.test_sector_insights,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                self._record_result(test.__name__, False, str(e))

        passed = sum(1 for r in self.test_results if r["passed"])
        failed = sum(1 for r in self.test_results if not r["passed"])
        total = len(self.test_results)

        print_summary(passed, failed, total)

        return passed, failed, total


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Insights API Tests")
    parser.add_argument("--base-url", default=settings.BASE_URL, help="Base URL for API")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")

    args = parser.parse_args()

    tester = TestAIInsightsAPI(base_url=args.base_url, verbose=not args.quiet)
    passed, failed, total = tester.run_all_tests()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
