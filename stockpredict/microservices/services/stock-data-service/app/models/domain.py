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

    # Adjusted prices
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
