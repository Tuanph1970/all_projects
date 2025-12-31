#!/usr/bin/env python3
"""
Permission Verification Test
Tests that customer and seller endpoints work correctly with appropriate roles
"""

import requests
import time
import json
from colorama import init, Fore, Style

init(autoreset=True)

BASE_URL = "http://localhost:8002/api/v1"

class PermissionTester:
    def __init__(self):
        self.timestamp = int(time.time())
        self.results = {
            "customer_tests": {"total": 0, "passed": 0, "failed": 0},
            "seller_tests": {"total": 0, "passed": 0, "failed": 0},
            "errors": []
        }

        # User credentials
        self.customer_email = f"customer_perm_{self.timestamp}@example.com"
        self.customer_username = f"customer_perm_{self.timestamp}"
        self.seller_email = f"seller_perm_{self.timestamp}@example.com"
        self.seller_username = f"seller_perm_{self.timestamp}"
        self.password = "Test123!@#"

        # Auth tokens
        self.customer_token = None
        self.customer_id = None
        self.seller_token = None
        self.seller_id = None

        # Test data
        self.category_id = None
        self.product_id = None
        self.order_id = None

    def log(self, message, level="INFO"):
        colors = {
            "INFO": Fore.CYAN,
            "SUCCESS": Fore.GREEN,
            "ERROR": Fore.RED,
            "WARNING": Fore.YELLOW,
            "SECTION": Fore.MAGENTA
        }
        color = colors.get(level, Fore.WHITE)
        print(f"{color}{message}{Style.RESET_ALL}")

    def setup_users(self):
        """Register and login both customer and seller"""
        self.log("\n" + "=" * 80, "SECTION")
        self.log("STEP 1: Setting Up Test Users", "SECTION")
        self.log("=" * 80, "SECTION")

        # Register Customer
        self.log("\nRegistering CUSTOMER account...", "INFO")
        response = requests.post(f"{BASE_URL}/auth/register", json={
            "email": self.customer_email,
            "username": self.customer_username,
            "password": self.password,
            "full_name": "Test Customer",
            "phone_number": "+1234567890",
            "role": "customer"
        })

        if response.status_code in [200, 201]:
            self.customer_id = response.json().get("id")
            self.log(f"✓ Customer registered (ID: {self.customer_id})", "SUCCESS")
        else:
            self.log(f"✗ Customer registration failed: {response.status_code}", "ERROR")
            return False

        # Login Customer
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": self.customer_username,
            "password": self.password
        })

        if response.status_code == 200:
            self.customer_token = response.json().get("access_token")
            self.log("✓ Customer logged in", "SUCCESS")
        else:
            self.log("✗ Customer login failed", "ERROR")
            return False

        # Register Seller
        self.log("\nRegistering SELLER account...", "INFO")
        response = requests.post(f"{BASE_URL}/auth/register", json={
            "email": self.seller_email,
            "username": self.seller_username,
            "password": self.password,
            "full_name": "Test Seller",
            "phone_number": "+9876543210",
            "role": "seller"
        })

        if response.status_code in [200, 201]:
            self.seller_id = response.json().get("id")
            self.log(f"✓ Seller registered (ID: {self.seller_id})", "SUCCESS")
        else:
            self.log(f"✗ Seller registration failed: {response.status_code}", "ERROR")
            return False

        # Login Seller
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": self.seller_username,
            "password": self.password
        })

        if response.status_code == 200:
            self.seller_token = response.json().get("access_token")
            self.log("✓ Seller logged in", "SUCCESS")
        else:
            self.log("✗ Seller login failed", "ERROR")
            return False

        return True

    def test_endpoint(self, name, method, url, token, expected_status, test_type, data=None):
        """Test a single endpoint"""
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return False

            self.results[f"{test_type}_tests"]["total"] += 1

            if response.status_code == expected_status:
                self.log(f"  ✓ {name}: {response.status_code}", "SUCCESS")
                self.results[f"{test_type}_tests"]["passed"] += 1
                return True
            else:
                self.log(f"  ✗ {name}: {response.status_code} (expected {expected_status})", "ERROR")
                self.results[f"{test_type}_tests"]["failed"] += 1
                self.results["errors"].append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "type": test_type
                })
                return False

        except Exception as e:
            self.log(f"  ✗ {name}: Exception - {str(e)}", "ERROR")
            self.results[f"{test_type}_tests"]["failed"] += 1
            self.results["errors"].append({
                "test": name,
                "error": str(e),
                "type": test_type
            })
            return False

    def test_customer_endpoints(self):
        """Test customer-accessible endpoints"""
        self.log("\n" + "=" * 80, "SECTION")
        self.log("STEP 2: Testing CUSTOMER Endpoints", "SECTION")
        self.log("=" * 80, "SECTION")

        # Product browsing
        self.log("\nProduct Browsing:", "INFO")
        self.test_endpoint("List Products", "GET", f"{BASE_URL}/products/",
                          self.customer_token, 200, "customer")
        self.test_endpoint("List Categories", "GET", f"{BASE_URL}/products/categories",
                          self.customer_token, 200, "customer")

        # Cart operations
        self.log("\nCart Operations:", "INFO")
        self.test_endpoint("Get Cart", "GET", f"{BASE_URL}/cart/",
                          self.customer_token, 200, "customer")
        self.test_endpoint("Cart Count", "GET", f"{BASE_URL}/cart/count",
                          self.customer_token, 200, "customer")

        # User profile
        self.log("\nUser Profile:", "INFO")
        self.test_endpoint("Get Profile", "GET", f"{BASE_URL}/users/me/profile",
                          self.customer_token, 200, "customer")

    def test_seller_endpoints(self):
        """Test seller-specific endpoints"""
        self.log("\n" + "=" * 80, "SECTION")
        self.log("STEP 3: Testing SELLER Endpoints", "SECTION")
        self.log("=" * 80, "SECTION")

        # First, create test data as seller
        self.log("\nCreating Test Data:", "INFO")

        # Create category
        response = requests.post(f"{BASE_URL}/products/categories",
                                headers={"Authorization": f"Bearer {self.seller_token}"},
                                json={
                                    "name": "Test Seller Category",
                                    "description": "Category for permission testing"
                                })
        if response.status_code in [200, 201]:
            self.category_id = response.json().get("id")
            self.log(f"  ✓ Category created (ID: {self.category_id})", "SUCCESS")

        # Create product
        if self.category_id:
            response = requests.post(f"{BASE_URL}/products/",
                                    headers={"Authorization": f"Bearer {self.seller_token}"},
                                    json={
                                        "name": "Test Product",
                                        "description": "Product for permission testing",
                                        "price": 99.99,
                                        "quantity_available": 10,
                                        "category_id": self.category_id,
                                        "material": "Ceramic",
                                        "color": "Blue"
                                    })
            if response.status_code in [200, 201]:
                self.product_id = response.json().get("id")
                self.log(f"  ✓ Product created (ID: {self.product_id})", "SUCCESS")

        # Seller Dashboard Tests
        self.log("\nSeller Dashboard:", "INFO")
        self.test_endpoint("Dashboard Overview", "GET",
                          f"{BASE_URL}/seller/dashboard/overview?days=30",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Sales Chart", "GET",
                          f"{BASE_URL}/seller/dashboard/sales-chart?days=30&granularity=day",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Top Products", "GET",
                          f"{BASE_URL}/seller/dashboard/top-products?days=30&metric=revenue&limit=10",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Category Performance", "GET",
                          f"{BASE_URL}/seller/dashboard/category-performance?days=30",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Recent Orders", "GET",
                          f"{BASE_URL}/seller/dashboard/recent-orders?limit=10",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Inventory Alerts", "GET",
                          f"{BASE_URL}/seller/dashboard/inventory-alerts?low_stock_threshold=5",
                          self.seller_token, 200, "seller")

        # Seller Product Management
        self.log("\nSeller Product Management:", "INFO")
        self.test_endpoint("Get Products for Management", "GET",
                          f"{BASE_URL}/seller/products/management?page=1&per_page=20",
                          self.seller_token, 200, "seller")

        # Seller Analytics
        self.log("\nSeller Analytics:", "INFO")
        self.test_endpoint("Analytics Dashboard", "GET",
                          f"{BASE_URL}/seller/analytics/analytics/dashboard?days=30",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Revenue Trends", "GET",
                          f"{BASE_URL}/seller/analytics/analytics/revenue-trends?days=30&granularity=day",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Customer Demographics", "GET",
                          f"{BASE_URL}/seller/analytics/analytics/customer-demographics?days=30",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Performance Metrics", "GET",
                          f"{BASE_URL}/seller/analytics/analytics/performance-metrics?days=30",
                          self.seller_token, 200, "seller")

        # Seller Profile
        self.log("\nSeller Profile:", "INFO")
        self.test_endpoint("Get Seller Profile", "GET",
                          f"{BASE_URL}/seller/profile/profile",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Get Store Info", "GET",
                          f"{BASE_URL}/seller/profile/store",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Get Store Stats", "GET",
                          f"{BASE_URL}/seller/profile/stats",
                          self.seller_token, 200, "seller")

        # Order Fulfillment
        self.log("\nOrder Fulfillment:", "INFO")
        self.test_endpoint("Get Seller Orders", "GET",
                          f"{BASE_URL}/seller/fulfillment/orders?page=1&per_page=20",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Order Statistics", "GET",
                          f"{BASE_URL}/seller/fulfillment/orders/stats/overview?days=30",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Fulfillment Analytics", "GET",
                          f"{BASE_URL}/seller/fulfillment/orders/analytics/fulfillment?days=30",
                          self.seller_token, 200, "seller")
        self.test_endpoint("Pending Returns", "GET",
                          f"{BASE_URL}/seller/fulfillment/orders/returns/pending",
                          self.seller_token, 200, "seller")

    def test_permission_boundaries(self):
        """Test that customer cannot access seller endpoints"""
        self.log("\n" + "=" * 80, "SECTION")
        self.log("STEP 4: Testing Permission Boundaries", "SECTION")
        self.log("=" * 80, "SECTION")

        self.log("\nVerifying customer CANNOT access seller endpoints:", "INFO")

        # These should all return 403 (Forbidden)
        seller_endpoints = [
            ("Dashboard Overview", "GET", f"{BASE_URL}/seller/dashboard/overview"),
            ("Get Seller Profile", "GET", f"{BASE_URL}/seller/profile/profile"),
            ("Get Seller Orders", "GET", f"{BASE_URL}/seller/fulfillment/orders"),
        ]

        for name, method, url in seller_endpoints:
            # Test with customer token (should fail with 403)
            self.test_endpoint(f"[BOUNDARY] Customer accessing {name}", method, url,
                             self.customer_token, 403, "customer")

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 80, "SECTION")
        self.log("TEST SUMMARY", "SECTION")
        self.log("=" * 80, "SECTION")

        customer_total = self.results["customer_tests"]["total"]
        customer_passed = self.results["customer_tests"]["passed"]
        customer_failed = self.results["customer_tests"]["failed"]

        seller_total = self.results["seller_tests"]["total"]
        seller_passed = self.results["seller_tests"]["passed"]
        seller_failed = self.results["seller_tests"]["failed"]

        total_tests = customer_total + seller_total
        total_passed = customer_passed + seller_passed
        total_failed = customer_failed + seller_failed

        self.log(f"\nCustomer Endpoints:", "INFO")
        self.log(f"  Total: {customer_total}", "INFO")
        self.log(f"  Passed: {customer_passed}", "SUCCESS")
        self.log(f"  Failed: {customer_failed}", "ERROR" if customer_failed > 0 else "INFO")
        if customer_total > 0:
            success_rate = (customer_passed / customer_total) * 100
            self.log(f"  Success Rate: {success_rate:.1f}%",
                    "SUCCESS" if success_rate >= 80 else "WARNING")

        self.log(f"\nSeller Endpoints:", "INFO")
        self.log(f"  Total: {seller_total}", "INFO")
        self.log(f"  Passed: {seller_passed}", "SUCCESS")
        self.log(f"  Failed: {seller_failed}", "ERROR" if seller_failed > 0 else "INFO")
        if seller_total > 0:
            success_rate = (seller_passed / seller_total) * 100
            self.log(f"  Success Rate: {success_rate:.1f}%",
                    "SUCCESS" if success_rate >= 80 else "WARNING")

        self.log(f"\nOverall:", "INFO")
        self.log(f"  Total Tests: {total_tests}", "INFO")
        self.log(f"  Passed: {total_passed}", "SUCCESS")
        self.log(f"  Failed: {total_failed}", "ERROR" if total_failed > 0 else "INFO")
        if total_tests > 0:
            success_rate = (total_passed / total_tests) * 100
            self.log(f"  Overall Success Rate: {success_rate:.1f}%",
                    "SUCCESS" if success_rate >= 80 else "WARNING")

        if self.results["errors"]:
            self.log(f"\nFailed Tests:", "ERROR")
            for error in self.results["errors"]:
                test_name = error.get("test", "Unknown")
                test_type = error.get("type", "unknown")
                if "expected" in error:
                    self.log(f"  [{test_type.upper()}] {test_name}: " +
                           f"Expected {error['expected']}, Got {error['actual']}", "ERROR")
                else:
                    self.log(f"  [{test_type.upper()}] {test_name}: {error.get('error', 'Unknown error')}", "ERROR")

    def run(self):
        """Run all tests"""
        if not self.setup_users():
            self.log("\n✗ Setup failed. Aborting tests.", "ERROR")
            return False

        self.test_customer_endpoints()
        self.test_seller_endpoints()
        self.test_permission_boundaries()
        self.print_summary()

        return self.results["customer_tests"]["failed"] == 0 and \
               self.results["seller_tests"]["failed"] == 0

if __name__ == "__main__":
    tester = PermissionTester()
    success = tester.run()
    exit(0 if success else 1)
