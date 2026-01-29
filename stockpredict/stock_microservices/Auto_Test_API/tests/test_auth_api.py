"""
Authentication API Tests

Tests for:
- POST /auth/register - Register new user
- POST /auth/login - User login
- POST /auth/refresh - Refresh token
- POST /auth/verify - Verify token
- GET /auth/me - Get current user
- POST /auth/change-password - Change password
- POST /auth/logout - Logout (single device)
- POST /auth/logout-all - Logout all devices
- POST /auth/reset-password - Request password reset
"""
import sys
import os
import uuid
from datetime import datetime
from typing import Tuple, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from utils.http_client import (
    APIClient,
    print_test_result,
    print_section,
    print_summary,
)


class TestAuthAPI:
    """Authentication API Test Suite"""

    def __init__(self, base_url: str = None, verbose: bool = True):
        self.base_url = base_url or settings.BASE_URL
        self.client = APIClient(self.base_url, verbose=verbose)
        self.test_results = []
        self.created_user_email: Optional[str] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

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

    def _generate_unique_email(self) -> str:
        """Generate unique email for testing"""
        unique_id = str(uuid.uuid4())[:8]
        return f"autotest_{unique_id}@stockhelper.com"

    def _generate_unique_username(self) -> str:
        """Generate unique username for testing"""
        unique_id = str(uuid.uuid4())[:8]
        return f"autotest_{unique_id}"

    # =========================================================================
    # TEST: Register User
    # =========================================================================
    def test_register_success(self) -> bool:
        """Test successful user registration"""
        print_section("TEST: Register User - Success")

        email = self._generate_unique_email()
        username = self._generate_unique_username()
        password = "TestPass@123"

        response = self.client.post("/auth/register", json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": "Auto Test User"
        })

        if response.success:
            self.created_user_email = email
            data = response.data
            passed = (
                data.get("email") == email and
                data.get("username") == username and
                "id" in data
            )
            return self._record_result(
                "Register user with valid data",
                passed,
                f"Created user ID: {data.get('id')}" if passed else "Response data mismatch"
            )
        else:
            return self._record_result(
                "Register user with valid data",
                False,
                response.error or "Registration failed"
            )

    def test_register_duplicate_email(self) -> bool:
        """Test registration with duplicate email"""
        print_section("TEST: Register User - Duplicate Email")

        if not self.created_user_email:
            return self._record_result(
                "Register with duplicate email",
                False,
                "No user created in previous test"
            )

        response = self.client.post("/auth/register", json={
            "email": self.created_user_email,
            "username": self._generate_unique_username(),
            "password": "TestPass@123"
        })

        passed = response.status_code == 409
        return self._record_result(
            "Register with duplicate email returns 409",
            passed,
            f"Got status code: {response.status_code}"
        )

    def test_register_invalid_email(self) -> bool:
        """Test registration with invalid email format"""
        print_section("TEST: Register User - Invalid Email")

        response = self.client.post("/auth/register", json={
            "email": "invalid-email-format",
            "username": self._generate_unique_username(),
            "password": "TestPass@123"
        })

        passed = response.status_code == 422  # Validation error
        return self._record_result(
            "Register with invalid email returns 422",
            passed,
            f"Got status code: {response.status_code}"
        )

    def test_register_weak_password(self) -> bool:
        """Test registration with weak password"""
        print_section("TEST: Register User - Weak Password")

        response = self.client.post("/auth/register", json={
            "email": self._generate_unique_email(),
            "username": self._generate_unique_username(),
            "password": "weak"  # Too short, no uppercase, no digit
        })

        passed = response.status_code == 422  # Validation error
        return self._record_result(
            "Register with weak password returns 422",
            passed,
            f"Got status code: {response.status_code}"
        )

    def test_register_missing_fields(self) -> bool:
        """Test registration with missing required fields"""
        print_section("TEST: Register User - Missing Fields")

        response = self.client.post("/auth/register", json={
            "email": self._generate_unique_email()
            # Missing username and password
        })

        passed = response.status_code == 422  # Validation error
        return self._record_result(
            "Register with missing fields returns 422",
            passed,
            f"Got status code: {response.status_code}"
        )

    # =========================================================================
    # TEST: Login User
    # =========================================================================
    def test_login_success(self) -> bool:
        """Test successful user login"""
        print_section("TEST: Login User - Success")

        # First ensure we have a test user
        if not self.created_user_email:
            self.test_register_success()

        if not self.created_user_email:
            return self._record_result(
                "Login with valid credentials",
                False,
                "Could not create test user"
            )

        response = self.client.post("/auth/login", json={
            "email": self.created_user_email,
            "password": "TestPass@123"
        })

        if response.success:
            data = response.data
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")

            passed = (
                self.access_token is not None and
                self.refresh_token is not None and
                data.get("token_type") == "bearer"
            )

            if passed:
                self.client.set_auth_tokens(self.access_token, self.refresh_token)

            return self._record_result(
                "Login with valid credentials",
                passed,
                "Got access and refresh tokens" if passed else "Missing tokens in response"
            )
        else:
            return self._record_result(
                "Login with valid credentials",
                False,
                response.error or "Login failed"
            )

    def test_login_invalid_password(self) -> bool:
        """Test login with invalid password"""
        print_section("TEST: Login User - Invalid Password")

        if not self.created_user_email:
            return self._record_result(
                "Login with invalid password",
                False,
                "No test user available"
            )

        response = self.client.post("/auth/login", json={
            "email": self.created_user_email,
            "password": "WrongPassword@123"
        })

        passed = response.status_code == 401
        return self._record_result(
            "Login with invalid password returns 401",
            passed,
            f"Got status code: {response.status_code}"
        )

    def test_login_nonexistent_user(self) -> bool:
        """Test login with non-existent user"""
        print_section("TEST: Login User - Non-existent User")

        response = self.client.post("/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "TestPass@123"
        })

        passed = response.status_code == 401
        return self._record_result(
            "Login with non-existent user returns 401",
            passed,
            f"Got status code: {response.status_code}"
        )

    # =========================================================================
    # TEST: Verify Token
    # =========================================================================
    def test_verify_token_valid(self) -> bool:
        """Test verifying a valid token"""
        print_section("TEST: Verify Token - Valid")

        if not self.access_token:
            self.test_login_success()

        if not self.access_token:
            return self._record_result(
                "Verify valid token",
                False,
                "No access token available"
            )

        response = self.client.post("/auth/verify", json={
            "token": self.access_token
        })

        if response.success:
            data = response.data
            passed = data.get("valid") == True
            return self._record_result(
                "Verify valid token returns valid=true",
                passed,
                f"Token valid: {data.get('valid')}"
            )
        else:
            return self._record_result(
                "Verify valid token",
                False,
                response.error or "Verification failed"
            )

    def test_verify_token_invalid(self) -> bool:
        """Test verifying an invalid token"""
        print_section("TEST: Verify Token - Invalid")

        response = self.client.post("/auth/verify", json={
            "token": "invalid.jwt.token"
        })

        if response.success:
            data = response.data
            passed = data.get("valid") == False
            return self._record_result(
                "Verify invalid token returns valid=false",
                passed,
                f"Token valid: {data.get('valid')}"
            )
        else:
            # Could also return error status
            return self._record_result(
                "Verify invalid token",
                True,  # Error response is acceptable
                f"Status: {response.status_code}"
            )

    # =========================================================================
    # TEST: Get Current User
    # =========================================================================
    def test_get_me_authenticated(self) -> bool:
        """Test getting current user info when authenticated"""
        print_section("TEST: Get Current User - Authenticated")

        if not self.access_token:
            self.test_login_success()

        if not self.access_token:
            return self._record_result(
                "Get current user info",
                False,
                "No access token available"
            )

        response = self.client.get("/auth/me")

        if response.success:
            data = response.data
            passed = (
                data.get("email") == self.created_user_email and
                "id" in data
            )
            return self._record_result(
                "Get current user info returns user data",
                passed,
                f"User: {data.get('email')}"
            )
        else:
            return self._record_result(
                "Get current user info",
                False,
                response.error or "Failed to get user info"
            )

    def test_get_me_unauthenticated(self) -> bool:
        """Test getting current user info without authentication"""
        print_section("TEST: Get Current User - Unauthenticated")

        # Clear auth headers temporarily
        self.client.clear_auth()

        response = self.client.get("/auth/me")

        # Restore auth
        if self.access_token:
            self.client.set_auth_tokens(self.access_token, self.refresh_token)

        passed = response.status_code == 401
        return self._record_result(
            "Get current user without auth returns 401",
            passed,
            f"Got status code: {response.status_code}"
        )

    # =========================================================================
    # TEST: Refresh Token
    # =========================================================================
    def test_refresh_token_valid(self) -> bool:
        """Test refreshing token with valid refresh token"""
        print_section("TEST: Refresh Token - Valid")

        if not self.refresh_token:
            self.test_login_success()

        if not self.refresh_token:
            return self._record_result(
                "Refresh token",
                False,
                "No refresh token available"
            )

        response = self.client.post("/auth/refresh", json={
            "refresh_token": self.refresh_token
        })

        if response.success:
            data = response.data
            new_access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token")

            passed = (
                new_access_token is not None and
                new_refresh_token is not None
            )

            if passed:
                self.access_token = new_access_token
                self.refresh_token = new_refresh_token
                self.client.set_auth_tokens(self.access_token, self.refresh_token)

            return self._record_result(
                "Refresh token returns new tokens",
                passed,
                "Got new tokens" if passed else "Missing tokens"
            )
        else:
            return self._record_result(
                "Refresh token",
                False,
                response.error or "Refresh failed"
            )

    def test_refresh_token_invalid(self) -> bool:
        """Test refreshing with invalid refresh token"""
        print_section("TEST: Refresh Token - Invalid")

        response = self.client.post("/auth/refresh", json={
            "refresh_token": "invalid.refresh.token"
        })

        passed = response.status_code == 401
        return self._record_result(
            "Refresh with invalid token returns 401",
            passed,
            f"Got status code: {response.status_code}"
        )

    # =========================================================================
    # TEST: Change Password
    # =========================================================================
    def test_change_password_success(self) -> bool:
        """Test changing password successfully"""
        print_section("TEST: Change Password - Success")

        if not self.access_token:
            self.test_login_success()

        if not self.access_token:
            return self._record_result(
                "Change password",
                False,
                "No access token available"
            )

        new_password = "NewTestPass@456"
        response = self.client.post("/auth/change-password", json={
            "current_password": "TestPass@123",
            "new_password": new_password
        })

        if response.success:
            # Try to login with new password
            self.client.clear_auth()
            login_response = self.client.post("/auth/login", json={
                "email": self.created_user_email,
                "password": new_password
            })

            passed = login_response.success

            if passed:
                self.access_token = login_response.data.get("access_token")
                self.refresh_token = login_response.data.get("refresh_token")
                self.client.set_auth_tokens(self.access_token, self.refresh_token)

            return self._record_result(
                "Change password and login with new password",
                passed,
                "Password changed successfully" if passed else "Could not login with new password"
            )
        else:
            return self._record_result(
                "Change password",
                False,
                response.error or "Change password failed"
            )

    def test_change_password_wrong_current(self) -> bool:
        """Test changing password with wrong current password"""
        print_section("TEST: Change Password - Wrong Current Password")

        if not self.access_token:
            self.test_login_success()

        if not self.access_token:
            return self._record_result(
                "Change password with wrong current",
                False,
                "No access token available"
            )

        response = self.client.post("/auth/change-password", json={
            "current_password": "WrongCurrentPass@123",
            "new_password": "NewTestPass@789"
        })

        passed = response.status_code == 400
        return self._record_result(
            "Change password with wrong current returns 400",
            passed,
            f"Got status code: {response.status_code}"
        )

    # =========================================================================
    # TEST: Logout
    # =========================================================================
    def test_logout_single(self) -> bool:
        """Test logout from single device"""
        print_section("TEST: Logout - Single Device")

        if not self.refresh_token:
            self.test_login_success()

        if not self.refresh_token:
            return self._record_result(
                "Logout single device",
                False,
                "No refresh token available"
            )

        response = self.client.post("/auth/logout", json={
            "refresh_token": self.refresh_token
        })

        passed = response.success
        return self._record_result(
            "Logout single device",
            passed,
            response.data.get("message") if response.success else response.error
        )

    def test_logout_all(self) -> bool:
        """Test logout from all devices"""
        print_section("TEST: Logout - All Devices")

        # First login again to get new tokens
        if self.created_user_email:
            login_response = self.client.post("/auth/login", json={
                "email": self.created_user_email,
                "password": "NewTestPass@456"  # Password was changed
            })

            if login_response.success:
                self.access_token = login_response.data.get("access_token")
                self.refresh_token = login_response.data.get("refresh_token")
                self.client.set_auth_tokens(self.access_token, self.refresh_token)

        if not self.access_token:
            return self._record_result(
                "Logout all devices",
                False,
                "No access token available"
            )

        response = self.client.post("/auth/logout-all")

        passed = response.success
        return self._record_result(
            "Logout all devices",
            passed,
            response.data.get("message") if response.success else response.error
        )

    # =========================================================================
    # TEST: Reset Password
    # =========================================================================
    def test_reset_password_request(self) -> bool:
        """Test requesting password reset"""
        print_section("TEST: Reset Password - Request")

        if not self.created_user_email:
            return self._record_result(
                "Request password reset",
                False,
                "No test user available"
            )

        response = self.client.post("/auth/reset-password", json={
            "email": self.created_user_email
        })

        # Should always return success (for security)
        passed = response.success
        return self._record_result(
            "Request password reset returns success",
            passed,
            response.data.get("message") if response.success else response.error
        )

    def test_reset_password_nonexistent(self) -> bool:
        """Test requesting password reset for non-existent email"""
        print_section("TEST: Reset Password - Non-existent Email")

        response = self.client.post("/auth/reset-password", json={
            "email": "nonexistent@example.com"
        })

        # Should still return success (for security - don't reveal if email exists)
        passed = response.success
        return self._record_result(
            "Request password reset for non-existent email",
            passed,
            "Returns success for security reasons"
        )

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================
    def run_all_tests(self) -> Tuple[int, int, int]:
        """Run all authentication tests"""
        print_section("AUTHENTICATION API TESTS")
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        tests = [
            # Registration Tests
            self.test_register_success,
            self.test_register_duplicate_email,
            self.test_register_invalid_email,
            self.test_register_weak_password,
            self.test_register_missing_fields,

            # Login Tests
            self.test_login_success,
            self.test_login_invalid_password,
            self.test_login_nonexistent_user,

            # Token Verification Tests
            self.test_verify_token_valid,
            self.test_verify_token_invalid,

            # Get Current User Tests
            self.test_get_me_authenticated,
            self.test_get_me_unauthenticated,

            # Refresh Token Tests
            self.test_refresh_token_valid,
            self.test_refresh_token_invalid,

            # Change Password Tests
            self.test_change_password_success,
            self.test_change_password_wrong_current,

            # Logout Tests
            self.test_logout_single,
            self.test_logout_all,

            # Reset Password Tests
            self.test_reset_password_request,
            self.test_reset_password_nonexistent,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                self._record_result(test.__name__, False, str(e))

        # Calculate summary
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = sum(1 for r in self.test_results if not r["passed"])
        total = len(self.test_results)

        print_summary(passed, failed, total)

        return passed, failed, total


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Authentication API Tests")
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

    tester = TestAuthAPI(base_url=args.base_url, verbose=not args.quiet)
    passed, failed, total = tester.run_all_tests()

    # Exit with non-zero code if any tests failed
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
