"""cascade delete live session chunks

Revision ID: 20260525_0003
Revises: 20260525_0002
Create Date: 2026-05-25
"""

from alembic import op

revision = "20260525_0003"
down_revision = "20260525_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("fk_capture_sessions_live_session_id_live_sessions", "capture_sessions", type_="foreignkey")
    op.create_foreign_key(
        "fk_capture_sessions_live_session_id_live_sessions",
        "capture_sessions",
        "live_sessions",
        ["live_session_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_capture_sessions_live_session_id_live_sessions", "capture_sessions", type_="foreignkey")
    op.create_foreign_key(
        "fk_capture_sessions_live_session_id_live_sessions",
        "capture_sessions",
        "live_sessions",
        ["live_session_id"],
        ["id"],
    )
