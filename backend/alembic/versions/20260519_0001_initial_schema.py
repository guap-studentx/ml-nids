"""initial schema

Revision ID: 20260519_0001
Revises:
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260519_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "agents",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=True),
        sa.Column("available_ifaces", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ml_models",
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("model_class_name", sa.String(length=64), nullable=False),
        sa.Column("score_type", sa.String(length=32), nullable=False),
        sa.Column("decision_threshold", sa.Float(), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metrics_test", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("artifact_path", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ml_models_model_id"), "ml_models", ["model_id"], unique=True)

    op.create_table(
        "capture_sessions",
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("source_filename", sa.String(length=512), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("iface", sa.String(length=64), nullable=True),
        sa.Column("bpf_filter", sa.String(length=255), nullable=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("flows_total", sa.Integer(), nullable=False),
        sa.Column("flows_anomaly", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("nfstream_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["ml_models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "flows",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("src_ip", postgresql.INET(), nullable=True),
        sa.Column("dst_ip", postgresql.INET(), nullable=True),
        sa.Column("src_port", sa.Integer(), nullable=True),
        sa.Column("dst_port", sa.Integer(), nullable=True),
        sa.Column("protocol", sa.SmallInteger(), nullable=True),
        sa.Column("bidirectional_duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("bidirectional_packets", sa.Integer(), nullable=True),
        sa.Column("bidirectional_bytes", sa.BigInteger(), nullable=True),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("prediction", sa.SmallInteger(), nullable=False),
        sa.Column("flow_features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("flow_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["capture_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_flows_session", "flows", ["session_id"], unique=False)
    op.create_index("idx_flows_session_pred", "flows", ["session_id", "prediction"], unique=False)
    op.create_index("idx_flows_session_score", "flows", ["session_id", "anomaly_score"], unique=False)

    op.create_table(
        "reports",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["capture_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_index("idx_flows_session_score", table_name="flows")
    op.drop_index("idx_flows_session_pred", table_name="flows")
    op.drop_index("idx_flows_session", table_name="flows")
    op.drop_table("flows")
    op.drop_table("capture_sessions")
    op.drop_index(op.f("ix_ml_models_model_id"), table_name="ml_models")
    op.drop_table("ml_models")
    op.drop_table("agents")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
