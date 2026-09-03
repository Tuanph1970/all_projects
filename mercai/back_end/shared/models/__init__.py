"""
Shared models for Mercai Microservices
"""
from .user import User, UserRole
from .product import Product, ProductImage, Category, ProductVideo, PriceHistory
from .cart import Cart, CartItem
from .order import Order, OrderItem, OrderStatus, PaymentStatus
from .chat import ChatRoom, Message
from .review import Review
from .address import ShippingAddress
from .seller_profile import SellerProfile, StoreTheme
from .seller_category import SellerCategory
from .analytics import SearchLog
from .ai import AiSuggestion
from .intel import (
    TrackedComparable, ComparableObservation, CategoryBenchmark,
    RejectedHostRequest,
)

__all__ = [
    # User
    "User",
    "UserRole",
    # Product
    "Product",
    "ProductImage",
    "Category",
    "ProductVideo",
    "PriceHistory",
    # Cart
    "Cart",
    "CartItem",
    # Order
    "Order",
    "OrderItem",
    "OrderStatus",
    "PaymentStatus",
    # Chat
    "ChatRoom",
    "Message",
    # Review
    "Review",
    # Address
    "ShippingAddress",
    # Seller
    "SellerProfile",
    "StoreTheme",
    "SellerCategory",
    # Telemetry
    "SearchLog",
    # AI
    "AiSuggestion",
    # Price intelligence
    "TrackedComparable",
    "ComparableObservation",
    "CategoryBenchmark",
    "RejectedHostRequest",
]