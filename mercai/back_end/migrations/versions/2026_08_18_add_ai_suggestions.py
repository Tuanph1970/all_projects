"""Add ai_suggestions table

Revision ID: 2026_08_18_ai_suggestions
Revises: 2026_08_17_search_logs
Create Date: 2026-08-18

Shared by every AI feature (listing optimizer, chat copilot, review
intelligence). Records what was suggested to a seller and what they did with
it -- the acceptance rate is how each feature's rollout is judged.

See docs/ai-features/02-listing-optimizer.md section 2.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_08_18_ai_suggestions'
down_revision = '2026_08_17_search_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_suggestions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        # No FK to users: these rows are analytics that outlive the account.
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('feature', sa.String(length=40), nullable=False),
        sa.Column('entity_type', sa.String(length=40), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),

        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('suggestion', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('accepted_fields', sa.JSON(), nullable=True),

        sa.Column('model', sa.String(length=80), nullable=False),
        sa.Column('prompt_version', sa.String(length=20), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('error', sa.String(length=255), nullable=True),

        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_ai_sugg_seller_feature', 'ai_suggestions',
                    ['seller_id', 'feature', 'created_at'])
    op.create_index('ix_ai_sugg_entity', 'ai_suggestions',
                    ['entity_type', 'entity_id'])
    op.create_index('ix_ai_sugg_hash', 'ai_suggestions', ['input_hash'])
    op.create_index('ix_ai_sugg_status', 'ai_suggestions',
                    ['feature', 'status', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_ai_sugg_status', table_name='ai_suggestions')
    op.drop_index('ix_ai_sugg_hash', table_name='ai_suggestions')
    op.drop_index('ix_ai_sugg_entity', table_name='ai_suggestions')
    op.drop_index('ix_ai_sugg_seller_feature', table_name='ai_suggestions')
    op.drop_table('ai_suggestions')
