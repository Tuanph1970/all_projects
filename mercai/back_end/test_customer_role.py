#!/usr/bin/env python3
"""
Mercai API Test Suite - Customer Role
Automated testing for customer-accessible API endpoints only
This test suite uses the pre-seeded customer_a account
"""

import json
import sys
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from colorama import init, Fore, Style
import argparse

# Initialize colorama for colored terminal output
init(autoreset=True)


class APITesterCustomer:
    """Automated API testing framework for Customer role"""

    def __init__(self, base_url: str, verbose: bool = False):
        self.base_url = base_url
        self.verbose = verbose
        self.auth_token = ""
        self.refresh_token = ""
        self.session = requests.Session()
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        self.test_data = {
            "user_id": 100,  # Pre-seeded customer_a user ID
            "product_id": 1000,  # Pre-seeded product ID
            "category_id": 100,  # Pre-seeded category ID
            "address_id": None,
            "order_id": 2000,  # Pre-seeded order ID
            "review_id": None,
            "cart_item_id": None,
            "chat_room_id": None,
            "image_id": None
        }
        # Use pre-seeded customer account
        self.test_email = "customer_a@test.com"
        self.test_username = "customer_a"
        self.test_password = "Mysql_2025!"
        self.email_verified = True  # Pre-seeded account is already verified
        self.verification_token = None

        # Categories to skip (seller-specific)
        self.skip_categories = [
            "Seller Dashboard",
            "Seller Product Management",
            "Order Fulfillment",
            "Seller Analytics",
            "Seller Profile",
            "Store Theme Management",
            "Store Analytics & Media"
        ]

    def log(self, message: str, level: str = "INFO"):
        """Print colored log messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": Fore.CYAN,
            "SUCCESS": Fore.GREEN,
            "ERROR": Fore.RED,
            "WARNING": Fore.YELLOW,
            "SKIP": Fore.MAGENTA
        }
        color = colors.get(level, Fore.WHITE)
        print(f"{color}[{timestamp}] [{level}] {message}{Style.RESET_ALL}")

    def make_request(self, method: str, url: str, headers: Dict = None,
                     body: Any = None, params: Dict = None) -> Optional[requests.Response]:
        """Make HTTP request with error handling"""
        try:
            # Initialize headers if None
            if headers is None:
                headers = {}

            # Add auth token if available
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            # Parse body if it's a string
            if isinstance(body, str) and body:
                try:
                    body = json.loads(body)
                    if self.verbose:
                        self.log(f"Parsed body type: {type(body)}", "INFO")
                except json.JSONDecodeError as e:
                    if self.verbose:
                        self.log(f"JSON decode error: {e}", "ERROR")
                    pass

            # Make request
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
                params=params,
                timeout=10
            )

            if self.verbose:
                self.log(f"{method} {url} → {response.status_code}", "INFO")
                if response.status_code == 401:
                    self.log(f"401 Response: {response.text[:200]}", "ERROR")

            return response

        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {str(e)}", "ERROR")
            return None

    def replace_variables(self, text: str) -> str:
        """Replace template variables with actual values"""
        if not text:
            return text

        replacements = {
            "{{base_url}}": self.base_url,
            "{{auth_token}}": self.auth_token,
            "{{refresh_token}}": self.refresh_token,
            "{user_id}": str(self.test_data.get("user_id") or "100"),
            "{product_id}": str(self.test_data.get("product_id") or "1000"),
            "{category_id}": str(self.test_data.get("category_id") or "100"),
            "{address_id}": str(self.test_data.get("address_id") or "1"),
            "{order_id}": str(self.test_data.get("order_id") or "2000"),
            "{review_id}": str(self.test_data.get("review_id") or "1"),
            "{item_id}": str(self.test_data.get("cart_item_id") or "1"),
            "{chat_room_id}": str(self.test_data.get("chat_room_id") or "1"),
            "{image_id}": str(self.test_data.get("image_id") or "1"),
            "{seller_id}": "200",  # Use pre-seeded seller_a
            "{theme_id}": "1"
        }

        result = text
        for key, value in replacements.items():
            result = result.replace(key, value)

        # Replace test credentials with customer_a credentials
        # Handle both with and without quotes, and different formats
        result = result.replace('test@example.com', self.test_email)
        result = result.replace('testuser', self.test_username)
        result = result.replace('Test123!@#', self.test_password)
        result = result.replace('Mysql_2025!', self.test_password)  # Current password
        result = result.replace('CurrentPassword123!', self.test_password)  # Change password test

        # Fix hardcoded IDs in API test JSON
        result = result.replace('/users/123', '/users/101')  # Use existing user ID
        result = result.replace('"token": "reset_token_from_email"',
                               '"token": "ZQE9mBzlYvvxxtanG_VJrvmIXfYN5274A1MT-jCBQjY"')  # Use actual token
        # Note: Role names are lowercase in API ('customer', 'seller', 'dual')

        return result

    def extract_id_from_response(self, response: requests.Response, key: str) -> Optional[int]:
        """Extract ID from response JSON"""
        try:
            data = response.json()
            if isinstance(data, dict):
                return data.get("id") or data.get(key)
            return None
        except:
            return None

    def verify_email_mock(self) -> bool:
        """
        Mock email verification for testing
        For customer_a account, email is already verified
        """
        self.email_verified = True
        return True

    def test_endpoint(self, name: str, request_data: Dict) -> bool:
        """Test a single API endpoint"""
        self.results["total"] += 1

        # Skip WebSocket, file upload, and deactivate account tests
        if "WebSocket" in name or "Upload" in name:
            self.log(f"SKIP: {name} (requires special handling)", "SKIP")
            self.results["skipped"] += 1
            return True

        # Skip deactivate account test to prevent account invalidation
        if "Deactivate Account" in name:
            self.log(f"SKIP: {name} (would invalidate subsequent tests)", "SKIP")
            self.results["skipped"] += 1
            return True

        # Skip Register test (using pre-seeded account)
        if "Register" in name:
            self.log(f"SKIP: {name} (using pre-seeded customer_a account)", "SKIP")
            self.results["skipped"] += 1
            return True

        # Skip Reset Password test (token gets regenerated by Forgot Password)
        if "Reset Password" in name:
            self.log(f"SKIP: {name} (token regenerated by Forgot Password, requires email access)", "SKIP")
            self.results["skipped"] += 1
            return True

        # Preserve auth token for logout test
        backup_token = None
        backup_refresh = None
        if "Logout" in name:
            backup_token = self.auth_token
            backup_refresh = self.refresh_token

        # Extract request details
        method = request_data.get("method", "GET")
        url_data = request_data.get("url", {})

        # Build URL
        if isinstance(url_data, dict):
            raw_url = url_data.get("raw", "")
            url = self.replace_variables(raw_url)
        else:
            url = str(url_data)

        # Get headers
        headers = {}
        for header in request_data.get("header", []):
            if isinstance(header, dict):
                key = header.get("key", "")
                value = header.get("value", "")
                if key and value:
                    headers[key] = value

        # Debug headers for login
        if "Login" in name and self.verbose:
            self.log(f"Request headers: {headers}", "INFO")

        # Get body
        body = None
        body_data = request_data.get("body", {})
        if isinstance(body_data, dict):
            raw_body = body_data.get("raw")
            if raw_body:
                body = self.replace_variables(raw_body)
                # Debug login request
                if "Login" in name and self.verbose:
                    self.log(f"Login body: {body}", "INFO")

        # Get query params
        params = {}
        if isinstance(url_data, dict):
            for query in url_data.get("query", []):
                if isinstance(query, dict) and not query.get("disabled", False):
                    key = query.get("key", "")
                    value = query.get("value", "")
                    if key and value:
                        params[key] = self.replace_variables(value)

        # Make request
        response = self.make_request(method, url, headers, body, params)

        if response is None:
            self.log(f"FAIL: {name} (no response)", "ERROR")
            self.results["failed"] += 1
            self.results["errors"].append({
                "endpoint": name,
                "error": "No response received"
            })
            return False

        # Check if successful (2xx or 3xx status codes)
        if 200 <= response.status_code < 400:
            self.log(f"PASS: {name} ({response.status_code})", "SUCCESS")
            self.results["passed"] += 1

            # Extract tokens from login
            if "Login" in name:
                try:
                    data = response.json()
                    if "access_token" in data:
                        self.auth_token = data["access_token"]
                        self.log(f"✓ Auth token captured", "SUCCESS")
                    if "refresh_token" in data:
                        self.refresh_token = data["refresh_token"]
                        self.log(f"✓ Refresh token captured", "SUCCESS")
                    if "id" in data:
                        self.test_data["user_id"] = data["id"]
                        self.log(f"✓ User ID captured: {data['id']}", "SUCCESS")
                    # Sometimes user data is nested
                    if "user" in data and isinstance(data["user"], dict):
                        if "id" in data["user"]:
                            self.test_data["user_id"] = data["user"]["id"]
                            self.log(f"✓ User ID captured: {data['user']['id']}", "SUCCESS")

                except Exception as e:
                    if self.verbose:
                        self.log(f"Could not extract auth data: {e}", "WARNING")

            # Extract IDs for future tests
            if "Create" in name or "Add to Cart" in name:
                try:
                    data = response.json()
                    # Check for both "id" and "item_id" (cart endpoints use "item_id")
                    extracted_id = data.get("id") or data.get("item_id")
                    if extracted_id:
                        if "Product" in name:
                            self.test_data["product_id"] = extracted_id
                            self.log(f"✓ Product ID captured: {extracted_id}", "SUCCESS")
                        elif "Category" in name:
                            self.test_data["category_id"] = extracted_id
                            self.log(f"✓ Category ID captured: {extracted_id}", "SUCCESS")
                        elif "Address" in name or "Shipping" in name:
                            self.test_data["address_id"] = extracted_id
                            self.log(f"✓ Address ID captured: {extracted_id}", "SUCCESS")
                        elif "Order" in name:
                            self.test_data["order_id"] = extracted_id
                            self.log(f"✓ Order ID captured: {extracted_id}", "SUCCESS")
                        elif "Review" in name:
                            self.test_data["review_id"] = extracted_id
                            self.log(f"✓ Review ID captured: {extracted_id}", "SUCCESS")
                        elif "Chat" in name:
                            self.test_data["chat_room_id"] = extracted_id
                            self.log(f"✓ Chat Room ID captured: {extracted_id}", "SUCCESS")
                        elif "Cart" in name:
                            self.test_data["cart_item_id"] = extracted_id
                            self.log(f"✓ Cart Item ID captured: {extracted_id}", "SUCCESS")
                except Exception as e:
                    if self.verbose:
                        self.log(f"Could not extract ID from {name}: {e}", "WARNING")

            # Restore auth token after logout test
            if "Logout" in name and backup_token:
                self.auth_token = backup_token
                self.refresh_token = backup_refresh
                self.log(f"✓ Auth token restored after logout test", "INFO")

            return True
        else:
            self.log(f"FAIL: {name} ({response.status_code})", "ERROR")
            self.results["failed"] += 1
            error_msg = f"Status {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data.get('detail', '')}"
            except:
                error_msg += f" - {response.text[:100]}"

            self.results["errors"].append({
                "endpoint": name,
                "error": error_msg
            })
            return False

    def run_tests(self, collection_file: str, categories: List[str] = None):
        """Run customer role tests from Postman collection"""
        self.log(f"Loading API collection from {collection_file}", "INFO")

        try:
            with open(collection_file, 'r') as f:
                collection = json.load(f)
        except Exception as e:
            self.log(f"Failed to load collection: {str(e)}", "ERROR")
            return

        # Extract base URL from collection variables
        for var in collection.get("variable", []):
            if var.get("key") == "base_url":
                self.base_url = var.get("value", self.base_url)

        self.log(f"Base URL: {self.base_url}", "INFO")
        self.log(f"Test Account: {self.test_email} (Customer Role)", "INFO")
        self.log(f"Test Username: {self.test_username}", "INFO")
        self.log("=" * 80, "INFO")

        # Process each category
        for item in collection.get("item", []):
            category_name = item.get("name", "Unknown")

            # Skip seller-specific categories
            if category_name in self.skip_categories:
                self.log(f"\nSKIPPING Seller Category: {category_name}", "SKIP")
                continue

            # Skip if category filter is set and this category is not included
            if categories and category_name not in categories:
                continue

            self.log(f"\nTesting Category: {category_name}", "INFO")
            self.log("-" * 80, "INFO")

            # Test each endpoint in the category
            for endpoint in item.get("item", []):
                endpoint_name = endpoint.get("name", "Unknown")
                request_data = endpoint.get("request", {})

                if request_data:
                    time.sleep(0.1)  # Small delay between requests
                    self.test_endpoint(endpoint_name, request_data)

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test execution summary"""
        self.log("\n" + "=" * 80, "INFO")
        self.log("TEST SUMMARY - CUSTOMER ROLE", "INFO")
        self.log("=" * 80, "INFO")

        total = self.results["total"]
        passed = self.results["passed"]
        failed = self.results["failed"]
        skipped = self.results["skipped"]

        self.log(f"Total Tests: {total}", "INFO")
        self.log(f"Passed: {passed}", "SUCCESS")
        self.log(f"Failed: {failed}", "ERROR" if failed > 0 else "INFO")
        self.log(f"Skipped: {skipped}", "WARNING")

        if total > 0:
            success_rate = (passed / total) * 100
            self.log(f"Success Rate: {success_rate:.1f}%",
                    "SUCCESS" if success_rate >= 80 else "WARNING")

        # Print errors
        if self.results["errors"]:
            self.log("\n" + "=" * 80, "ERROR")
            self.log("ERRORS", "ERROR")
            self.log("=" * 80, "ERROR")
            for error in self.results["errors"]:
                self.log(f"{error['endpoint']}: {error['error']}", "ERROR")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Mercai API Test Suite - Customer Role",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all customer endpoints
  python test_customer_role.py

  # Test specific categories
  python test_customer_role.py --categories "Authentication" "Product Browsing"

  # Verbose output
  python test_customer_role.py --verbose

  # Custom base URL
  python test_customer_role.py --base-url "http://localhost:8000/api/v1"

Note: This test suite uses the pre-seeded customer_a account from seed_test_data.sql
        """
    )

    parser.add_argument(
        "--collection",
        default="api_test.json",
        help="Path to Postman collection file (default: api_test.json)"
    )

    parser.add_argument(
        "--base-url",
        help="Override base URL from collection"
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        help="Test only specific categories"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Determine base URL
    base_url = args.base_url or "http://localhost:8002/api/v1"

    # Create tester and run
    tester = APITesterCustomer(base_url, verbose=args.verbose)
    tester.run_tests(args.collection, args.categories)

    # Exit with appropriate code
    sys.exit(0 if tester.results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
