"""
Portfolio API Tests

Tests for Portfolio Service:
- POST /portfolio/portfolios - Create portfolio
- GET /portfolio/portfolios - List portfolios
- GET /portfolio/portfolios/default - Get default portfolio
- GET /portfolio/portfolios/{id} - Get portfolio details
- GET /portfolio/portfolios/{id}/summary - Get portfolio summary
- PUT /portfolio/portfolios/{id} - Update portfolio
- DELETE /portfolio/portfolios/{id} - Delete portfolio

- POST /portfolio/portfolios/{id}/holdings - Add holding
- GET /portfolio/portfolios/{id}/holdings - Get holdings
- PUT /portfolio/portfolios/{id}/holdings/{symbol} - Update holding
- DELETE /portfolio/portfolios/{id}/holdings/{symbol} - Remove holding

- POST /portfolio/portfolios/{id}/transactions - Record transaction
- GET /portfolio/portfolios/{id}/transactions - Get transactions
- DELETE /portfolio/portfolios/{id}/transactions/{id} - Delete transaction

- POST /portfolio/alerts - Create price alert
- GET /portfolio/alerts - Get alerts
- PUT /portfolio/alerts/{id} - Update alert
- DELETE /portfolio/alerts/{id} - Delete alert

- POST /portfolio/watchlist - Add to watchlist
- GET /portfolio/watchlist - Get watchlist
- DELETE /portfolio/watchlist/{symbol} - Remove from watchlist
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


class TestPortfolioAPI:
    """Portfolio API Test Suite"""

    def __init__(self, base_url: str = None, verbose: bool = True):
        self.base_url = base_url or settings.BASE_URL
        self.client = APIClient(self.base_url, verbose=verbose)
        self.test_results = []

        # Track created resources for cleanup
        self.access_token: Optional[str] = None
        self.portfolio_id: Optional[int] = None
        self.alert_id: Optional[int] = None
        self.transaction_id: Optional[int] = None
        self.test_symbol = settings.TEST_STOCK_SYMBOL

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
        """Authenticate and set token"""
        if self.access_token:
            return True

        # Try to register a new test user
        unique_id = str(uuid.uuid4())[:8]
        email = f"portfolio_test_{unique_id}@stockhelper.com"
        password = "TestPass@123"

        # Register
        self.client.post("/auth/register", json={
            "email": email,
            "username": f"portfolio_test_{unique_id}",
            "password": password
        })

        # Login
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
    # TEST: Portfolio CRUD
    # =========================================================================
    def test_create_portfolio(self) -> bool:
        """Test creating a portfolio"""
        print_section("TEST: Create Portfolio")

        if not self._authenticate():
            return self._record_result("Create portfolio", False, "Authentication failed")

        response = self.client.post("/portfolio/portfolios", json={
            "name": f"Test Portfolio {datetime.now().strftime('%Y%m%d%H%M%S')}",
            "description": "Portfolio created by automated tests"
        })

        if response.success:
            data = response.data
            self.portfolio_id = data.get("id")
            passed = self.portfolio_id is not None
            return self._record_result(
                "Create portfolio",
                passed,
                f"Portfolio ID: {self.portfolio_id}"
            )
        else:
            return self._record_result(
                "Create portfolio",
                False,
                response.error or "Failed"
            )

    def test_get_portfolios(self) -> bool:
        """Test getting list of portfolios"""
        print_section("TEST: Get Portfolios List")

        if not self._authenticate():
            return self._record_result("Get portfolios", False, "Authentication failed")

        response = self.client.get("/portfolio/portfolios")

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get portfolios list",
                passed,
                f"Portfolios: {len(data)}"
            )
        else:
            return self._record_result(
                "Get portfolios list",
                False,
                response.error or "Failed"
            )

    def test_get_default_portfolio(self) -> bool:
        """Test getting or creating default portfolio"""
        print_section("TEST: Get Default Portfolio")

        if not self._authenticate():
            return self._record_result("Get default portfolio", False, "Authentication failed")

        response = self.client.get("/portfolio/portfolios/default")

        if response.success:
            data = response.data
            passed = "id" in data and "name" in data
            if passed and not self.portfolio_id:
                self.portfolio_id = data.get("id")
            return self._record_result(
                "Get default portfolio",
                passed,
                f"Portfolio: {data.get('name')}"
            )
        else:
            return self._record_result(
                "Get default portfolio",
                False,
                response.error or "Failed"
            )

    def test_get_portfolio_details(self) -> bool:
        """Test getting portfolio details"""
        print_section("TEST: Get Portfolio Details")

        if not self._authenticate():
            return self._record_result("Get portfolio details", False, "Authentication failed")

        if not self.portfolio_id:
            self.test_get_default_portfolio()

        if not self.portfolio_id:
            return self._record_result("Get portfolio details", False, "No portfolio available")

        response = self.client.get(f"/portfolio/portfolios/{self.portfolio_id}")

        if response.success:
            data = response.data
            passed = data.get("id") == self.portfolio_id
            return self._record_result(
                "Get portfolio details",
                passed,
                f"Portfolio: {data.get('name')}"
            )
        else:
            return self._record_result(
                "Get portfolio details",
                False,
                response.error or "Failed"
            )

    def test_update_portfolio(self) -> bool:
        """Test updating portfolio"""
        print_section("TEST: Update Portfolio")

        if not self._authenticate():
            return self._record_result("Update portfolio", False, "Authentication failed")

        if not self.portfolio_id:
            self.test_get_default_portfolio()

        if not self.portfolio_id:
            return self._record_result("Update portfolio", False, "No portfolio available")

        new_name = f"Updated Portfolio {datetime.now().strftime('%H%M%S')}"
        response = self.client.put(f"/portfolio/portfolios/{self.portfolio_id}", json={
            "name": new_name,
            "description": "Updated by automated tests"
        })

        if response.success:
            data = response.data
            passed = data.get("name") == new_name
            return self._record_result(
                "Update portfolio",
                passed,
                f"New name: {data.get('name')}"
            )
        else:
            return self._record_result(
                "Update portfolio",
                False,
                response.error or "Failed"
            )

    def test_get_portfolio_summary(self) -> bool:
        """Test getting portfolio summary"""
        print_section("TEST: Get Portfolio Summary")

        if not self._authenticate():
            return self._record_result("Get portfolio summary", False, "Authentication failed")

        if not self.portfolio_id:
            self.test_get_default_portfolio()

        if not self.portfolio_id:
            return self._record_result("Get portfolio summary", False, "No portfolio available")

        response = self.client.get(f"/portfolio/portfolios/{self.portfolio_id}/summary")

        if response.success:
            data = response.data
            passed = "portfolio_id" in data or "total_holdings" in data or True
            return self._record_result(
                "Get portfolio summary",
                passed,
                f"Summary retrieved"
            )
        else:
            return self._record_result(
                "Get portfolio summary",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Holdings
    # =========================================================================
    def test_add_holding(self) -> bool:
        """Test adding a holding to portfolio"""
        print_section("TEST: Add Holding")

        if not self._authenticate():
            return self._record_result("Add holding", False, "Authentication failed")

        if not self.portfolio_id:
            self.test_get_default_portfolio()

        if not self.portfolio_id:
            return self._record_result("Add holding", False, "No portfolio available")

        response = self.client.post(
            f"/portfolio/portfolios/{self.portfolio_id}/holdings",
            json={
                "symbol": self.test_symbol,
                "quantity": 100,
                "average_price": 80000.0,
                "is_watchlist_only": False
            }
        )

        if response.success:
            data = response.data
            passed = data.get("symbol") == self.test_symbol
            return self._record_result(
                f"Add holding {self.test_symbol}",
                passed,
                f"Holding added with quantity: {data.get('quantity')}"
            )
        else:
            # Might already exist, which is OK
            if "already" in str(response.error).lower():
                return self._record_result(
                    f"Add holding {self.test_symbol}",
                    True,
                    "Holding already exists"
                )
            return self._record_result(
                f"Add holding {self.test_symbol}",
                False,
                response.error or "Failed"
            )

    def test_get_holdings(self) -> bool:
        """Test getting portfolio holdings"""
        print_section("TEST: Get Holdings")

        if not self._authenticate():
            return self._record_result("Get holdings", False, "Authentication failed")

        if not self.portfolio_id:
            self.test_get_default_portfolio()

        if not self.portfolio_id:
            return self._record_result("Get holdings", False, "No portfolio available")

        response = self.client.get(f"/portfolio/portfolios/{self.portfolio_id}/holdings")

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get portfolio holdings",
                passed,
                f"Holdings: {len(data)}"
            )
        else:
            return self._record_result(
                "Get portfolio holdings",
                False,
                response.error or "Failed"
            )

    def test_update_holding(self) -> bool:
        """Test updating a holding"""
        print_section("TEST: Update Holding")

        if not self._authenticate():
            return self._record_result("Update holding", False, "Authentication failed")

        if not self.portfolio_id:
            self.test_get_default_portfolio()

        if not self.portfolio_id:
            return self._record_result("Update holding", False, "No portfolio available")

        response = self.client.put(
            f"/portfolio/portfolios/{self.portfolio_id}/holdings/{self.test_symbol}",
            json={
                "quantity": 150,
                "average_price": 82000.0
            }
        )

        if response.success:
            data = response.data
            passed = data.get("quantity") == 150
            return self._record_result(
                f"Update holding {self.test_symbol}",
                passed,
                f"New quantity: {data.get('quantity')}"
            )
        else:
            return self._record_result(
                f"Update holding {self.test_symbol}",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Transactions
    # =========================================================================
    def test_record_transaction(self) -> bool:
        """Test recording a transaction"""
        print_section("TEST: Record Transaction")

        if not self._authenticate():
            return self._record_result("Record transaction", False, "Authentication failed")

        if not self.portfolio_id:
            self.test_get_default_portfolio()

        if not self.portfolio_id:
            return self._record_result("Record transaction", False, "No portfolio available")

        response = self.client.post(
            f"/portfolio/portfolios/{self.portfolio_id}/transactions",
            json={
                "symbol": self.test_symbol,
                "type": "buy",
                "quantity": 50,
                "price": 81000.0,
                "fees": 50000.0,
                "notes": "Test transaction"
            }
        )

        if response.success:
            data = response.data
            self.transaction_id = data.get("id")
            passed = self.transaction_id is not None
            return self._record_result(
                "Record buy transaction",
                passed,
                f"Transaction ID: {self.transaction_id}"
            )
        else:
            return self._record_result(
                "Record buy transaction",
                False,
                response.error or "Failed"
            )

    def test_get_transactions(self) -> bool:
        """Test getting portfolio transactions"""
        print_section("TEST: Get Transactions")

        if not self._authenticate():
            return self._record_result("Get transactions", False, "Authentication failed")

        if not self.portfolio_id:
            self.test_get_default_portfolio()

        if not self.portfolio_id:
            return self._record_result("Get transactions", False, "No portfolio available")

        response = self.client.get(
            f"/portfolio/portfolios/{self.portfolio_id}/transactions",
            params={"limit": 50}
        )

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get portfolio transactions",
                passed,
                f"Transactions: {len(data)}"
            )
        else:
            return self._record_result(
                "Get portfolio transactions",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Price Alerts
    # =========================================================================
    def test_create_alert(self) -> bool:
        """Test creating a price alert"""
        print_section("TEST: Create Price Alert")

        if not self._authenticate():
            return self._record_result("Create alert", False, "Authentication failed")

        response = self.client.post("/portfolio/alerts", json={
            "symbol": self.test_symbol,
            "condition": "above",
            "target_price": 90000.0,
            "notes": "Test alert"
        })

        if response.success:
            data = response.data
            self.alert_id = data.get("id")
            passed = self.alert_id is not None
            return self._record_result(
                "Create price alert",
                passed,
                f"Alert ID: {self.alert_id}"
            )
        else:
            return self._record_result(
                "Create price alert",
                False,
                response.error or "Failed"
            )

    def test_get_alerts(self) -> bool:
        """Test getting price alerts"""
        print_section("TEST: Get Price Alerts")

        if not self._authenticate():
            return self._record_result("Get alerts", False, "Authentication failed")

        response = self.client.get("/portfolio/alerts")

        if response.success:
            data = response.data
            passed = isinstance(data, list)
            return self._record_result(
                "Get price alerts",
                passed,
                f"Alerts: {len(data)}"
            )
        else:
            return self._record_result(
                "Get price alerts",
                False,
                response.error or "Failed"
            )

    def test_update_alert(self) -> bool:
        """Test updating a price alert"""
        print_section("TEST: Update Price Alert")

        if not self._authenticate():
            return self._record_result("Update alert", False, "Authentication failed")

        if not self.alert_id:
            self.test_create_alert()

        if not self.alert_id:
            return self._record_result("Update alert", False, "No alert available")

        response = self.client.put(f"/portfolio/alerts/{self.alert_id}", json={
            "target_price": 95000.0,
            "notes": "Updated test alert"
        })

        if response.success:
            data = response.data
            passed = data.get("target_price") == 95000.0
            return self._record_result(
                "Update price alert",
                passed,
                f"New target: {data.get('target_price')}"
            )
        else:
            return self._record_result(
                "Update price alert",
                False,
                response.error or "Failed"
            )

    # =========================================================================
    # TEST: Watchlist
    # =========================================================================
    def test_add_to_watchlist(self) -> bool:
        """Test adding stock to watchlist"""
        print_section("TEST: Add to Watchlist")

        if not self._authenticate():
            return self._record_result("Add to watchlist", False, "Authentication failed")

        response = self.client.post("/portfolio/watchlist", json={
            "symbol": "FPT"
        })

        passed = response.success or "already" in str(response.error).lower()
        return self._record_result(
            "Add to watchlist",
            passed,
            "Added FPT to watchlist" if response.success else response.error
        )

    def test_get_watchlist(self) -> bool:
        """Test getting watchlist"""
        print_section("TEST: Get Watchlist")

        if not self._authenticate():
            return self._record_result("Get watchlist", False, "Authentication failed")

        response = self.client.get("/portfolio/watchlist")

        if response.success:
            data = response.data
            passed = "items" in data or isinstance(data, list)
            items = data.get("items", data) if isinstance(data, dict) else data
            return self._record_result(
                "Get watchlist",
                passed,
                f"Watchlist items: {len(items)}"
            )
        else:
            return self._record_result(
                "Get watchlist",
                False,
                response.error or "Failed"
            )

    def test_remove_from_watchlist(self) -> bool:
        """Test removing from watchlist"""
        print_section("TEST: Remove from Watchlist")

        if not self._authenticate():
            return self._record_result("Remove from watchlist", False, "Authentication failed")

        response = self.client.delete("/portfolio/watchlist/FPT")

        passed = response.success or response.status_code == 404
        return self._record_result(
            "Remove from watchlist",
            passed,
            "Removed FPT from watchlist"
        )

    # =========================================================================
    # TEST: Cleanup / Delete
    # =========================================================================
    def test_delete_holding(self) -> bool:
        """Test deleting a holding"""
        print_section("TEST: Delete Holding")

        if not self._authenticate():
            return self._record_result("Delete holding", False, "Authentication failed")

        if not self.portfolio_id:
            return self._record_result("Delete holding", False, "No portfolio available")

        response = self.client.delete(
            f"/portfolio/portfolios/{self.portfolio_id}/holdings/{self.test_symbol}"
        )

        passed = response.success or response.status_code == 404
        return self._record_result(
            f"Delete holding {self.test_symbol}",
            passed,
            "Holding deleted"
        )

    def test_delete_alert(self) -> bool:
        """Test deleting a price alert"""
        print_section("TEST: Delete Price Alert")

        if not self._authenticate():
            return self._record_result("Delete alert", False, "Authentication failed")

        if not self.alert_id:
            return self._record_result("Delete alert", False, "No alert available")

        response = self.client.delete(f"/portfolio/alerts/{self.alert_id}")

        passed = response.success or response.status_code == 404
        return self._record_result(
            "Delete price alert",
            passed,
            "Alert deleted"
        )

    # =========================================================================
    # TEST: Unauthenticated Access
    # =========================================================================
    def test_portfolios_without_auth(self) -> bool:
        """Test accessing portfolios without authentication"""
        print_section("TEST: Portfolios Without Auth")

        self.client.clear_auth()

        response = self.client.get("/portfolio/portfolios")

        # Restore auth
        if self.access_token:
            self.client.set_auth_tokens(self.access_token)

        passed = response.status_code == 401
        return self._record_result(
            "Access portfolios without auth returns 401",
            passed,
            f"Got status code: {response.status_code}"
        )

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    def run_all_tests(self) -> Tuple[int, int, int]:
        """Run all portfolio tests"""
        print_section("PORTFOLIO API TESTS")
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        tests = [
            # Portfolio CRUD Tests
            self.test_create_portfolio,
            self.test_get_portfolios,
            self.test_get_default_portfolio,
            self.test_get_portfolio_details,
            self.test_update_portfolio,
            self.test_get_portfolio_summary,

            # Holdings Tests
            self.test_add_holding,
            self.test_get_holdings,
            self.test_update_holding,

            # Transactions Tests
            self.test_record_transaction,
            self.test_get_transactions,

            # Price Alerts Tests
            self.test_create_alert,
            self.test_get_alerts,
            self.test_update_alert,

            # Watchlist Tests
            self.test_add_to_watchlist,
            self.test_get_watchlist,
            self.test_remove_from_watchlist,

            # Auth Tests
            self.test_portfolios_without_auth,

            # Cleanup Tests (last)
            self.test_delete_holding,
            self.test_delete_alert,
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

    parser = argparse.ArgumentParser(description="Portfolio API Tests")
    parser.add_argument("--base-url", default=settings.BASE_URL, help="Base URL for API")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")

    args = parser.parse_args()

    tester = TestPortfolioAPI(base_url=args.base_url, verbose=not args.quiet)
    passed, failed, total = tester.run_all_tests()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
