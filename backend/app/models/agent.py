from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.capture_session import CaptureSession
    from app.models.live_session import LiveSession


class Agent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(String(16), default="offline")
    available_ifaces: Mapped[list[str] | None] = mapped_column(JSONB)
    agent_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    captures: Mapped[list["CaptureSession"]] = relationship(back_populates="agent")
    live_sessions: Mapped[list["LiveSession"]] = relationship(back_populates="agent")
