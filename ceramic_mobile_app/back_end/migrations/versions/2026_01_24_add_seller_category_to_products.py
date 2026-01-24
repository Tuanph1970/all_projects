"""Add seller_category_id to products table

Revision ID: 2026_01_24_seller_category_products
Revises: 2026_01_23_seller_categories
Create Date: 2026-01-24

This migration adds:
- seller_category_id column to products table (references seller_categories)
- Makes category_id nullable for backward compatibility
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_01_24_seller_category_products'
down_revision = '2026_01_23_seller_categories'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add seller_category_id column to products table
    op.add_column(
        'products',
        sa.Column('seller_category_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_products_seller_category_id',
        'products',
        'seller_categories',
        ['seller_category_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index for seller_category_id
    op.create_index(
        'ix_products_seller_category_id',
        'products',
        ['seller_category_id']
    )

    # Make category_id nullable (for backward compatibility)
    op.alter_column(
        'products',
        'category_id',
        existing_type=sa.Integer(),
        nullable=True
    )


def downgrade() -> None:
    # Make category_id NOT NULL again
    op.alter_column(
        'products',
        'category_id',
        existing_type=sa.Integer(),
        nullable=False
    )

    # Drop index
    op.drop_index('ix_products_seller_category_id', table_name='products')

    # Drop foreign key constraint
    op.drop_constraint('fk_products_seller_category_id', 'products', type_='foreignkey')

    # Drop column
    op.drop_column('products', 'seller_category_id')
