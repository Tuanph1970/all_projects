from sqlalchemy import Column, Integer, String, Text,  Boolean, DateTime, ForeignKey
from sqlalchemy import Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

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
    slug = Column(String(255), nullable=True, unique=True, index=True)  # SEO-friendly URL
    description = Column(Text, nullable=False)
    price = Column(Numeric(10, 2), nullable=False, index=True)
    original_price = Column(Numeric(10, 2), nullable=True)  # For discount tracking
    discount_percentage = Column(Numeric(5, 2), nullable=True)  # Discount percentage
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

    # SEO and discovery
    tags = Column(String(500), nullable=True)  # comma-separated tags
    sku = Column(String(50), unique=True, index=True, nullable=True)

    # Foreign keys
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    seller = relationship("User", back_populates="products")
    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    attributes = relationship("ProductAttribute", back_populates="product", cascade="all, delete-orphan")
    specifications = relationship("ProductSpecification", back_populates="product", cascade="all, delete-orphan")
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


class Brand(Base):
    """Brand model for product brands/manufacturers"""
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    website = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    products = relationship("Product", back_populates="brand")


class ProductVariant(Base):
    """Product variant model for different sizes, colors, etc."""
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Large - Blue"

    # Variant attributes
    size = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)
    material = Column(String(100), nullable=True)
    weight = Column(Numeric(5, 2), nullable=True)
    dimensions = Column(String(100), nullable=True)

    # Pricing and inventory
    price = Column(Numeric(10, 2), nullable=False)
    price_adjustment = Column(Numeric(10, 2), default=0)  # Difference from base price
    quantity_available = Column(Integer, nullable=False, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # Image for this variant
    image_url = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="variants")


class PriceHistory(Base):
    """Track price changes for products"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True, index=True)

    old_price = Column(Numeric(10, 2), nullable=False)
    new_price = Column(Numeric(10, 2), nullable=False)
    change_reason = Column(String(255), nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="price_history")
    variant = relationship("ProductVariant")


class ProductTag(Base):
    """Tags associated with products (many-to-many)"""
    __tablename__ = "product_tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    slug = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProductTagAssociation(Base):
    """Association table for products and tags"""
    __tablename__ = "product_tag_associations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("product_tags.id"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProductAttribute(Base):
    """Custom attributes for products"""
    __tablename__ = "product_attributes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)  # e.g., "Firing Temperature", "Glaze Type"
    value = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=True)  # e.g., "°C", "kg"
    display_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="attributes")


class ProductSpecification(Base):
    """Detailed specifications for products"""
    __tablename__ = "product_specifications"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    group_name = Column(String(100), nullable=True)  # e.g., "Physical", "Technical"
    spec_name = Column(String(100), nullable=False)
    spec_value = Column(String(255), nullable=False)
    display_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("Product", back_populates="specifications")