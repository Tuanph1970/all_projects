"""
Auth Service Tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "auth-service"


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient):
    """Test liveness probe"""
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, test_user_data):
    """Test user registration"""
    response = await client.post(
        "/stock_helper/api/v2/auth/register",
        json=test_user_data,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["username"] == test_user_data["username"]
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user_data):
    """Test duplicate email registration fails"""
    # First registration
    await client.post("/stock_helper/api/v2/auth/register", json=test_user_data)

    # Duplicate registration
    response = await client.post(
        "/stock_helper/api/v2/auth/register",
        json=test_user_data,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient, test_user_data):
    """Test user login"""
    # Register first
    await client.post("/stock_helper/api/v2/auth/register", json=test_user_data)

    # Login
    response = await client.post(
        "/stock_helper/api/v2/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user_data):
    """Test login with invalid credentials"""
    # Register first
    await client.post("/stock_helper/api/v2/auth/register", json=test_user_data)

    # Login with wrong password
    response = await client.post(
        "/stock_helper/api/v2/auth/login",
        json={
            "email": test_user_data["email"],
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user_data):
    """Test get current user endpoint"""
    # Register and login
    await client.post("/stock_helper/api/v2/auth/register", json=test_user_data)
    login_response = await client.post(
        "/stock_helper/api/v2/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    token = login_response.json()["access_token"]

    # Get current user
    response = await client.get(
        "/stock_helper/api/v2/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_data["email"]


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test get current user without authentication"""
    response = await client.get("/stock_helper/api/v2/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_token(client: AsyncClient, test_user_data):
    """Test token verification"""
    # Register and login
    await client.post("/stock_helper/api/v2/auth/register", json=test_user_data)
    login_response = await client.post(
        "/stock_helper/api/v2/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    token = login_response.json()["access_token"]

    # Verify token
    response = await client.post(
        "/stock_helper/api/v2/auth/verify",
        json={"token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user_data):
    """Test token refresh"""
    # Register and login
    await client.post("/stock_helper/api/v2/auth/register", json=test_user_data)
    login_response = await client.post(
        "/stock_helper/api/v2/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = await client.post(
        "/stock_helper/api/v2/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_user_data):
    """Test logout"""
    # Register and login
    await client.post("/stock_helper/api/v2/auth/register", json=test_user_data)
    login_response = await client.post(
        "/stock_helper/api/v2/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    # Logout
    response = await client.post(
        "/stock_helper/api/v2/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200

    # Try to use the refresh token again
    response = await client.post(
        "/stock_helper/api/v2/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401
