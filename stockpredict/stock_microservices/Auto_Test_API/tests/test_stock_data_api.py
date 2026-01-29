"""
Stock Data API Tests

Tests for Stock Data Service:
- GET /companies - List companies (paginated)
- GET /companies/all - All companies
- GET /stocks/{symbol} - Get company details
- GET /stocks/{symbol}/history - Historical OHLCV data
- GET /stocks/search - Search companies
- GET /companies/top-gainers - Top gainers
- GET /companies/top-losers - Top losers
- GET /companies/top-actives - Most active stocks
- GET /industries - All industries
- GET /industries/{id}/companies - Companies by industry
- GET /market/indices - Market indices
- GET /market/indices/latest - Latest indices
- GET /priceboards - Price board data
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from utils.http_client import (
    APIClient,
    print_test_result,
    print_section,
    print_summary,
)


class TestStockDataAPI:
    """Stock Data API Test Suite"""

    def __init__(self, base_url: str = None, verbose: bool = True):
        self.base_url = base_url or settings.BASE_URL
        self.client = APIClient(self.base_url, verbose=verbose)
        self.test_results = []
        self.test_symbol = settings.TEST_STOCK_SYMBOL  # VNM

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

    # =========================================================================
    # TEST: Companies List
    # =========================================================================
    def test_get_companies_paginated(self) -> bool:
        """Test getting paginated list of companies"""
        print_section("TEST: Get Companies - Paginated")

        response = self.client.get("/companies", params={
            "page": 1,
            "page_size": 10
        })

        if response.success:
            data = response.data
            passed = (
                "items" in data and
                isinstance(data["items"], list) and
                "total" in data and
                len(data["items"]) <= 10
            )
            return self._record_result(
                "Get paginated companies list",
                passed,
                f"Total: {data.get('total')}, Page items: {len(data.get('items', []))}"
            )
        else:
            return self._record_result(
                "Get paginated companies list",
                False,
                response.error or "Failed"
            )

    def test_get_companies_all(self) -> bool:
        """Test getting all companies without pagination"""
        print_section("TEST: Get Companies - All")

        response = self.client.get("/companies/all")

        if response.success:
            data = response.data
            passed = isinstance(data, list) and len(data) > 0
            return self._record_result(
                "Get all companies list",
                passed,
                f"Total companies: {len(data)}"
            )
        else:
            return self._record_result(
                "Get all companies list",
                False,
                response.error or "Failed"
            )

    def test_get_companies_by_exchange(self) -> bool:
        """Test filtering companies by exchange"""
        print_section("TEST: Get Companies - By Exchange")

        response = self.client.get("/companies", params={
            "exchange": "HOSE",
            "page_size": 20
        })

        if response.success:
            data = response.data
            items = data.get("items", [])
            all_hose = all(item.get("exchange") == "HOSE" for item in items)
            passed = len(items) > 0 and all_hose
            return self._record_result(
                "Filter companies by exchange",
                passed,
                f"Items: {len(items)}, All HOSE: {all_hose}"
            )
        else:
            return self._record_result(
                "Filter companies by exchange",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Company Details
    # =========================================================================
    def test_get_stock_details(self) -> bool:
        """Test getting company details by symbol"""
        print_section("TEST: Get Stock Details")

        response = self.client.get(f"/stocks/{self.test_symbol}")

        if response.success:
            data = response.data
            passed = (
                data.get("symbol") == self.test_symbol and
                "name" in data and
                "exchange" in data
            )
            return self._record_result(
                f"Get stock details for {self.test_symbol}",
                passed,
                f"Name: {data.get('name')}"
            )
        else:
            return self._record_result(
                f"Get stock details for {self.test_symbol}",
                False,
                response.error or "Failed"
            )

    def test_get_stock_details_invalid(self) -> bool:
        """Test getting details for invalid symbol"""
        print_section("TEST: Get Stock Details - Invalid Symbol")

        response = self.client.get("/stocks/INVALID123")

        passed = response.status_code == 404
        return self._record_result(
            "Get invalid stock returns 404",
            passed,
            f"Got status code: {response.status_code}"
        )

    # =========================================================================
    # TEST: Historical Data
    # =========================================================================
    def test_get_stock_history(self) -> bool:
        """Test getting stock historical data"""
        print_section("TEST: Get Stock History")

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        response = self.client.get(f"/stocks/{self.test_symbol}/history", params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })

        if response.success:
            data = response.data
            passed = (
                data.get("symbol") == self.test_symbol and
                "data" in data and
                isinstance(data["data"], list)
            )
            return self._record_result(
                f"Get historical data for {self.test_symbol}",
                passed,
                f"Data points: {len(data.get('data', []))}"
            )
        else:
            return self._record_result(
                f"Get historical data for {self.test_symbol}",
                False,
                response.error or "Failed"
            )

    def test_get_stock_history_no_dates(self) -> bool:
        """Test getting stock history without date params"""
        print_section("TEST: Get Stock History - No Date Params")

        response = self.client.get(f"/stocks/{self.test_symbol}/history")

        if response.success:
            data = response.data
            passed = "data" in data
            return self._record_result(
                "Get historical data without date params",
                passed,
                f"Data points: {len(data.get('data', []))}"
            )
        else:
            return self._record_result(
                "Get historical data without date params",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Search
    # =========================================================================
    def test_search_companies(self) -> bool:
        """Test searching companies"""
        print_section("TEST: Search Companies")

        response = self.client.get("/stocks/search", params={
            "q": "Vietnam",
            "limit": 10
        })

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Search companies by name",
                passed,
                f"Results: {len(data)}"
            )
        else:
            return self._record_result(
                "Search companies by name",
                False,
                response.error or "Failed"
            )

    def test_search_by_symbol(self) -> bool:
        """Test searching by symbol"""
        print_section("TEST: Search By Symbol")

        response = self.client.get("/stocks/search", params={
            "q": "VNM",
            "limit": 5
        })

        if response.success:
            data = response.data
            has_vnm = any(item.get("symbol") == "VNM" for item in data)
            passed = len(data) > 0 and has_vnm
            return self._record_result(
                "Search by symbol finds VNM",
                passed,
                f"Found VNM: {has_vnm}"
            )
        else:
            return self._record_result(
                "Search by symbol",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Top Movers
    # =========================================================================
    def test_get_top_gainers(self) -> bool:
        """Test getting top gainers"""
        print_section("TEST: Get Top Gainers")

        response = self.client.get("/companies/top-gainers", params={"limit": 10})

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get top gainers",
                passed,
                f"Results: {len(data)}"
            )
        else:
            return self._record_result(
                "Get top gainers",
                False,
                response.error or "Failed"
            )

    def test_get_top_losers(self) -> bool:
        """Test getting top losers"""
        print_section("TEST: Get Top Losers")

        response = self.client.get("/companies/top-losers", params={"limit": 10})

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get top losers",
                passed,
                f"Results: {len(data)}"
            )
        else:
            return self._record_result(
                "Get top losers",
                False,
                response.error or "Failed"
            )

    def test_get_top_actives(self) -> bool:
        """Test getting most active stocks"""
        print_section("TEST: Get Most Active Stocks")

        response = self.client.get("/companies/top-actives", params={"limit": 10})

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get most active stocks",
                passed,
                f"Results: {len(data)}"
            )
        else:
            return self._record_result(
                "Get most active stocks",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Industries
    # =========================================================================
    def test_get_industries(self) -> bool:
        """Test getting all industries"""
        print_section("TEST: Get Industries")

        response = self.client.get("/industries")

        if response.success:
            data = response.data
            passed = isinstance(data, list) and len(data) > 0
            return self._record_result(
                "Get all industries",
                passed,
                f"Industries: {len(data)}"
            )
        else:
            return self._record_result(
                "Get all industries",
                False,
                response.error or "Failed"
            )

    def test_get_companies_by_industry(self) -> bool:
        """Test getting companies by industry"""
        print_section("TEST: Get Companies by Industry")

        # First get industries
        industries_response = self.client.get("/industries")
        if not industries_response.success or not industries_response.data:
            return self._record_result(
                "Get companies by industry",
                False,
                "Could not get industries list"
            )

        industry_id = industries_response.data[0].get("id")
        response = self.client.get(f"/industries/{industry_id}/companies")

        if response.success:
            data = response.data
            passed = "items" in data
            return self._record_result(
                f"Get companies for industry {industry_id}",
                passed,
                f"Companies: {len(data.get('items', []))}"
            )
        else:
            return self._record_result(
                f"Get companies for industry {industry_id}",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Market Indices
    # =========================================================================
    def test_get_market_indices(self) -> bool:
        """Test getting market indices"""
        print_section("TEST: Get Market Indices")

        response = self.client.get("/market/indices")

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get market indices",
                passed,
                f"Indices: {len(data)}"
            )
        else:
            return self._record_result(
                "Get market indices",
                False,
                response.error or "Failed"
            )

    def test_get_latest_indices(self) -> bool:
        """Test getting latest market indices"""
        print_section("TEST: Get Latest Market Indices")

        response = self.client.get("/market/indices/latest")

        if response.success:
            data = response.data
            passed = isinstance(data, list) or isinstance(data, dict)
            return self._record_result(
                "Get latest market indices",
                passed,
                f"Response type: {type(data).__name__}"
            )
        else:
            return self._record_result(
                "Get latest market indices",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Priceboard
    # =========================================================================
    def test_get_priceboard(self) -> bool:
        """Test getting price board data"""
        print_section("TEST: Get Price Board")

        response = self.client.get("/priceboards", params={"group": "VN30"})

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get VN30 price board",
                passed,
                f"Stocks: {len(data)}"
            )
        else:
            return self._record_result(
                "Get VN30 price board",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    def run_all_tests(self) -> Tuple[int, int, int]:
        """Run all stock data tests"""
        print_section("STOCK DATA API TESTS")
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        tests = [
            # Companies Tests
            self.test_get_companies_paginated,
            self.test_get_companies_all,
            self.test_get_companies_by_exchange,

            # Stock Details Tests
            self.test_get_stock_details,
            self.test_get_stock_details_invalid,

            # Historical Data Tests
            self.test_get_stock_history,
            self.test_get_stock_history_no_dates,

            # Search Tests
            self.test_search_companies,
            self.test_search_by_symbol,

            # Top Movers Tests
            self.test_get_top_gainers,
            self.test_get_top_losers,
            self.test_get_top_actives,

            # Industries Tests
            self.test_get_industries,
            self.test_get_companies_by_industry,

            # Market Indices Tests
            self.test_get_market_indices,
            self.test_get_latest_indices,

            # Priceboard Tests
            self.test_get_priceboard,
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

    parser = argparse.ArgumentParser(description="Stock Data API Tests")
    parser.add_argument(
        "--base-url",
        default=settings.BASE_URL,
        help="Base URL for API"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )

    args = parser.parse_args()

    tester = TestStockDataAPI(base_url=args.base_url, verbose=not args.quiet)
    passed, failed, total = tester.run_all_tests()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
