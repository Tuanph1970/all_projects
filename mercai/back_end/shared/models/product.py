from sqlalchemy import Column, Integer, String, Text,  Boolean, DateTime, ForeignKey
from sqlalchemy import Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from shared.database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    parent = relationship("Category", remote_side=[id])
    children = relationship("Category")
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    price = Column(Numeric(10, 2), nullable=False, index=True)
    quantity_available = Column(Integer, nullable=False, default=0)
    
    # Product details
    dimensions = Column(String(100), nullable=True)  # e.g., "10x15x8 cm"
    weight = Column(Numeric(5, 2), nullable=True)  # in kg
    material = Column(String(100), nullable=True)
    color = Column(String(50), nullable=True)
    technique = Column(String(100), nullable=True)
    
    # Business logic
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    minimum_order_quantity = Column(Integer, default=1)

    # Analytics
    view_count = Column(Integer, default=0, nullable=False)
    
    # SEO and discovery
    tags = Column(String(500), nullable=True)  # comma-separated tags
    sku = Column(String(50), unique=True, index=True, nullable=True)
    
    # Foreign keys
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    seller_category_id = Column(Integer, ForeignKey("seller_categories.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    seller = relationship("User", back_populates="products")
    category = relationship("Category", back_populates="products")
    seller_category = relationship("SellerCategory", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    videos = relationship("ProductVideo", back_populates="product", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    reviews = relationship("Review", back_populates="product")

class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)
    alt_text = Column(String(255), nullable=True)
    is_primary = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="images")


class PriceHistory(Base):
    """
    One row per price change, written in the same transaction as the change.

    Reliability class: LEDGER (see docs/ai-features/01-instrumentation.md).
    If this write fails, the price change must fail with it -- a price history
    that silently diverges from `products.price` is worse than none, because
    it yields confidently wrong elasticity analysis.

    The table predates this model: it was created by migration
    2026_01_14_add_product_enhancements but nothing ever wrote to it.
    """
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    # The column exists in the table with an FK to product_variants, but the
    # live schema has no ProductVariant model, so no ForeignKey is declared
    # here -- create_all() would fail resolving a table that is not in this
    # metadata. Always NULL until variants are modelled.
    variant_id = Column(Integer, nullable=True, index=True)

    old_price = Column(Numeric(10, 2), nullable=False)
    new_price = Column(Numeric(10, 2), nullable=False)

    # 'initial' | 'seller_update' | 'bulk_update'
    change_reason = Column(String(255), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    product = relationship("Product", back_populates="price_history")

    def __repr__(self):
        return (
            f"<PriceHistory(product_id={self.product_id}, "
            f"{self.old_price} -> {self.new_price}, reason={self.change_reason!r})>"
        )


class ProductVideo(Base):
    __tablename__ = "product_videos"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    alt_text = Column(String(255), nullable=True)
    duration_seconds = Column(Numeric(5, 2), nullable=True)
    file_size_mb = Column(Numeric(8, 2), nullable=True)
    resolution = Column(String(20), nullable=True)
    is_primary = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="videos")