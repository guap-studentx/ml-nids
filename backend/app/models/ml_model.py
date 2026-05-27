import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.common import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.capture_session import CaptureSession
    from app.models.live_session import LiveSession
    from app.models.user import User


class MLModel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ml_models"

    model_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_class_name: Mapped[str] = mapped_column(String(64), nullable=False)
    score_type: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    features: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    metrics_test: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    uploader: Mapped["User | None"] = relationship(back_populates="uploaded_models")
    captures: Mapped[list["CaptureSession"]] = relationship(back_populates="model")
    live_sessions: Mapped[list["LiveSession"]] = relationship(back_populates="model")
