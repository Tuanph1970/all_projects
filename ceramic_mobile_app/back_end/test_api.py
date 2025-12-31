#!/usr/bin/env python3
"""
Ceramic Mobile App API Test Suite
Automated testing for all API endpoints defined in api_test.json
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


class APITester:
    """Automated API testing framework"""

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
            "user_id": None,
            "product_id": None,
            "category_id": None,
            "address_id": None,
            "order_id": None,
            "review_id": None,
            "cart_item_id": None,
            "chat_room_id": None,
            "image_id": None
        }
        # Generate unique test credentials
        timestamp = int(time.time())
        self.test_email = f"test_{timestamp}@example.com"
        self.test_username = f"testuser_{timestamp}"
        self.test_password = "Test123!@#"
        self.email_verified = False
        self.verification_token = None

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
                except json.JSONDecodeError:
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
            "{user_id}": str(self.test_data.get("user_id") or "1"),
            "{product_id}": str(self.test_data.get("product_id") or "1"),
            "{category_id}": str(self.test_data.get("category_id") or "1"),
            "{address_id}": str(self.test_data.get("address_id") or "1"),
            "{order_id}": str(self.test_data.get("order_id") or "1"),
            "{review_id}": str(self.test_data.get("review_id") or "1"),
            "{item_id}": str(self.test_data.get("cart_item_id") or "1"),
            "{chat_room_id}": str(self.test_data.get("chat_room_id") or "1"),
            "{image_id}": str(self.test_data.get("image_id") or "1"),
            "{seller_id}": str(self.test_data.get("user_id") or "1"),
            "{theme_id}": "1"
        }

        result = text
        for key, value in replacements.items():
            result = result.replace(key, value)

        # Replace test credentials dynamically
        if '"test@example.com"' in result:
            result = result.replace('"test@example.com"', f'"{self.test_email}"')
        if '"testuser"' in result:
            result = result.replace('"testuser"', f'"{self.test_username}"')

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
        In production, this would require checking email and clicking verification link.
        For testing, we'll attempt to verify using a mock token.
        """
        if self.email_verified:
            return True

        self.log("⚠️  Email verification required for some endpoints", "WARNING")
        self.log("⚠️  In production: Check email and click verification link", "WARNING")
        self.log("⚠️  For testing: Using mock verification (may not work)", "WARNING")

        # Try to get verification from database directly (won't work remotely)
        # This is a placeholder - actual verification requires email access
        self.email_verified = False
        return False

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

        # Get body
        body = None
        body_data = request_data.get("body", {})
        if isinstance(body_data, dict):
            raw_body = body_data.get("raw")
            if raw_body:
                body = self.replace_variables(raw_body)

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
            if "Login" in name or "Register" in name:
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

                    # Attempt email verification after registration
                    if "Register" in name:
                        self.verify_email_mock()

                except Exception as e:
                    if self.verbose:
                        self.log(f"Could not extract auth data: {e}", "WARNING")

            # Extract IDs for future tests
            if "Create" in name:
                try:
                    data = response.json()
                    extracted_id = data.get("id")
                    if extracted_id:
                        if "Product" in name:
                            self.test_data["product_id"] = extracted_id
                            self.log(f"✓ Product ID captured: {extracted_id}", "SUCCESS")
                        elif "Category" in name:
                            self.test_data["category_id"] = extracted_id
                            self.log(f"✓ Category ID captured: {extracted_id}", "SUCCESS")
                        elif "Address" in name:
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
        """Run all tests from Postman collection"""
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
        self.log(f"Test Email: {self.test_email}", "INFO")
        self.log(f"Test Username: {self.test_username}", "INFO")
        self.log("=" * 80, "INFO")

        # Process each category
        for item in collection.get("item", []):
            category_name = item.get("name", "Unknown")

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
        self.log("TEST SUMMARY", "INFO")
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
        description="Ceramic Mobile App API Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all endpoints
  python test_api.py

  # Test specific categories
  python test_api.py --categories "Authentication" "Product Management"

  # Verbose output
  python test_api.py --verbose

  # Custom base URL
  python test_api.py --base-url "http://localhost:8000/api/v1"
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
    base_url = args.base_url or "http://112.213.91.103:8002/api/v1"

    # Create tester and run
    tester = APITester(base_url, verbose=args.verbose)
    tester.run_tests(args.collection, args.categories)

    # Exit with appropriate code
    sys.exit(0 if tester.results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
