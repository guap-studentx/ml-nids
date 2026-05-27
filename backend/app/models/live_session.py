import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.capture_session import CaptureSession
    from app.models.ml_model import MLModel
    from app.models.user import User


class LiveSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "live_sessions"

    name: Mapped[str | None] = mapped_column(String(255))
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    iface: Mapped[str] = mapped_column(String(64), nullable=False)
    bpf_filter: Mapped[str | None] = mapped_column(String(255))
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ml_models.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    chunk_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    flows_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flows_anomaly: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    error_message: Mapped[str | None] = mapped_column(Text)

    agent: Mapped["Agent"] = relationship(back_populates="live_sessions")
    model: Mapped["MLModel"] = relationship(back_populates="live_sessions")
    creator: Mapped["User | None"] = relationship(back_populates="live_sessions")
    chunks: Mapped[list["CaptureSession"]] = relationship(
        back_populates="live_session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
