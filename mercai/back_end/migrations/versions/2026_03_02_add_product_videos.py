"""Add product_videos table

Revision ID: 2026_03_02_add_product_videos
Revises: 2026_01_24_seller_category_to_products
Create Date: 2026-03-02

This migration adds:
- product_videos table for storing product video information
- Supports video URL, thumbnail, duration, resolution, and metadata
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_03_02_add_product_videos'
down_revision = '2026_01_24_seller_category_to_products'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_videos table
    op.create_table(
        'product_videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('video_url', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('alt_text', sa.String(length=255), nullable=True),
        sa.Column('duration_seconds', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('file_size_mb', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('resolution', sa.String(length=20), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True, default=False),
        sa.Column('order_index', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better query performance
    op.create_index('ix_product_videos_product_id', 'product_videos', ['product_id'])
    op.create_index('ix_product_videos_is_primary', 'product_videos', ['is_primary'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_product_videos_is_primary', table_name='product_videos')
    op.drop_index('ix_product_videos_product_id', table_name='product_videos')

    # Drop product_videos table
    op.drop_table('product_videos')
