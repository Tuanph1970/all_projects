"""
Domain Models - SQLAlchemy ORM models for stock data service
"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    BigInteger,
    Index,
)
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Industry(Base):
    """Industry/Sector model"""
    __tablename__ = "industries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("industries.id"), nullable=True)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    companies = relationship("Company", back_populates="industry")
    children = relationship("Industry", backref="parent", remote_side=[id])

    def __repr__(self):
        return f"<Industry(id={self.id}, code={self.code}, name={self.name})>"


class Company(Base):
    """Company/Stock model"""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    exchange = Column(String(20), nullable=False, index=True)  # HOSE, HNX, UPCOM
    industry_id = Column(Integer, ForeignKey("industries.id"), nullable=True)

    # Company details
    listing_date = Column(Date, nullable=True)
    outstanding_shares = Column(BigInteger, nullable=True)
    market_cap = Column(BigInteger, nullable=True)
    website = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_tradeable = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)

    # Relationships
    industry = relationship("Industry", back_populates="companies")
    prices = relationship("StockPrice", back_populates="company", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_company_exchange", "exchange"),
        Index("idx_company_industry", "industry_id"),
    )

    def __repr__(self):
        return f"<Company(symbol={self.symbol}, name={self.name})>"


class StockPrice(Base):
    """Stock price history model"""
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)

    # OHLCV data
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=True)
    value = Column(BigInteger, nullable=True)  # Trading value

    # Adjusted close.
    #
    # The upstream source (vnstock/VCI) already returns a BACK-ADJUSTED series: when a
    # bonus issue or stock dividend changes the share count, every prior price in the
    # history is restated. Verified against TCB's 1:1 bonus issue (ex-date June 2024),
    # whose series runs smoothly through the event at the post-bonus level, and ACB's
    # 2023 stock dividend. So `close` IS the adjusted close, and this column mirrors it.
    #
    # It is populated rather than left NULL because a NULL here reads as "unadjusted" to
    # any consumer computing a return, which is the opposite of the truth (Backlog #56).
    #
    # Scope: adjusted for share-count events. Cash-dividend adjustment is NOT verified —
    # treat this as capital-adjusted, not total-return.
    adj_close = Column(Float, nullable=True)

    # Change metrics
    change = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="prices")

    # Indexes
    __table_args__ = (
        Index("idx_price_company_date", "company_id", "date", unique=True),
        Index("idx_price_date", "date"),
    )

    def __repr__(self):
        return f"<StockPrice(company_id={self.company_id}, date={self.date}, close={self.close})>"


class MarketIndex(Base):
    """Market index model"""
    __tablename__ = "market_indices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, index=True)  # VNINDEX, VN30, HNX
    name = Column(String(255), nullable=False)
    date = Column(Date, nullable=False, index=True)

    # Index values
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=True)
    value = Column(BigInteger, nullable=True)

    # Change metrics
    change = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_market_index_code_date", "code", "date", unique=True),
    )

    def __repr__(self):
        return f"<MarketIndex(code={self.code}, date={self.date}, close={self.close})>"


class PriceBoard(Base):
    """Cached price board data from Vietcap API"""
    __tablename__ = "tbl_price_board"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    stock_group = Column(String(20), nullable=False, index=True)

    # Reference prices
    ref_price = Column(Float, nullable=True)
    ceiling = Column(Float, nullable=True)
    floor = Column(Float, nullable=True)

    # Match price data
    match_price = Column(Float, nullable=True)
    match_qty = Column(BigInteger, nullable=True)
    match_value = Column(BigInteger, nullable=True)
    change = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    total_qty = Column(BigInteger, nullable=True)
    total_value = Column(BigInteger, nullable=True)
    highest = Column(Float, nullable=True)
    lowest = Column(Float, nullable=True)
    open_price = Column(Float, nullable=True)
    average_price = Column(Float, nullable=True)

    # Bid prices (3 levels)
    buy_price_1 = Column(Float, nullable=True)
    buy_qty_1 = Column(BigInteger, nullable=True)
    buy_price_2 = Column(Float, nullable=True)
    buy_qty_2 = Column(BigInteger, nullable=True)
    buy_price_3 = Column(Float, nullable=True)
    buy_qty_3 = Column(BigInteger, nullable=True)

    # Ask prices (3 levels)
    sell_price_1 = Column(Float, nullable=True)
    sell_qty_1 = Column(BigInteger, nullable=True)
    sell_price_2 = Column(Float, nullable=True)
    sell_qty_2 = Column(BigInteger, nullable=True)
    sell_price_3 = Column(Float, nullable=True)
    sell_qty_3 = Column(BigInteger, nullable=True)

    # Metadata
    exchange = Column(String(20), nullable=True)
    # VCI emits values like TRADING_RESTRICTION_ACTIVATED (29 chars); was String(20)
    trading_status = Column(String(64), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_price_board_group_symbol", "stock_group", "symbol", unique=True),
    )

    def __repr__(self):
        return f"<PriceBoard(symbol={self.symbol}, group={self.stock_group}, match_price={self.match_price})>"


class CompanyProfile(Base):
    """Cached company profile data from vnstock"""
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    company_profile = Column(Text, nullable=True)
    history = Column(Text, nullable=True)
    industry = Column(String(255), nullable=True)
    industry_l2 = Column(String(255), nullable=True)
    industry_l3 = Column(String(255), nullable=True)
    charter_capital = Column(Float, nullable=True)
    issue_share = Column(Float, nullable=True)
    outstanding_share = Column(BigInteger, nullable=True)
    foreign_percent = Column(Float, nullable=True)
    free_float_rate = Column(Float, nullable=True)
    no_shareholders = Column(Integer, nullable=True)
    no_employees = Column(Integer, nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CompanyProfile(ticker={self.ticker})>"


class FinancialStatement(Base):
    """Cached financial statement data from vnstock"""
    __tablename__ = "financial_statements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    statement_type = Column(String(50), nullable=False)  # income_statement, cash_flow, balance_sheet, ratio
    period = Column(String(20), nullable=False)  # annual, quarter
    report_year = Column(Integer, nullable=True)
    data = Column(Text, nullable=False)  # JSON-encoded dict for one reporting row
    synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_fin_stmt_lookup", "symbol", "statement_type", "period"),
    )
