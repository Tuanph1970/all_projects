"""
Seller Category Model - Tree structure for seller-specific product categories
Each seller manages their own category hierarchy (max 4 levels)
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, validates
from shared.database import Base


class SellerCategory(Base):
    """
    Seller-specific product category with hierarchical tree structure.

    Features:
    - Multi-tenant: Each seller has their own category tree
    - Max 4 levels deep: Root (1) -> Child (2) -> Grandchild (3) -> Great-grandchild (4)
    - Self-referential for parent-child relationships
    - Soft ordering via display_order
    - Path storage for efficient tree traversal
    """
    __tablename__ = "seller_categories"

    id = Column(Integer, primary_key=True, index=True)

    # Seller ownership - multi-tenant isolation
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Category details
    name = Column(String(100), nullable=False)
    slug = Column(String(120), nullable=True)  # URL-friendly name
    description = Column(Text, nullable=True)

    # Tree structure
    parent_id = Column(Integer, ForeignKey("seller_categories.id", ondelete="CASCADE"), nullable=True, index=True)
    level = Column(Integer, nullable=False, default=1)  # 1-4, root=1
    path = Column(String(255), nullable=True)  # e.g., "1/5/12" for efficient tree queries

    # Display & ordering
    display_order = Column(Integer, default=0)
    icon_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    product_count = Column(Integer, default=0)  # Cached count for performance

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    seller = relationship("User", foreign_keys=[seller_id])
    parent = relationship("SellerCategory", remote_side=[id], back_populates="children", foreign_keys=[parent_id])
    children = relationship("SellerCategory", back_populates="parent", cascade="all, delete-orphan", foreign_keys=[parent_id])
    products = relationship("Product", back_populates="seller_category")

    # Indexes for performance
    __table_args__ = (
        Index('ix_seller_categories_seller_parent', 'seller_id', 'parent_id'),
        Index('ix_seller_categories_seller_level', 'seller_id', 'level'),
        Index('ix_seller_categories_seller_active', 'seller_id', 'is_active'),
        Index('ix_seller_categories_path', 'path'),
    )

    @validates('level')
    def validate_level(self, key, level):
        """Ensure level doesn't exceed maximum depth of 4"""
        if level < 1 or level > 4:
            raise ValueError(f"Category level must be between 1 and 4, got {level}")
        return level

    def __repr__(self):
        return f"<SellerCategory(id={self.id}, name='{self.name}', seller_id={self.seller_id}, level={self.level})>"

    @property
    def is_root(self) -> bool:
        """Check if this is a root category"""
        return self.parent_id is None

    @property
    def can_have_children(self) -> bool:
        """Check if this category can have child categories (max level 4)"""
        return self.level < 4

    def get_full_path_name(self, separator: str = " > ") -> str:
        """
        Get full hierarchical path name.
        e.g., "Ceramics > Vases > Decorative"
        """
        names = [self.name]
        current = self.parent
        while current:
            names.insert(0, current.name)
            current = current.parent
        return separator.join(names)

    def update_path(self):
        """
        Update the path string based on parent hierarchy.
        Should be called when parent changes.
        """
        if self.parent:
            parent_path = self.parent.path or str(self.parent.id)
            self.path = f"{parent_path}/{self.id}"
        else:
            self.path = str(self.id) if self.id else None
