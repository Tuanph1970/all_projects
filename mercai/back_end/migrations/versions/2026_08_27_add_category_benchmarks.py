"""add category_benchmarks

Revision ID: 2026_08_27_category_benchmarks
Revises: 2026_08_27_intel_comparables
Create Date: 2026-08-27

Hand-written, like its predecessors -- see 01-instrumentation.md on why
autogenerate is not safe unattended in this repo.
"""
import sqlalchemy as sa
from alembic import op

revision = '2026_08_27_category_benchmarks'
down_revision = '2026_08_27_intel_comparables'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'category_benchmarks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.String(length=30), nullable=False),
        sa.Column('external_category_id', sa.String(length=40), nullable=False),
        sa.Column('external_category_label', sa.String(length=255), nullable=True),
        # By NAME, not id: category ids differ between environments.
        sa.Column('mercai_category_name', sa.String(length=100), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pages_sampled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('catalogue_total', sa.Integer(), nullable=True),
        sa.Column('p25', sa.Numeric(12, 2), nullable=True),
        sa.Column('median', sa.Numeric(12, 2), nullable=True),
        sa.Column('p75', sa.Numeric(12, 2), nullable=True),
        sa.Column('price_min', sa.Numeric(12, 2), nullable=True),
        sa.Column('price_max', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='VND'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='ok'),
        sa.Column('computed_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('source', 'external_category_id', name='uq_cb_source_category'),
    )
    op.create_index('ix_cb_mercai_category', 'category_benchmarks',
                    ['mercai_category_name', 'computed_at'])


def downgrade():
    op.drop_index('ix_cb_mercai_category', table_name='category_benchmarks')
    op.drop_table('category_benchmarks')
