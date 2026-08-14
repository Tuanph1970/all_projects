"""Add order status history table for tracking status changes

Revision ID: 2026_01_21_order_status_history
Revises: 2026_01_14_product_enhancements
Create Date: 2026-01-21

This migration adds:
- Order status history table for audit trail of status changes
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_01_21_order_status_history'
down_revision = '2026_01_14_product_enhancements'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create order_status_history table
    op.create_table(
        'order_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('old_status', sa.Enum('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded', name='orderstatus'), nullable=True),
        sa.Column('new_status', sa.Enum('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded', name='orderstatus'), nullable=False),
        sa.Column('changed_by_id', sa.Integer(), nullable=True),
        sa.Column('changed_by_role', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index('ix_order_status_history_id', 'order_status_history', ['id'])
    op.create_index('ix_order_status_history_order_id', 'order_status_history', ['order_id'])
    op.create_index('ix_order_status_history_changed_at', 'order_status_history', ['changed_at'])


def downgrade() -> None:
    op.drop_index('ix_order_status_history_changed_at', table_name='order_status_history')
    op.drop_index('ix_order_status_history_order_id', table_name='order_status_history')
    op.drop_index('ix_order_status_history_id', table_name='order_status_history')
    op.drop_table('order_status_history')
