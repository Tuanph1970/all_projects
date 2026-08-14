from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from shared.database import Base
import enum

class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    SELLER = "seller"
    DUAL = "dual"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=True)
    
    # Profile info
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Seller specific fields
    shop_name = Column(String(100), nullable=True)
    shop_description = Column(Text, nullable=True)
    business_license = Column(String(100), nullable=True)
    
    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    products = relationship("Product", back_populates="seller")
    cart = relationship("Cart", back_populates="user", uselist=False)
    orders_as_customer = relationship("Order", foreign_keys="Order.customer_id", back_populates="customer")
    orders_as_seller = relationship("Order", foreign_keys="Order.seller_id", back_populates="seller")
    reviews_given = relationship("Review", foreign_keys="Review.reviewer_id", back_populates="reviewer")
    reviews_received = relationship("Review", foreign_keys="Review.seller_id", back_populates="seller")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")
    shipping_addresses = relationship("ShippingAddress", back_populates="user")
    seller_profile = relationship("SellerProfile", back_populates="user", uselist=False)
    
    @property
    def is_seller(self) -> bool:
        """Check if user has seller role"""
        return self.role in [UserRole.SELLER, UserRole.DUAL]
    
    @property
    def first_name(self) -> str:
        """Extract first name from full_name"""
        return self.full_name.split(' ')[0] if self.full_name else ""
    
    @property
    def last_name(self) -> str:
        """Extract last name from full_name"""
        parts = self.full_name.split(' ') if self.full_name else []
        return ' '.join(parts[1:]) if len(parts) > 1 else ""