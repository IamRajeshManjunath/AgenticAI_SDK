"""Add workspace and workflow scope to agent schema audit records.

Revision ID: 002
Revises: 001
"""

from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "schema_audit_trails",
        sa.Column("workspace_id", sa.String(), nullable=True),
    )
    op.add_column(
        "schema_audit_trails",
        sa.Column("workflow_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_schema_audit_trails_workspace_id",
        "schema_audit_trails",
        ["workspace_id"],
    )
    op.create_index(
        "ix_schema_audit_trails_workflow_id",
        "schema_audit_trails",
        ["workflow_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_schema_audit_trails_workflow_id", table_name="schema_audit_trails")
    op.drop_index("ix_schema_audit_trails_workspace_id", table_name="schema_audit_trails")
    op.drop_column("schema_audit_trails", "workflow_id")
    op.drop_column("schema_audit_trails", "workspace_id")
