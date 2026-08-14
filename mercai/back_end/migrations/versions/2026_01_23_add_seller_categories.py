"""Add seller_categories table for seller-specific product category management

Revision ID: 2026_01_23_seller_categories
Revises: 2026_01_21_order_status_history
Create Date: 2026-01-23

This migration adds:
- seller_categories table for tree-structured seller-specific categories
- Maximum depth of 4 levels enforced at application level
- Multi-tenant isolation via seller_id foreign key
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_01_23_seller_categories'
down_revision = '2026_01_21_order_status_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create seller_categories table
    op.create_table(
        'seller_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(120), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, default=1),
        sa.Column('path', sa.String(255), nullable=True),
        sa.Column('display_order', sa.Integer(), default=0),
        sa.Column('icon_url', sa.String(500), nullable=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('product_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['seller_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['seller_categories.id'], ondelete='CASCADE')
    )

    # Create indexes
    op.create_index('ix_seller_categories_id', 'seller_categories', ['id'])
    op.create_index('ix_seller_categories_seller_id', 'seller_categories', ['seller_id'])
    op.create_index('ix_seller_categories_parent_id', 'seller_categories', ['parent_id'])
    op.create_index('ix_seller_categories_seller_parent', 'seller_categories', ['seller_id', 'parent_id'])
    op.create_index('ix_seller_categories_seller_level', 'seller_categories', ['seller_id', 'level'])
    op.create_index('ix_seller_categories_seller_active', 'seller_categories', ['seller_id', 'is_active'])
    op.create_index('ix_seller_categories_path', 'seller_categories', ['path'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_seller_categories_path', table_name='seller_categories')
    op.drop_index('ix_seller_categories_seller_active', table_name='seller_categories')
    op.drop_index('ix_seller_categories_seller_level', table_name='seller_categories')
    op.drop_index('ix_seller_categories_seller_parent', table_name='seller_categories')
    op.drop_index('ix_seller_categories_parent_id', table_name='seller_categories')
    op.drop_index('ix_seller_categories_seller_id', table_name='seller_categories')
    op.drop_index('ix_seller_categories_id', table_name='seller_categories')

    # Drop table
    op.drop_table('seller_categories')
