"""add lead_states and lead_events

Lead Workflow v2 (PRD 2026-08-20): the five-status state machine plus its
append-only timeline. Schema only -- the data migration that folds the old
claim/review state into these tables is the next revision, so the two can be
rolled back independently.

Revision ID: a1b2c3d4e5f6
Revises: cf4ebe0689c1
Create Date: 2026-08-20 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'cf4ebe0689c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lead_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('assigned_to_id', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_actor_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['last_actor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    # UNIQUE, not just indexed: one lead state per company is the invariant the
    # claim race relies on (INSERT ... ON CONFLICT (company_id)).
    op.create_index(op.f('ix_lead_states_company_id'), 'lead_states', ['company_id'], unique=True)
    op.create_index('ix_lead_states_status_activity', 'lead_states', ['status', 'last_activity_at'], unique=False)
    op.create_index('ix_lead_states_assignee_status', 'lead_states', ['assigned_to_id', 'status'], unique=False)

    op.create_table(
        'lead_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=24), nullable=False),
        sa.Column('from_status', sa.String(length=16), nullable=True),
        sa.Column('to_status', sa.String(length=16), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_lead_events_company_id'), 'lead_events', ['company_id'], unique=False)
    op.create_index('ix_lead_events_company_created', 'lead_events', ['company_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_lead_events_company_created', table_name='lead_events')
    op.drop_index(op.f('ix_lead_events_company_id'), table_name='lead_events')
    op.drop_table('lead_events')
    op.drop_index('ix_lead_states_assignee_status', table_name='lead_states')
    op.drop_index('ix_lead_states_status_activity', table_name='lead_states')
    op.drop_index(op.f('ix_lead_states_company_id'), table_name='lead_states')
    op.drop_table('lead_states')
