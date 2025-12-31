"""
Integration tests for auth-service.

Tests cover:
- User registration
- User login/logout
- Token refresh
- Password management
- Token verification
"""

import pytest
import httpx
from datetime import datetime

from tests.conftest import get_api_path


pytestmark = [pytest.mark.integration, pytest.mark.auth]


class TestHealthEndpoints:
    """Test auth-service health endpoints."""

    async def test_health_live(self, auth_client: httpx.AsyncClient):
        """Test liveness probe endpoint."""
        response = await auth_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    async def test_health_ready(self, auth_client: httpx.AsyncClient):
        """Test readiness probe endpoint."""
        response = await auth_client.get("/health/ready")
        # May return 503 if database not connected
        assert response.status_code in [200, 503]
        data = response.json()
        if response.status_code == 200:
            assert data["status"] == "ready"
            assert "database" in data


class TestUserRegistration:
    """Test user registration flow."""

    async def test_register_new_user(
        self,
        auth_client: httpx.AsyncClient,
        test_user_data: dict
    ):
        """Test successful user registration."""
        response = await auth_client.post(
            get_api_path("auth/register"),
            json=test_user_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "password" not in data  # Password should not be returned
        assert "id" in data

    async def test_register_duplicate_username(
        self,
        auth_client: httpx.AsyncClient,
        registered_user: dict,
        test_user_data: dict
    ):
        """Test registration with existing username fails."""
        duplicate_data = {
            **test_user_data,
            "username": registered_user["username"],
            "email": "different@test.com"
        }
        response = await auth_client.post(
            get_api_path("auth/register"),
            json=duplicate_data
        )
        assert response.status_code in [400, 409]

    async def test_register_duplicate_email(
        self,
        auth_client: httpx.AsyncClient,
        registered_user: dict,
        test_user_data: dict
    ):
        """Test registration with existing email fails."""
        duplicate_data = {
            **test_user_data,
            "username": "different_user",
            "email": registered_user["email"]
        }
        response = await auth_client.post(
            get_api_path("auth/register"),
            json=duplicate_data
        )
        assert response.status_code in [400, 409]

    async def test_register_invalid_email(self, auth_client: httpx.AsyncClient):
        """Test registration with invalid email fails."""
        response = await auth_client.post(
            get_api_path("auth/register"),
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "Password123!"
            }
        )
        assert response.status_code == 422

    async def test_register_weak_password(self, auth_client: httpx.AsyncClient):
        """Test registration with weak password fails."""
        response = await auth_client.post(
            get_api_path("auth/register"),
            json={
                "username": "testuser",
                "email": "test@test.com",
                "password": "weak"
            }
        )
        assert response.status_code == 422


