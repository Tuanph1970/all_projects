"""
Stock Data Service Tests
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "stock-data-service"


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient):
    """Test liveness probe"""
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "stock-data-service"
    assert "version" in data


@pytest.mark.asyncio
async def test_get_industries(client: AsyncClient, mock_industry, mock_stock_service):
    """Test get industries endpoint"""
    mock_stock_service.get_all_industries = AsyncMock(return_value=[mock_industry])
    response = await client.get("/stock_helper/api/v2/industries")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_companies(client: AsyncClient, mock_company, mock_stock_service):
    """Test get companies endpoint"""
    mock_stock_service.get_all_companies = AsyncMock(return_value=([mock_company], 1, 1))
    response = await client.get("/stock_helper/api/v2/companies")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_get_top_gainers(client: AsyncClient, mock_top_mover, mock_stock_service):
    """Test top gainers endpoint"""
    mock_stock_service.get_top_gainers = AsyncMock(return_value=[mock_top_mover])
    response = await client.get("/stock_helper/api/v2/companies/top-gainers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_top_losers(client: AsyncClient, mock_top_mover, mock_stock_service):
    """Test top losers endpoint"""
    mock_stock_service.get_top_losers = AsyncMock(return_value=[mock_top_mover])
    response = await client.get("/stock_helper/api/v2/companies/top-losers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_top_actives(client: AsyncClient, mock_top_mover, mock_stock_service):
    """Test top actives endpoint"""
    mock_stock_service.get_most_active = AsyncMock(return_value=[mock_top_mover])
    response = await client.get("/stock_helper/api/v2/companies/top-actives")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_market_indices(client: AsyncClient, mock_market_index, mock_stock_service):
    """Test market indices endpoint"""
    mock_stock_service.get_latest_indices = AsyncMock(return_value=[mock_market_index])
    response = await client.get("/stock_helper/api/v2/market/indices/latest")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_company_not_found(client: AsyncClient, mock_stock_service):
    """Test 404 for non-existent company"""
    mock_stock_service.get_company_detail = AsyncMock(return_value=None)
    response = await client.get("/stock_helper/api/v2/stocks/NOTEXIST123")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_company_by_symbol(client: AsyncClient, mock_company_detail, mock_stock_service):
    """Test get company by symbol"""
    mock_stock_service.get_company_detail = AsyncMock(return_value=mock_company_detail)
    response = await client.get("/stock_helper/api/v2/stocks/VNM")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "VNM"


@pytest.mark.asyncio
async def test_get_historical_data(client: AsyncClient, mock_historical_data, mock_stock_service):
    """Test get historical data"""
    mock_stock_service.get_historical_data = AsyncMock(return_value=mock_historical_data)
    response = await client.get("/stock_helper/api/v2/stocks/VNM/history")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "VNM"
    assert "data" in data


@pytest.mark.asyncio
async def test_get_historical_data_not_found(client: AsyncClient, mock_stock_service):
    """Test get historical data for non-existent company"""
    mock_stock_service.get_historical_data = AsyncMock(return_value=None)
    response = await client.get("/stock_helper/api/v2/stocks/NOTEXIST/history")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_companies_by_industry(client: AsyncClient, mock_company, mock_stock_service):
    """Test get companies by industry"""
    # Route calls get_companies_by_industry_code and returns a
    # PaginatedResponse[CompanyResponse], not a bare list.
    paged = {
        "items": [mock_company.dict() if hasattr(mock_company, "dict") else mock_company],
        "total": 1,
        "page": 1,
        "page_size": 50,
        "total_pages": 1,
    }
    mock_stock_service.get_companies_by_industry_code = AsyncMock(return_value=paged)
    response = await client.get("/stock_helper/api/v2/industries/8300/companies")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body and isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_companies_pagination(client: AsyncClient, mock_company, mock_stock_service):
    """Test companies pagination"""
    mock_stock_service.get_all_companies = AsyncMock(return_value=([mock_company], 100, 4))
    response = await client.get("/stock_helper/api/v2/companies?page=2&page_size=25")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 25


@pytest.mark.asyncio
async def test_get_all_companies_list(client: AsyncClient, mock_company, mock_stock_service):
    """Test get all companies without pagination"""
    # Route calls get_all_companies_live (the /companies/all endpoint
    # bypasses pagination and returns a flat list from VNStock).
    mock_stock_service.get_all_companies_live = AsyncMock(return_value=[mock_company])
    response = await client.get("/stock_helper/api/v2/companies/all")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_market_indices_with_dates(client: AsyncClient, mock_market_index, mock_stock_service):
    """Test market indices with date filters"""
    mock_stock_service.get_market_indices = AsyncMock(return_value=[mock_market_index])
    response = await client.get(
        "/stock_helper/api/v2/market/indices?start_date=2024-01-01&end_date=2024-12-31"
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sync_stock_data(client: AsyncClient, mock_stock_service):
    """Test sync stock data endpoint"""
    mock_stock_service.fetch_and_save_historical_data = AsyncMock(return_value=100)
    response = await client.post("/stock_helper/api/v2/stocks/VNM/sync")
    assert response.status_code == 200
    data = response.json()
    assert "Synced" in data["message"]
    assert data["success"] is True
