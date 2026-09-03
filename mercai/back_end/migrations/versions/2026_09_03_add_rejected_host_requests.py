"""add rejected_host_requests

Revision ID: 2026_09_03_rejected_hosts
Revises: 2026_08_27_category_benchmarks
Create Date: 2026-09-03

The adapter worklist (docs/ai-features/05-price-intelligence.md section 12,
point 2). `POST /comparables` refuses an unsupported host at add-time without
leaving a row behind, which is right for tracked_comparables and wrong for the
signal: the hosts sellers keep asking for are exactly the list that says which
adapter to write next, and until now they were discarded with the 422.

Hand-written, per 01-instrumentation.md -- `alembic revision --autogenerate`
still proposes dropping the six orphan tables from
2026_01_14_add_product_enhancements. Read any generated file before applying it.
"""
import sqlalchemy as sa
from alembic import op

revision = '2026_09_03_rejected_hosts'
down_revision = '2026_08_27_category_benchmarks'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rejected_host_requests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('sample_url', sa.String(length=1000), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        # The grain is (host, seller), not (host, attempt): ranking a host by
        # raw attempts would put one seller pasting forty links above twelve
        # sellers pasting one each, and breadth of demand is what justifies the
        # work. The constraint is what makes COUNT(*) mean "distinct sellers".
        sa.UniqueConstraint('host', 'seller_id', name='uq_rhr_host_seller'),
    )
    op.create_index('ix_rejected_host_requests_host', 'rejected_host_requests', ['host'])
    op.create_index('ix_rejected_host_requests_seller_id',
                    'rejected_host_requests', ['seller_id'])
    op.create_index('ix_rhr_host_last_seen', 'rejected_host_requests',
                    ['host', 'last_seen_at'])

    # No foreign key to users on purpose. This is telemetry about intent, and
    # it should survive a seller being deleted -- the demand for a source was
    # still real. The seller_id is only ever counted, never joined back.


def downgrade():
    op.drop_index('ix_rhr_host_last_seen', table_name='rejected_host_requests')
    op.drop_index('ix_rejected_host_requests_seller_id',
                  table_name='rejected_host_requests')
    op.drop_index('ix_rejected_host_requests_host', table_name='rejected_host_requests')
    op.drop_table('rejected_host_requests')