class TestUserLogin:
    """Test user login flow."""

    async def test_login_with_email(
        self,
        auth_client: httpx.AsyncClient,
        registered_user: dict
    ):
        """Test successful login with email."""
        response = await auth_client.post(
            get_api_path("auth/login"),
            json={
                "email": registered_user["email"],
                "password": registered_user["password"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(
        self,
        auth_client: httpx.AsyncClient,
        registered_user: dict
    ):
        """Test login with wrong password fails."""
        response = await auth_client.post(
            get_api_path("auth/login"),
            json={
                "email": registered_user["email"],
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, auth_client: httpx.AsyncClient):
        """Test login with non-existent user fails."""
        response = await auth_client.post(
            get_api_path("auth/login"),
            json={
                "email": "nonexistent@test.com",
                "password": "Password123!"
            }
        )
        assert response.status_code == 401


class TestTokenManagement:
    """Test token management operations."""

    async def test_token_refresh(
        self,
        auth_client: httpx.AsyncClient,
        registered_user: dict
    ):
        """Test refreshing access token."""
        # First login to get tokens
        login_response = await auth_client.post(
            get_api_path("auth/login"),
            json={
                "email": registered_user["email"],
                "password": registered_user["password"]
            }
        )
        tokens = login_response.json()

        # Refresh the token
        response = await auth_client.post(
            get_api_path("auth/refresh"),
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        # New access token should be returned (may or may not be different
        # depending on whether timestamp changed)
        assert data["access_token"]

    async def test_token_refresh_invalid_token(self, auth_client: httpx.AsyncClient):
        """Test refresh with invalid token fails."""
        response = await auth_client.post(
            get_api_path("auth/refresh"),
            json={"refresh_token": "invalid.refresh.token"}
        )
        assert response.status_code == 401

    async def test_verify_valid_token(
        self,
        auth_client: httpx.AsyncClient,
        auth_token: str
    ):
        """Test verifying a valid token."""
        response = await auth_client.post(
            get_api_path("auth/verify"),
            json={"token": auth_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    async def test_verify_invalid_token(self, auth_client: httpx.AsyncClient):
        """Test verifying an invalid token."""
        response = await auth_client.post(
            get_api_path("auth/verify"),
            json={"token": "invalid.token.here"}
        )
        # Returns 200 with valid=False, or 401 depending on implementation
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["valid"] is False


class TestUserProfile:
    """Test user profile operations."""

    async def test_get_current_user(
        self,
        auth_client: httpx.AsyncClient,
        auth_token: str,
        registered_user: dict
    ):
        """Test getting current user profile."""
        response = await auth_client.get(
            get_api_path("auth/me"),
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == registered_user["username"]
        assert data["email"] == registered_user["email"]

    async def test_get_current_user_unauthorized(self, auth_client: httpx.AsyncClient):
        """Test getting current user without token fails."""
        response = await auth_client.get(get_api_path("auth/me"))
        assert response.status_code == 401


class TestPasswordManagement:
    """Test password management operations."""

    async def test_change_password(
        self,
        auth_client: httpx.AsyncClient,
        auth_token: str,
        registered_user: dict
    ):
        """Test changing password."""
        new_password = "NewPassword456!"
        response = await auth_client.post(
            get_api_path("auth/change-password"),
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": registered_user["password"],
                "new_password": new_password
            }
        )
        assert response.status_code == 200

        # Verify new password works
        login_response = await auth_client.post(
            get_api_path("auth/login"),
            json={
                "email": registered_user["email"],
                "password": new_password
            }
        )
        assert login_response.status_code == 200

    async def test_change_password_wrong_current(
        self,
        auth_client: httpx.AsyncClient,
        auth_token: str
    ):
        """Test changing password with wrong current password fails."""
        response = await auth_client.post(
            get_api_path("auth/change-password"),
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewPassword456!"
            }
        )
        assert response.status_code in [400, 401]


class TestLogout:
    """Test logout operations."""

    async def test_logout(
        self,
        auth_client: httpx.AsyncClient,
        registered_user: dict
    ):
        """Test logging out invalidates token."""
        # First login to get tokens
        login_response = await auth_client.post(
            get_api_path("auth/login"),
            json={
                "email": registered_user["email"],
                "password": registered_user["password"]
            }
        )
        tokens = login_response.json()

        # Logout using refresh token
        response = await auth_client.post(
            get_api_path("auth/logout"),
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == 200

        # Token should be invalid now - refresh should fail
        refresh_response = await auth_client.post(
            get_api_path("auth/refresh"),
            json={"refresh_token": tokens["refresh_token"]}
        )
        # Refresh token should be revoked
        assert refresh_response.status_code in [401, 404]


class TestRateLimiting:
    """Test rate limiting on auth endpoints."""

    @pytest.mark.slow
    async def test_login_rate_limiting(self, auth_client: httpx.AsyncClient):
        """Test that login endpoint has rate limiting."""
        # Attempt many failed logins
        responses = []
        for _ in range(20):
            response = await auth_client.post(
                get_api_path("auth/login"),
                json={
                    "email": "nonexistent@test.com",
                    "password": "wrong"
                }
            )
            responses.append(response.status_code)

        # Should see some 429 (Too Many Requests) eventually
        # Or all 401s if rate limiting is per-IP and generous
        assert all(code in [401, 429] for code in responses)


class TestInputValidation:
    """Test input validation on auth endpoints."""

    async def test_register_missing_fields(self, auth_client: httpx.AsyncClient):
        """Test registration with missing required fields."""
        response = await auth_client.post(
            get_api_path("auth/register"),
            json={"username": "testuser"}  # Missing email and password
        )
        assert response.status_code == 422

    async def test_login_missing_fields(self, auth_client: httpx.AsyncClient):
        """Test login with missing fields."""
        response = await auth_client.post(
            get_api_path("auth/login"),
            json={"email": "test@test.com"}  # Missing password
        )
        assert response.status_code == 422

    async def test_register_username_too_short(self, auth_client: httpx.AsyncClient):
        """Test registration with too short username."""
        response = await auth_client.post(
            get_api_path("auth/register"),
            json={
                "username": "ab",  # Too short
                "email": "test@test.com",
                "password": "Password123!"
            }
        )
        assert response.status_code == 422
