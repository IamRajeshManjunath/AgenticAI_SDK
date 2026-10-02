"""Add workflow_revisions table for immutable configuration revisions

Revision ID: 001
Revises: 
Create Date: 2026-10-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create workflow_revisions table for immutable configuration revisions
    op.create_table(
        'workflow_revisions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('revision', sa.BigInteger(), nullable=False),
        sa.Column('document', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('workflow_id', 'revision', name='uq_workflow_revision'),
        sa.UniqueConstraint('workflow_id', 'content_hash', name='uq_workflow_content_hash'),
        sa.CheckConstraint(
            "status IN ('draft', 'validated', 'published', 'archived')",
            name='ck_workflow_revision_status'
        )
    )
    
    # Create indexes
    op.create_index(
        'ix_workflow_revisions_workflow',
        'workflow_revisions',
        ['workflow_id']
    )
    op.create_index(
        'ix_workflow_revisions_document',
        'workflow_revisions',
        ['document'],
        postgresql_using='gin'
    )
    
    # Add revision column to runs table for immutable reference
    op.add_column('runs', sa.Column('workflow_revision_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_runs_workflow_revision',
        'runs', 'workflow_revisions',
        ['workflow_revision_id'], ['id']
    )
    op.create_index('ix_runs_workflow_revision', 'runs', ['workflow_revision_id'])


def downgrade() -> None:
    op.drop_index('ix_runs_workflow_revision', table_name='runs')
    op.drop_constraint('fk_runs_workflow_revision', 'runs', type_='foreignkey')
    op.drop_column('runs', 'workflow_revision_id')
    
    op.drop_index('ix_workflow_revisions_document', table_name='workflow_revisions')
    op.drop_index('ix_workflow_revisions_workflow', table_name='workflow_revisions')
    op.drop_table('workflow_revisions')