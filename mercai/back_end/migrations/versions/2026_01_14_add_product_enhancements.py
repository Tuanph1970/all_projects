"""Add product enhancements: variants, brands, price history, tags, attributes, specifications

Revision ID: 2026_01_14_product_enhancements
Revises:
Create Date: 2026-01-14

This migration adds support for:
- Product slug field for SEO-friendly URLs
- Product discount fields (original_price, discount_percentage)
- Brand management system
- Product variants (sizes, colors, etc.)
- Price history tracking
- Product tags (many-to-many)
- Custom product attributes
- Product specifications
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '2026_01_14_product_enhancements'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create brands table
    op.create_table(
        'brands',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_brands_id', 'brands', ['id'])
    op.create_index('ix_brands_name', 'brands', ['name'], unique=True)
    op.create_index('ix_brands_slug', 'brands', ['slug'], unique=True)

    # Add new columns to products table
    op.add_column('products', sa.Column('slug', sa.String(255), nullable=True))
    op.add_column('products', sa.Column('original_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('products', sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=True))
    op.add_column('products', sa.Column('brand_id', sa.Integer(), nullable=True))

    op.create_index('ix_products_slug', 'products', ['slug'], unique=True)
    op.create_index('ix_products_brand_id', 'products', ['brand_id'])

    op.create_foreign_key(
        'fk_products_brand_id',
        'products', 'brands',
        ['brand_id'], ['id']
    )

    # Create product_variants table
    op.create_table(
        'product_variants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('size', sa.String(50), nullable=True),
        sa.Column('color', sa.String(50), nullable=True),
        sa.Column('material', sa.String(100), nullable=True),
        sa.Column('weight', sa.Numeric(5, 2), nullable=True),
        sa.Column('dimensions', sa.String(100), nullable=True),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('price_adjustment', sa.Numeric(10, 2), default=0),
        sa.Column('quantity_available', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'])
    )
    op.create_index('ix_product_variants_id', 'product_variants', ['id'])
    op.create_index('ix_product_variants_product_id', 'product_variants', ['product_id'])
    op.create_index('ix_product_variants_sku', 'product_variants', ['sku'], unique=True)

    # Create price_history table
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('variant_id', sa.Integer(), nullable=True),
        sa.Column('old_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('new_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('change_reason', sa.String(255), nullable=True),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['variant_id'], ['product_variants.id']),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'])
    )
    op.create_index('ix_price_history_id', 'price_history', ['id'])
    op.create_index('ix_price_history_product_id', 'price_history', ['product_id'])
    op.create_index('ix_price_history_variant_id', 'price_history', ['variant_id'])

    # Create product_tags table
    op.create_table(
        'product_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('slug', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_product_tags_id', 'product_tags', ['id'])
    op.create_index('ix_product_tags_name', 'product_tags', ['name'])
    op.create_index('ix_product_tags_slug', 'product_tags', ['slug'], unique=True)

    # Create product_tag_associations table (many-to-many)
    op.create_table(
        'product_tag_associations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['tag_id'], ['product_tags.id'])
    )
    op.create_index('ix_product_tag_associations_id', 'product_tag_associations', ['id'])
    op.create_index('ix_product_tag_associations_product_id', 'product_tag_associations', ['product_id'])
    op.create_index('ix_product_tag_associations_tag_id', 'product_tag_associations', ['tag_id'])

    # Create product_attributes table
    op.create_table(
        'product_attributes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('value', sa.String(255), nullable=False),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('display_order', sa.Integer(), default=0),
        sa.Column('is_visible', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'])
    )
    op.create_index('ix_product_attributes_id', 'product_attributes', ['id'])
    op.create_index('ix_product_attributes_product_id', 'product_attributes', ['product_id'])

    # Create product_specifications table
    op.create_table(
        'product_specifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('group_name', sa.String(100), nullable=True),
        sa.Column('spec_name', sa.String(100), nullable=False),
        sa.Column('spec_value', sa.String(255), nullable=False),
        sa.Column('display_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'])
    )
    op.create_index('ix_product_specifications_id', 'product_specifications', ['id'])
    op.create_index('ix_product_specifications_product_id', 'product_specifications', ['product_id'])


def downgrade() -> None:
    # Drop tables in reverse order of dependencies
    op.drop_table('product_specifications')
    op.drop_table('product_attributes')
    op.drop_table('product_tag_associations')
    op.drop_table('product_tags')
    op.drop_table('price_history')
    op.drop_table('product_variants')

    # Remove foreign key and columns from products
    op.drop_constraint('fk_products_brand_id', 'products', type_='foreignkey')
    op.drop_index('ix_products_brand_id', table_name='products')
    op.drop_index('ix_products_slug', table_name='products')
    op.drop_column('products', 'brand_id')
    op.drop_column('products', 'discount_percentage')
    op.drop_column('products', 'original_price')
    op.drop_column('products', 'slug')

    # Drop brands table
    op.drop_index('ix_brands_slug', table_name='brands')
    op.drop_index('ix_brands_name', table_name='brands')
    op.drop_index('ix_brands_id', table_name='brands')
    op.drop_table('brands')
