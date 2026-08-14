#!/usr/bin/env python3
"""
Mercai - Full Integration Test
Complete end-to-end testing with seller flow: Register → Create Products → Create Orders → Test All Endpoints
"""

import json
import sys
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from colorama import init, Fore, Style
import argparse

# Initialize colorama
init(autoreset=True)


class IntegrationTester:
    """Full integration tester with complete seller workflow"""

    def __init__(self, base_url: str, verbose: bool = False):
        self.base_url = base_url
        self.verbose = verbose
        self.session = requests.Session()
        
        # Auth tokens
        self.seller_token = ""
        self.customer_token = ""
        
        # Test data storage
        self.seller_id = None
        self.customer_id = None
        self.category_id = None
        self.product_ids = []
        self.order_ids = []
        self.cart_item_ids = []
        
        # Test results
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        
        # Generate unique credentials
        timestamp = int(time.time())
        self.seller_email = f"seller_int_{timestamp}@example.com"
        self.seller_username = f"seller_int_{timestamp}"
        self.customer_email = f"customer_int_{timestamp}@example.com"
        self.customer_username = f"customer_int_{timestamp}"
        self.password = "Test123!@#"

    def log(self, message: str, level: str = "INFO"):
        """Print colored log messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": Fore.CYAN,
            "SUCCESS": Fore.GREEN,
            "ERROR": Fore.RED,
            "WARNING": Fore.YELLOW,
            "STEP": Fore.MAGENTA
        }
        color = colors.get(level, Fore.WHITE)
        print(f"{color}[{timestamp}] [{level}] {message}{Style.RESET_ALL}")

    def make_request(self, method: str, url: str, token: str = None, body: Any = None) -> Optional[requests.Response]:
        """Make HTTP request"""
        try:
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            if body:
                headers["Content-Type"] = "application/json"

            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
                timeout=10
            )

            if self.verbose:
                self.log(f"{method} {url} → {response.status_code}", "INFO")

            return response
        except Exception as e:
            self.log(f"Request failed: {str(e)}", "ERROR")
            return None

    def run_integration_tests(self):
        """Run complete integration test suite"""
        self.log("=" * 80, "STEP")
        self.log("MERCAI - FULL INTEGRATION TEST", "STEP")
        self.log("=" * 80, "STEP")
        
        # Phase 1: Setup
        self.log("\n🔧 Phase 1: Setup & Authentication", "STEP")
        if not self.setup_users():
            self.log("Setup failed. Aborting.", "ERROR")
            return
        
        # Phase 2: Category & Product Creation
        self.log("\n📦 Phase 2: Create Category & Products", "STEP")
        if not self.create_test_products():
            self.log("Product creation failed. Continuing with limited tests...", "WARNING")
        
        # Phase 3: Customer Actions
        self.log("\n🛒 Phase 3: Customer Shopping Flow", "STEP")
        if not self.customer_shopping_flow():
            self.log("Shopping flow incomplete. Continuing...", "WARNING")
        
        # Phase 4: Seller Dashboard Tests
        self.log("\n📊 Phase 4: Seller Dashboard & Analytics", "STEP")
        self.test_seller_dashboards()
        
        # Phase 5: Order Management
        self.log("\n📋 Phase 5: Order Fulfillment", "STEP")
        self.test_order_management()
        
        # Print Summary
        self.print_summary()

    def setup_users(self) -> bool:
        """Register and login seller and customer"""
        # Register Seller
        self.log("Registering seller account...", "INFO")
        response = self.make_request("POST", f"{self.base_url}/auth/register", body={
            "email": self.seller_email,
            "username": self.seller_username,
            "password": self.password,
            "full_name": "Test Seller",
            "phone_number": "+1234567890",
            "role": "seller"
        })
        
        if not response or response.status_code not in [200, 201]:
            self.log("Failed to register seller", "ERROR")
            return False
        
        self.seller_id = response.json().get("id")
        self.log(f"✓ Seller registered (ID: {self.seller_id})", "SUCCESS")
        
        # Login Seller
        self.log("Logging in as seller...", "INFO")
        response = self.make_request("POST", f"{self.base_url}/auth/login", body={
            "username": self.seller_username,
            "password": self.password
        })
        
        if not response or response.status_code != 200:
            self.log("Failed to login seller", "ERROR")
            return False
        
        self.seller_token = response.json().get("access_token")
        self.log("✓ Seller logged in", "SUCCESS")
        
        # Register Customer
        self.log("Registering customer account...", "INFO")
        response = self.make_request("POST", f"{self.base_url}/auth/register", body={
            "email": self.customer_email,
            "username": self.customer_username,
            "password": self.password,
            "full_name": "Test Customer",
            "phone_number": "+9876543210",
            "role": "customer"
        })
        
        if not response or response.status_code not in [200, 201]:
            self.log("Failed to register customer", "ERROR")
            return False
        
        self.customer_id = response.json().get("id")
        self.log(f"✓ Customer registered (ID: {self.customer_id})", "SUCCESS")
        
        # Login Customer
        self.log("Logging in as customer...", "INFO")
        response = self.make_request("POST", f"{self.base_url}/auth/login", body={
            "username": self.customer_username,
            "password": self.password
        })
        
        if not response or response.status_code != 200:
            self.log("Failed to login customer", "ERROR")
            return False
        
        self.customer_token = response.json().get("access_token")
        self.log("✓ Customer logged in", "SUCCESS")
        
        return True

    def create_test_products(self) -> bool:
        """Create category and test products"""
        # Create Category
        self.log("Creating product category...", "INFO")
        response = self.make_request("POST", f"{self.base_url}/products/categories", 
                                    token=self.seller_token, body={
            "name": "Test Ceramics",
            "description": "Test category for ceramics",
            "parent_id": None
        })
        
        if not response or response.status_code not in [200, 201]:
            self.log("Failed to create category", "ERROR")
            return False
        
        self.category_id = response.json().get("id")
        self.log(f"✓ Category created (ID: {self.category_id})", "SUCCESS")
        
        # Create 3 test products
        products = [
            {"name": "Ceramic Vase", "price": 45.99, "quantity": 10},
            {"name": "Ceramic Bowl", "price": 25.50, "quantity": 15},
            {"name": "Ceramic Plate Set", "price": 89.99, "quantity": 5}
        ]
        
        for product_data in products:
            response = self.make_request("POST", f"{self.base_url}/products/",
                                        token=self.seller_token, body={
                "name": product_data["name"],
                "description": f"Beautiful {product_data['name'].lower()}",
                "price": product_data["price"],
                "quantity_available": product_data["quantity"],
                "category_id": self.category_id,
                "material": "Clay",
                "color": "Blue",
                "is_featured": False
            })
            
            if response and response.status_code in [200, 201]:
                product_id = response.json().get("id")
                self.product_ids.append(product_id)
                self.log(f"✓ Created {product_data['name']} (ID: {product_id})", "SUCCESS")
            else:
                self.log(f"Failed to create {product_data['name']}", "ERROR")
        
        return len(self.product_ids) > 0

    def customer_shopping_flow(self) -> bool:
        """Simulate customer shopping and order creation"""
        if not self.product_ids:
            self.log("No products available for shopping", "WARNING")
            return False
        
        # Add products to cart
        self.log("Adding products to cart...", "INFO")
        for product_id in self.product_ids[:2]:  # Add first 2 products
            response = self.make_request("POST", f"{self.base_url}/cart/add",
                                        token=self.customer_token, body={
                "product_id": product_id,
                "quantity": 2
            })
            
            if response and response.status_code in [200, 201]:
                self.log(f"✓ Added product {product_id} to cart", "SUCCESS")
            else:
                self.log(f"Failed to add product {product_id} to cart", "ERROR")
        
        time.sleep(0.5)
        
        # Create order from cart
        self.log("Creating order from cart...", "INFO")
        response = self.make_request("POST", f"{self.base_url}/orders/checkout",
                                    token=self.customer_token, body={
            "title": "Home",
            "full_name": "Test Customer",
            "phone_number": "+9876543210",
            "address_line1": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
            "country": "USA",
            "payment_method": "credit_card"
        })
        
        if response and response.status_code in [200, 201]:
            order_id = response.json().get("id")
            self.order_ids.append(order_id)
            self.log(f"✓ Order created (ID: {order_id})", "SUCCESS")
            return True
        else:
            self.log("Failed to create order", "ERROR")
            return False

    def test_seller_dashboards(self):
        """Test all seller dashboard endpoints"""
        endpoints = [
            ("Dashboard Overview", "/seller/dashboard/overview?days=30"),
            ("Sales Chart", "/seller/dashboard/sales-chart?days=30&granularity=day"),
            ("Top Products", "/seller/dashboard/top-products?days=30&metric=revenue&limit=10"),
            ("Category Performance", "/seller/dashboard/category-performance?days=30"),
            ("Recent Orders", "/seller/dashboard/recent-orders?limit=10"),
            ("Inventory Alerts", "/seller/dashboard/inventory-alerts?low_stock_threshold=5"),
            ("Analytics Dashboard", "/seller/analytics/analytics/dashboard?days=30"),
            ("Revenue Trends", "/seller/analytics/analytics/revenue-trends?days=30&granularity=day"),
            ("Seller Profile", "/seller/profile/profile"),
            ("Store Stats", "/seller/profile/stats")
        ]
        
        for name, endpoint in endpoints:
            self.results["total"] += 1
            response = self.make_request("GET", f"{self.base_url}{endpoint}", 
                                        token=self.seller_token)
            
            if response and 200 <= response.status_code < 300:
                self.log(f"✓ {name}", "SUCCESS")
                self.results["passed"] += 1
            else:
                error_msg = f"Status {response.status_code}" if response else "No response"
                if response:
                    try:
                        error_msg += f" - {response.json().get('detail', '')}"
                    except:
                        pass
                self.log(f"✗ {name}: {error_msg}", "ERROR")
                self.results["failed"] += 1
                self.results["errors"].append({"endpoint": name, "error": error_msg})

    def test_order_management(self):
        """Test order fulfillment endpoints"""
        if not self.order_ids:
            self.log("No orders to test", "WARNING")
            return
        
        endpoints = [
            ("Get Seller Orders", "/seller/fulfillment/orders?page=1&per_page=20"),
            ("Order Statistics", "/seller/fulfillment/orders/stats/overview?days=30"),
            ("Pending Returns", "/seller/fulfillment/orders/returns/pending")
        ]
        
        for name, endpoint in endpoints:
            self.results["total"] += 1
            response = self.make_request("GET", f"{self.base_url}{endpoint}",
                                        token=self.seller_token)
            
            if response and 200 <= response.status_code < 300:
                self.log(f"✓ {name}", "SUCCESS")
                self.results["passed"] += 1
            else:
                error_msg = f"Status {response.status_code}" if response else "No response"
                self.log(f"✗ {name}: {error_msg}", "ERROR")
                self.results["failed"] += 1
                self.results["errors"].append({"endpoint": name, "error": error_msg})

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 80, "STEP")
        self.log("INTEGRATION TEST SUMMARY", "STEP")
        self.log("=" * 80, "STEP")
        
        self.log(f"\nTest Data Created:", "INFO")
        self.log(f"  Seller ID: {self.seller_id}", "INFO")
        self.log(f"  Customer ID: {self.customer_id}", "INFO")
        self.log(f"  Category ID: {self.category_id}", "INFO")
        self.log(f"  Products: {len(self.product_ids)} created", "INFO")
        self.log(f"  Orders: {len(self.order_ids)} created", "INFO")
        
        self.log(f"\nTest Results:", "INFO")
        self.log(f"  Total Tests: {self.results['total']}", "INFO")
        self.log(f"  Passed: {self.results['passed']}", "SUCCESS")
        self.log(f"  Failed: {self.results['failed']}", "ERROR" if self.results['failed'] > 0 else "INFO")
        
        if self.results["total"] > 0:
            success_rate = (self.results["passed"] / self.results["total"]) * 100
            self.log(f"  Success Rate: {success_rate:.1f}%",
                    "SUCCESS" if success_rate >= 80 else "WARNING")
        
        if self.results["errors"]:
            self.log("\nErrors:", "ERROR")
            for error in self.results["errors"]:
                self.log(f"  {error['endpoint']}: {error['error']}", "ERROR")


def main():
    parser = argparse.ArgumentParser(description="Mercai - Full Integration Test")
    parser.add_argument("--base-url", default="http://112.213.91.103:8002/api/v1")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    
    tester = IntegrationTester(args.base_url, args.verbose)
    tester.run_integration_tests()
    
    sys.exit(0 if tester.results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
