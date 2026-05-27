"""add live sessions

Revision ID: 20260525_0002
Revises: 20260519_0001
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260525_0002"
down_revision = "20260519_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "live_sessions",
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("iface", sa.String(length=64), nullable=False),
        sa.Column("bpf_filter", sa.String(length=255), nullable=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("chunk_seconds", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("flows_total", sa.Integer(), nullable=False),
        sa.Column("flows_anomaly", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["ml_models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("capture_sessions", sa.Column("live_session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("capture_sessions", sa.Column("chunk_index", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_capture_sessions_live_session_id_live_sessions",
        "capture_sessions",
        "live_sessions",
        ["live_session_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_capture_sessions_live_session_id_live_sessions", "capture_sessions", type_="foreignkey")
    op.drop_column("capture_sessions", "chunk_index")
    op.drop_column("capture_sessions", "live_session_id")
    op.drop_table("live_sessions")
