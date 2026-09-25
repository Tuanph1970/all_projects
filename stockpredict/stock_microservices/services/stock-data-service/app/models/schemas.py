"""
Pydantic Schemas for API request/response validation
"""
from datetime import datetime, date
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class IndustryResponse(BaseModel):
    """Industry response schema"""
    id: int
    code: str
    name: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    level: int
    company_count: Optional[int] = None

    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    """Company response schema"""
    id: int
    symbol: str
    name: str
    name_en: Optional[str] = None
    exchange: Optional[str] = None
    industry_id: Optional[int] = None
    industry_name: Optional[str] = None
    icb_name2: Optional[str] = None
    icb_name3: Optional[str] = None
    icb_name4: Optional[str] = None
    com_type_code: Optional[str] = None
    listing_date: Optional[date] = None
    outstanding_shares: Optional[int] = None
    market_cap: Optional[int] = None
    website: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    is_tradeable: bool

    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    """Simplified company list response"""
    symbol: str
    name: str
    exchange: Optional[str] = None
    industry_name: Optional[str] = None


class CompanyListingResponse(BaseModel):
    """Company listing from vnstock (live data)"""
    symbol: str
    name: str
    exchange: Optional[str] = None

    class Config:
        from_attributes = True


class CompanyDetailResponse(BaseModel):
    """Detailed company response with current price"""
    id: int
    symbol: str
    name: str
    name_en: Optional[str] = None
    exchange: str
    industry: Optional[IndustryResponse] = None
    listing_date: Optional[date] = None
    outstanding_shares: Optional[int] = None
    market_cap: Optional[int] = None
    website: Optional[str] = None
    description: Optional[str] = None
    current_price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None

    class Config:
        from_attributes = True


class StockPriceResponse(BaseModel):
    """Stock price response schema"""
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[int] = None
    value: Optional[int] = None
    # Mirrors `close`: the upstream series is already back-adjusted for share-count
    # events (bonus issues, stock dividends). See StockPrice.adj_close in domain.py.
    adj_close: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None

    class Config:
        from_attributes = True


class HistoricalDataRequest(BaseModel):
    """Request for historical data"""
    symbol: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    interval: str = Field(default="1D", description="Data interval: 1D, 1W, 1M")


class HistoricalDataResponse(BaseModel):
    """Historical data response"""
    symbol: str
    name: str
    exchange: Optional[str] = None
    data: List[StockPriceResponse]
    count: int


class MarketIndexResponse(BaseModel):
    """Market index response schema"""
    code: str
    name: str
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[int] = None
    value: Optional[int] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None

    class Config:
        from_attributes = True


class TopMoverResponse(BaseModel):
    """Top mover (gainer/loser) response"""
    symbol: str
    name: str
    exchange: str
    close: float
    change: float
    change_percent: float
    volume: int


class SearchResult(BaseModel):
    """Search result schema"""
    symbol: str
    name: str
    exchange: str
    industry_name: Optional[str] = None
    match_score: float = 1.0


class CompanyNewsResponse(BaseModel):
    """Company news response"""
    title: str
    source: str
    published_at: datetime
    url: str
    summary: Optional[str] = None


class CompanyEventResponse(BaseModel):
    """Company event response"""
    event_type: str
    event_date: date
    description: str
    ex_date: Optional[date] = None
    record_date: Optional[date] = None


class DividendResponse(BaseModel):
    """Dividend response"""
    ex_date: date
    record_date: Optional[date] = None
    payment_date: Optional[date] = None
    dividend_type: str
    dividend_rate: float
    description: Optional[str] = None


class PriceboardResponse(BaseModel):
    """Real-time priceboard response"""
    symbol: str
    name: str
    ref_price: float
    ceiling: float
    floor: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    avg_price: Optional[float] = None
    volume: Optional[int] = None
    value: Optional[int] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    bid_price_1: Optional[float] = None
    bid_volume_1: Optional[int] = None
    ask_price_1: Optional[float] = None
    ask_volume_1: Optional[int] = None


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class FinancialRatiosData(BaseModel):
    """Financial ratios data"""
    pe: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debtToEquity: Optional[float] = None
    currentRatio: Optional[float] = None
    quickRatio: Optional[float] = None
    grossMargin: Optional[float] = None
    operatingMargin: Optional[float] = None
    netMargin: Optional[float] = None


class GrowthMetricsData(BaseModel):
    """Growth metrics data"""
    revenueGrowth: Optional[float] = None
    earningsGrowth: Optional[float] = None
    epsGrowth: Optional[float] = None


class IncomeStatementData(BaseModel):
    """Income statement data"""
    revenue: Optional[float] = None
    grossProfit: Optional[float] = None
    operatingIncome: Optional[float] = None
    netIncome: Optional[float] = None
    eps: Optional[float] = None


class BalanceSheetData(BaseModel):
    """Balance sheet data"""
    totalAssets: Optional[float] = None
    totalLiabilities: Optional[float] = None
    totalEquity: Optional[float] = None
    cash: Optional[float] = None
    longTermDebt: Optional[float] = None


class CashFlowData(BaseModel):
    """Cash flow data"""
    operatingCashFlow: Optional[float] = None
    investingCashFlow: Optional[float] = None
    financingCashFlow: Optional[float] = None
    freeCashFlow: Optional[float] = None
    netCashFlow: Optional[float] = None


class CompanyFinancialsResponse(BaseModel):
    """Company financial ratios and metrics"""
    symbol: str
    company_name: Optional[str] = None
    # Valuation ratios (flat for backwards compatibility)
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    # Profitability ratios
    roe: Optional[float] = None
    roa: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    gross_margin: Optional[float] = None
    # Growth metrics
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    # Financial health
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    # Market data
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    # Per share data
    eps: Optional[float] = None
    book_value_per_share: Optional[float] = None
    dividend_yield: Optional[float] = None
    # Nested structures for frontend compatibility
    financial_ratios: Optional[FinancialRatiosData] = None
    growth_metrics: Optional[GrowthMetricsData] = None
    income_statement: Optional[IncomeStatementData] = None
    balance_sheet: Optional[BalanceSheetData] = None
    cash_flow: Optional[CashFlowData] = None
