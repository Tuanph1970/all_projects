"""
Test data factories for generating test fixtures.

Uses factory pattern to create consistent test data.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass, field


def random_string(length: int = 8) -> str:
    """Generate a random string."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def random_email() -> str:
    """Generate a random email address."""
    return f"test_{random_string()}@test.com"


def random_password() -> str:
    """Generate a valid password."""
    return f"Test{random_string(4)}123!"


@dataclass
class UserFactory:
    """Factory for generating user test data."""

    username: str = field(default_factory=lambda: f"user_{random_string()}")
    email: str = field(default_factory=random_email)
    password: str = field(default_factory=random_password)
    first_name: str = "Test"
    last_name: str = "User"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }

    @classmethod
    def create(cls, **overrides) -> "UserFactory":
        """Create a user with optional overrides."""
        return cls(**overrides)

    @classmethod
    def create_batch(cls, count: int, **overrides) -> list["UserFactory"]:
        """Create multiple users."""
        return [cls.create(**overrides) for _ in range(count)]


@dataclass
class PortfolioFactory:
    """Factory for generating portfolio test data."""

    name: str = field(default_factory=lambda: f"Portfolio_{random_string()}")
    description: str = "Test portfolio"
    initial_cash: float = 100000000.0  # 100 million VND

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            "name": self.name,
            "description": self.description,
            "initial_cash": self.initial_cash,
        }

    @classmethod
    def create(cls, **overrides) -> "PortfolioFactory":
        """Create a portfolio with optional overrides."""
        return cls(**overrides)


@dataclass
class HoldingFactory:
    """Factory for generating holding test data."""

    symbol: str = "VNM"
    quantity: int = 100
    average_price: float = 75000.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "average_price": self.average_price,
        }

    @classmethod
    def create(cls, **overrides) -> "HoldingFactory":
        """Create a holding with optional overrides."""
        return cls(**overrides)

    @classmethod
    def create_diversified(cls) -> list["HoldingFactory"]:
        """Create a diversified set of holdings."""
        stocks = [
            ("VNM", 100, 75000),
            ("FPT", 50, 90000),
            ("VIC", 200, 50000),
            ("HPG", 150, 25000),
            ("MWG", 30, 60000),
        ]
        return [
            cls(symbol=s, quantity=q, average_price=p)
            for s, q, p in stocks
        ]


@dataclass
class TransactionFactory:
    """Factory for generating transaction test data."""

    symbol: str = "VNM"
    type: str = "buy"  # buy or sell
    quantity: int = 100
    price: float = 75000.0
    date: Optional[str] = None

    def __post_init__(self):
        if self.date is None:
            self.date = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            "symbol": self.symbol,
            "type": self.type,
            "quantity": self.quantity,
            "price": self.price,
            "date": self.date,
        }

    @classmethod
    def create_buy(cls, symbol: str = "VNM", quantity: int = 100, price: float = 75000.0) -> "TransactionFactory":
        """Create a buy transaction."""
        return cls(symbol=symbol, type="buy", quantity=quantity, price=price)

    @classmethod
    def create_sell(cls, symbol: str = "VNM", quantity: int = 50, price: float = 80000.0) -> "TransactionFactory":
        """Create a sell transaction."""
        return cls(symbol=symbol, type="sell", quantity=quantity, price=price)

    @classmethod
    def create_history(cls, symbol: str = "VNM", count: int = 10) -> list["TransactionFactory"]:
        """Create a transaction history."""
        transactions = []
        base_price = 70000.0
        owned = 0

        for i in range(count):
            date = (datetime.now() - timedelta(days=count - i)).isoformat()

            if owned == 0 or random.random() > 0.3:
                # Buy
                quantity = random.randint(50, 200)
                price = base_price * (1 + random.uniform(-0.05, 0.1))
                transactions.append(cls(
                    symbol=symbol,
                    type="buy",
                    quantity=quantity,
                    price=price,
                    date=date
                ))
                owned += quantity
                base_price = price
            else:
                # Sell
                sell_quantity = random.randint(1, min(owned, 100))
                price = base_price * (1 + random.uniform(-0.03, 0.07))
                transactions.append(cls(
                    symbol=symbol,
                    type="sell",
                    quantity=sell_quantity,
                    price=price,
                    date=date
                ))
                owned -= sell_quantity
                base_price = price

        return transactions


@dataclass
class AlertFactory:
    """Factory for generating price alert test data."""

    symbol: str = "VNM"
    target_price: float = 80000.0
    condition: str = "above"  # above or below
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API requests."""
        return {
            "symbol": self.symbol,
            "target_price": self.target_price,
            "condition": self.condition,
            "is_active": self.is_active,
        }

    @classmethod
    def create_above(cls, symbol: str = "VNM", price: float = 80000.0) -> "AlertFactory":
        """Create an 'above' price alert."""
        return cls(symbol=symbol, target_price=price, condition="above")

    @classmethod
    def create_below(cls, symbol: str = "VNM", price: float = 70000.0) -> "AlertFactory":
        """Create a 'below' price alert."""
        return cls(symbol=symbol, target_price=price, condition="below")


# Stock symbols for testing
VIETNAMESE_STOCK_SYMBOLS = [
    "VNM", "FPT", "VIC", "VHM", "HPG", "MWG", "TCB", "VCB", "BID", "CTG",
    "VPB", "MBB", "ACB", "STB", "SHB", "VRE", "NVL", "DIG", "KDH", "DXG",
    "VJC", "HVN", "GMD", "PVD", "GAS", "PLX", "POW", "NT2", "REE", "SAB"
]


def random_stock_symbol() -> str:
    """Get a random Vietnamese stock symbol."""
    return random.choice(VIETNAMESE_STOCK_SYMBOLS)


def random_stock_symbols(count: int = 5) -> list[str]:
    """Get random stock symbols without duplicates."""
    return random.sample(VIETNAMESE_STOCK_SYMBOLS, min(count, len(VIETNAMESE_STOCK_SYMBOLS)))
