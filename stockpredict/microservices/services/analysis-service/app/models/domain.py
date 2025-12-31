"""Domain Models for Analysis Service"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class AnalysisType(enum.Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    COMBINED = "combined"


class AnalysisResult(Base):
    """Cached analysis results"""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    analysis_type = Column(SQLEnum(AnalysisType), nullable=False)

    # Technical indicators
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)
    ema_12 = Column(Float, nullable=True)
    ema_26 = Column(Float, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    atr = Column(Float, nullable=True)
    volume_sma = Column(Float, nullable=True)

    # Signals
    overall_signal = Column(String(20), nullable=True)  # buy, sell, hold
    signal_strength = Column(Float, nullable=True)  # 0-1
    technical_score = Column(Float, nullable=True)  # -100 to 100

    # Additional data
    indicators_data = Column(JSON, nullable=True)
    support_levels = Column(JSON, nullable=True)
    resistance_levels = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class ScreenerConfig(Base):
    """User-saved screener configurations"""
    __tablename__ = "screener_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Filter criteria
    filters = Column(JSON, nullable=False)  # List of filter conditions
    sort_by = Column(String(50), default="symbol")
    sort_order = Column(String(10), default="asc")

    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScreenerResult(Base):
    """Cached screener results"""
    __tablename__ = "screener_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(Integer, nullable=True, index=True)
    filter_hash = Column(String(64), nullable=False, index=True)  # Hash of filter criteria

    results = Column(JSON, nullable=False)  # List of matching symbols with data
    total_matches = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class FundamentalData(Base):
    """Cached fundamental analysis data"""
    __tablename__ = "fundamental_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True, index=True)

    # Valuation
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)
    ps_ratio = Column(Float, nullable=True)
    peg_ratio = Column(Float, nullable=True)
    ev_ebitda = Column(Float, nullable=True)

    # Profitability
    roe = Column(Float, nullable=True)  # Return on Equity
    roa = Column(Float, nullable=True)  # Return on Assets
    profit_margin = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)
    gross_margin = Column(Float, nullable=True)

    # Growth
    revenue_growth = Column(Float, nullable=True)
    earnings_growth = Column(Float, nullable=True)
    book_value_growth = Column(Float, nullable=True)

    # Financial Health
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)
    debt_to_equity = Column(Float, nullable=True)
    interest_coverage = Column(Float, nullable=True)

    # Dividends
    dividend_yield = Column(Float, nullable=True)
    payout_ratio = Column(Float, nullable=True)

    # Market Data
    market_cap = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)

    # Scores
    fundamental_score = Column(Float, nullable=True)  # 0-100
    value_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    growth_score = Column(Float, nullable=True)

    # Additional data
    raw_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
