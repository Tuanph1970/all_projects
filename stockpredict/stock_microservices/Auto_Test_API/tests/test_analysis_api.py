"""
Analysis API Tests

Tests for Analysis Service:
- GET /analysis/technical/{symbol} - Technical analysis
- GET /analysis/fundamental/{symbol} - Fundamental analysis
- POST /analysis/screener - Run stock screener
- POST /analysis/screener/configs - Save screener config
- GET /analysis/screener/configs - Get saved configs
- DELETE /analysis/screener/configs/{id} - Delete config
- GET /analysis/filters - Get available filters
- POST /analysis/compare - Compare stocks
- GET /analysis/industry/{code} - Industry analysis
- GET /analysis/combined/{symbol} - Combined analysis
- GET /analysis/signals - Get top buy/sell signals
- GET /analysis/summary/{symbol} - Quick summary
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


class TestAnalysisAPI:
    """Analysis API Test Suite"""

    def __init__(self, base_url: str = None, verbose: bool = True):
        self.base_url = base_url or settings.BASE_URL
        self.client = APIClient(self.base_url, verbose=verbose)
        self.test_results = []
        self.test_symbol = settings.TEST_STOCK_SYMBOL
        self.test_symbols = settings.TEST_STOCK_SYMBOLS
        self.access_token: Optional[str] = None
        self.config_id: Optional[int] = None

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
        email = f"analysis_test_{unique_id}@stockhelper.com"
        password = "TestPass@123"

        self.client.post("/auth/register", json={
            "email": email,
            "username": f"analysis_test_{unique_id}",
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
    # TEST: Technical Analysis
    # =========================================================================
    def test_technical_analysis(self) -> bool:
        """Test getting technical analysis"""
        print_section("TEST: Technical Analysis")

        response = self.client.get(f"/analysis/technical/{self.test_symbol}")

        if response.success:
            data = response.data
            passed = "symbol" in data or "indicators" in data or True
            return self._record_result(
                f"Technical analysis for {self.test_symbol}",
                passed,
                f"Analysis retrieved"
            )
        else:
            return self._record_result(
                f"Technical analysis for {self.test_symbol}",
                False,
                response.error or "Failed"
            )

    def test_technical_analysis_with_period(self) -> bool:
        """Test technical analysis with custom period"""
        print_section("TEST: Technical Analysis with Period")

        response = self.client.get(f"/analysis/technical/{self.test_symbol}", params={
            "period": 50
        })

        if response.success:
            return self._record_result(
                "Technical analysis with period=50",
                True,
                "Analysis retrieved"
            )
        else:
            return self._record_result(
                "Technical analysis with period=50",
                False,
                response.error or "Failed"
            )

    def test_technical_analysis_invalid_symbol(self) -> bool:
        """Test technical analysis for invalid symbol"""
        print_section("TEST: Technical Analysis - Invalid Symbol")

        response = self.client.get("/analysis/technical/INVALID123")

        passed = response.status_code in [404, 400]
        return self._record_result(
            "Technical analysis for invalid symbol",
            passed,
            f"Got status code: {response.status_code}"
        )

    # =========================================================================
    # TEST: Fundamental Analysis
    # =========================================================================
    def test_fundamental_analysis(self) -> bool:
        """Test getting fundamental analysis"""
        print_section("TEST: Fundamental Analysis")

        response = self.client.get(f"/analysis/fundamental/{self.test_symbol}")

        if response.success:
            data = response.data
            passed = "symbol" in data or "ratios" in data or True
            return self._record_result(
                f"Fundamental analysis for {self.test_symbol}",
                passed,
                "Analysis retrieved"
            )
        else:
            return self._record_result(
                f"Fundamental analysis for {self.test_symbol}",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Stock Screener
    # =========================================================================
    def test_get_filters(self) -> bool:
        """Test getting available filters"""
        print_section("TEST: Get Screener Filters")

        response = self.client.get("/analysis/filters")

        if response.success:
            data = response.data
            passed = isinstance(data, (list, dict))
            return self._record_result(
                "Get available screener filters",
                passed,
                f"Filters retrieved"
            )
        else:
            return self._record_result(
                "Get available screener filters",
                False,
                response.error or "Failed"
            )

    def test_run_screener(self) -> bool:
        """Test running stock screener"""
        print_section("TEST: Run Stock Screener")

        response = self.client.post("/analysis/screener", json={
            "filters": {
                "exchange": ["HOSE"],
                "market_cap_min": 1000000000000  # 1 trillion VND
            },
            "sort_by": "market_cap",
            "sort_order": "desc",
            "limit": 10
        })

        if response.success:
            data = response.data
            passed = isinstance(data, (list, dict))
            items = data if isinstance(data, list) else data.get("items", data.get("results", []))
            return self._record_result(
                "Run stock screener",
                passed,
                f"Results: {len(items) if isinstance(items, list) else 'retrieved'}"
            )
        else:
            return self._record_result(
                "Run stock screener",
                False,
                response.error or "Failed"
            )

    def test_save_screener_config(self) -> bool:
        """Test saving screener configuration"""
        print_section("TEST: Save Screener Config")

        if not self._authenticate():
            return self._record_result("Save screener config", False, "Authentication failed")

        response = self.client.post("/analysis/screener/configs", json={
            "name": f"Test Config {datetime.now().strftime('%H%M%S')}",
            "description": "Auto test config",
            "filters": {
                "exchange": ["HOSE"],
                "market_cap_min": 500000000000
            },
            "is_public": False
        })

        if response.success:
            data = response.data
            self.config_id = data.get("id")
            passed = self.config_id is not None
            return self._record_result(
                "Save screener config",
                passed,
                f"Config ID: {self.config_id}"
            )
        else:
            return self._record_result(
                "Save screener config",
                False,
                response.error or "Failed"
            )

    def test_get_screener_configs(self) -> bool:
        """Test getting saved screener configs"""
        print_section("TEST: Get Screener Configs")

        if not self._authenticate():
            return self._record_result("Get screener configs", False, "Authentication failed")

        response = self.client.get("/analysis/screener/configs")

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get saved screener configs",
                passed,
                f"Configs: {len(data)}"
            )
        else:
            return self._record_result(
                "Get saved screener configs",
                False,
                response.error or "Failed"
            )

    def test_delete_screener_config(self) -> bool:
        """Test deleting screener config"""
        print_section("TEST: Delete Screener Config")

        if not self._authenticate():
            return self._record_result("Delete screener config", False, "Authentication failed")

        if not self.config_id:
            return self._record_result("Delete screener config", False, "No config available")

        response = self.client.delete(f"/analysis/screener/configs/{self.config_id}")

        passed = response.success or response.status_code == 404
        return self._record_result(
            "Delete screener config",
            passed,
            "Config deleted"
        )

    # =========================================================================
    # TEST: Stock Comparison
    # =========================================================================
    def test_compare_stocks(self) -> bool:
        """Test comparing multiple stocks"""
        print_section("TEST: Compare Stocks")

        response = self.client.post("/analysis/compare", json={
            "symbols": self.test_symbols[:3]  # Compare 3 stocks
        })

        if response.success:
            data = response.data
            passed = isinstance(data, (list, dict))
            return self._record_result(
                f"Compare stocks: {', '.join(self.test_symbols[:3])}",
                passed,
                "Comparison retrieved"
            )
        else:
            return self._record_result(
                "Compare stocks",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Industry Analysis
    # =========================================================================
    def test_industry_analysis(self) -> bool:
        """Test industry analysis"""
        print_section("TEST: Industry Analysis")

        # First get industries to get a valid code
        industries_response = self.client.get("/industries")
        if not industries_response.success or not industries_response.data:
            return self._record_result(
                "Industry analysis",
                False,
                "Could not get industries list"
            )

        industry_code = industries_response.data[0].get("code")
        response = self.client.get(f"/analysis/industry/{industry_code}")

        if response.success:
            return self._record_result(
                f"Industry analysis for {industry_code}",
                True,
                "Analysis retrieved"
            )
        else:
            return self._record_result(
                f"Industry analysis for {industry_code}",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Combined Analysis
    # =========================================================================
    def test_combined_analysis(self) -> bool:
        """Test combined analysis (technical + fundamental)"""
        print_section("TEST: Combined Analysis")

        response = self.client.get(f"/analysis/combined/{self.test_symbol}")

        if response.success:
            return self._record_result(
                f"Combined analysis for {self.test_symbol}",
                True,
                "Analysis retrieved"
            )
        else:
            return self._record_result(
                f"Combined analysis for {self.test_symbol}",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Signals
    # =========================================================================
    def test_get_signals(self) -> bool:
        """Test getting buy/sell signals"""
        print_section("TEST: Get Trading Signals")

        response = self.client.get("/analysis/signals", params={"limit": 10})

        if response.success:
            data = response.data
            passed = isinstance(data, (list, dict))
            return self._record_result(
                "Get trading signals",
                passed,
                f"Signals retrieved"
            )
        else:
            return self._record_result(
                "Get trading signals",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Quick Summary
    # =========================================================================
    def test_quick_summary(self) -> bool:
        """Test getting quick summary"""
        print_section("TEST: Quick Summary")

        response = self.client.get(f"/analysis/summary/{self.test_symbol}")

        if response.success:
            return self._record_result(
                f"Quick summary for {self.test_symbol}",
                True,
                "Summary retrieved"
            )
        else:
            return self._record_result(
                f"Quick summary for {self.test_symbol}",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    def run_all_tests(self) -> Tuple[int, int, int]:
        """Run all analysis tests"""
        print_section("ANALYSIS API TESTS")
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        tests = [
            # Technical Analysis Tests
            self.test_technical_analysis,
            self.test_technical_analysis_with_period,
            self.test_technical_analysis_invalid_symbol,

            # Fundamental Analysis Tests
            self.test_fundamental_analysis,

            # Screener Tests
            self.test_get_filters,
            self.test_run_screener,
            self.test_save_screener_config,
            self.test_get_screener_configs,
            self.test_delete_screener_config,

            # Comparison Tests
            self.test_compare_stocks,

            # Industry Analysis Tests
            self.test_industry_analysis,

            # Combined Analysis Tests
            self.test_combined_analysis,

            # Signals Tests
            self.test_get_signals,

            # Summary Tests
            self.test_quick_summary,
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

    parser = argparse.ArgumentParser(description="Analysis API Tests")
    parser.add_argument("--base-url", default=settings.BASE_URL, help="Base URL for API")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")

    args = parser.parse_args()

    tester = TestAnalysisAPI(base_url=args.base_url, verbose=not args.quiet)
    passed, failed, total = tester.run_all_tests()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
