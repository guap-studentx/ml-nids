from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.common import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.capture_session import CaptureSession
    from app.models.live_session import LiveSession
    from app.models.ml_model import MLModel


class User(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    captures: Mapped[list["CaptureSession"]] = relationship(back_populates="creator")
    live_sessions: Mapped[list["LiveSession"]] = relationship(back_populates="creator")
    uploaded_models: Mapped[list["MLModel"]] = relationship(back_populates="uploader")
