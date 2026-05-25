"""Pydantic Schemas for Portfolio Service"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class AlertType(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    CHANGE_PERCENT = "change_percent"


# Portfolio Schemas
class PortfolioCreate(BaseModel):
    name: str = Field(default="Default Portfolio", max_length=255)
    description: Optional[str] = None
    is_default: bool = False


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    is_default: Optional[bool] = None


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Holding Schemas
class HoldingCreate(BaseModel):
    symbol: str = Field(..., max_length=20)
    quantity: int = Field(default=0, ge=0)
    average_price: Optional[float] = Field(default=None, ge=0)
    is_watchlist_only: bool = False


class HoldingUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, ge=0)
    average_price: Optional[float] = Field(default=None, ge=0)
    is_watchlist_only: Optional[bool] = None


class HoldingResponse(BaseModel):
    id: int
    portfolio_id: int
    symbol: str
    quantity: int
    average_price: Optional[float]
    total_cost: float
    current_price: Optional[float]
    current_value: Optional[float]
    profit_loss: Optional[float]
    profit_loss_percent: Optional[float]
    is_watchlist_only: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Transaction Schemas
class TransactionCreate(BaseModel):
    symbol: str = Field(..., max_length=20)
    transaction_type: Optional[TransactionType] = Field(default=None, alias="type")
    type: Optional[TransactionType] = None  # Accept both 'type' and 'transaction_type'
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    fees: float = Field(default=0, ge=0)
    notes: Optional[str] = None
    transaction_date: Optional[datetime] = Field(default=None, alias="date")

    def get_transaction_type(self) -> TransactionType:
        """Get transaction type from either field"""
        return self.transaction_type or self.type or TransactionType.BUY

    class Config:
        populate_by_name = True


class TransactionResponse(BaseModel):
    id: int
    portfolio_id: int
    symbol: str
    transaction_type: TransactionType
    quantity: int
    price: float
    total_value: float
    fees: float
    notes: Optional[str]
    transaction_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Price Alert Schemas
#
# Unit convention for price fields on this model and all alert-related code:
#   target_price  — actual VND (e.g. 73900 = 73,900 VND/share), matching what
#                   the user types into the Add-Alert form.
#   current_price — actual VND on the wire to the UI; the GET /alerts handler
#                   multiplies stock_prices.close (thousands-quote) by 1000
#                   before populating this field.
#
class AlertCreate(BaseModel):
    symbol: str = Field(..., max_length=20)
    alert_type: Optional[AlertType] = Field(default=None, alias="condition")
    condition: Optional[AlertType] = None  # Accept both 'condition' and 'alert_type'
    target_price: Optional[float] = Field(default=None, gt=0)
    target_percent: Optional[float] = None
    is_active: bool = True
    notes: Optional[str] = None

    def get_alert_type(self) -> AlertType:
        """Get alert type from either field"""
        return self.alert_type or self.condition or AlertType.ABOVE

    class Config:
        populate_by_name = True


class AlertUpdate(BaseModel):
    target_price: Optional[float] = Field(default=None, gt=0)
    target_percent: Optional[float] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class AlertResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    alert_type: AlertType
    target_price: Optional[float]
    target_percent: Optional[float]
    current_price: Optional[float] = None
    is_active: bool
    is_triggered: bool
    triggered_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Portfolio Summary Schemas
class PortfolioSummary(BaseModel):
    portfolio_id: int
    portfolio_name: str
    total_holdings: int
    total_invested: float
    current_value: float
    total_profit_loss: float
    total_profit_loss_percent: float
    top_performers: List[HoldingResponse]
    worst_performers: List[HoldingResponse]


class PortfolioWithHoldings(PortfolioResponse):
    holdings: List[HoldingResponse] = []
    transactions: List[TransactionResponse] = []


# Watchlist Schemas
class WatchlistAdd(BaseModel):
    """Schema for adding to watchlist via JSON body"""
    symbol: str = Field(..., max_length=20)


class WatchlistItem(BaseModel):
    symbol: str
    current_price: Optional[float]
    change_percent: Optional[float]
    added_at: datetime


class WatchlistResponse(BaseModel):
    items: List[WatchlistItem]
    total: int


# Bulk Operations
class BulkTransactionCreate(BaseModel):
    transactions: List[TransactionCreate]


class BulkTransactionResponse(BaseModel):
    successful: int
    failed: int
    transactions: List[TransactionResponse]
    errors: List[str]


# Notifications
class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    body: Optional[str] = None
    metadata: Optional[dict] = None
    read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread: int


class MarkReadResponse(BaseModel):
    updated: int


# Web push
class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    """Body sent from the frontend after PushManager.subscribe(). The
    shape matches the JSON returned by `subscription.toJSON()` so the
    frontend can POST it directly."""
    endpoint: str = Field(..., max_length=500)
    keys: PushKeys
    user_agent: Optional[str] = Field(default=None, max_length=255)


class PushSubscriptionResponse(BaseModel):
    id: int
    endpoint: str
    created_at: datetime

    class Config:
        from_attributes = True


class VapidPublicKeyResponse(BaseModel):
    public_key: str
