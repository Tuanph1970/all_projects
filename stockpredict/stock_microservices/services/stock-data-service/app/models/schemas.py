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
    exchange: str
    industry_id: Optional[int] = None
    industry_name: Optional[str] = None
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
    exchange: str
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
    exchange: str
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
