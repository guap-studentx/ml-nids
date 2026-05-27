import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.flow import Flow
    from app.models.live_session import LiveSession
    from app.models.ml_model import MLModel
    from app.models.report import Report
    from app.models.user import User


class CaptureSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "capture_sessions"

    name: Mapped[str | None] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(512))
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"))
    iface: Mapped[str | None] = mapped_column(String(64))
    bpf_filter: Mapped[str | None] = mapped_column(String(255))
    model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ml_models.id"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    flows_total: Mapped[int] = mapped_column(Integer, default=0)
    flows_anomaly: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    error_message: Mapped[str | None] = mapped_column(Text)
    nfstream_settings: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    live_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
    )
    chunk_index: Mapped[int | None] = mapped_column(Integer)

    agent: Mapped["Agent | None"] = relationship(back_populates="captures")
    model: Mapped["MLModel | None"] = relationship(back_populates="captures")
    creator: Mapped["User | None"] = relationship(back_populates="captures")
    flows: Mapped[list["Flow"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    live_session: Mapped["LiveSession | None"] = relationship(back_populates="chunks")
