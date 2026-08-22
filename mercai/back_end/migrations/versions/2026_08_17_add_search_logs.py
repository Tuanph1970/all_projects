"""Add search_logs table

Revision ID: 2026_08_17_search_logs
Revises: 2026_03_02_add_product_videos
Create Date: 2026-08-17

Captures buyer search intent, which is currently recorded nowhere and cannot
be reconstructed after the fact. `result_count = 0` is the assortment-gap
signal: a buyer looked for something this marketplace does not sell.

See docs/ai-features/01-instrumentation.md (PR 1).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_08_17_search_logs'
down_revision = '2026_03_02_add_product_videos'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'search_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('query_text', sa.String(length=500), nullable=True),
        sa.Column('query_norm', sa.String(length=500), nullable=True),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('result_count', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        # No FK to users: telemetry outlives the account that produced it, and
        # a constraint here would put high-volume inserts in contention with
        # the users table.
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('anon_id', sa.String(length=64), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Aggregates group on the normalised query.
    op.create_index('ix_search_logs_norm', 'search_logs', ['query_norm'])
    # "what did buyers search for and find nothing?" over a time window.
    op.create_index('ix_search_logs_zero', 'search_logs', ['result_count', 'created_at'])
    # Time-range scans and the retention purge of query_text / anon_id.
    op.create_index('ix_search_logs_created', 'search_logs', ['created_at'])
    op.create_index('ix_search_logs_user', 'search_logs', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_search_logs_user', table_name='search_logs')
    op.drop_index('ix_search_logs_created', table_name='search_logs')
    op.drop_index('ix_search_logs_zero', table_name='search_logs')
    op.drop_index('ix_search_logs_norm', table_name='search_logs')
    op.drop_table('search_logs')
