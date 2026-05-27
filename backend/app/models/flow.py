import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, SmallInteger
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import UUIDPrimaryKeyMixin


class Flow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "flows"
    __table_args__ = (
        Index("idx_flows_session", "session_id"),
        Index("idx_flows_session_score", "session_id", "anomaly_score"),
        Index("idx_flows_session_pred", "session_id", "prediction"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("capture_sessions.id", ondelete="CASCADE"), nullable=False
    )
    src_ip: Mapped[str | None] = mapped_column(INET)
    dst_ip: Mapped[str | None] = mapped_column(INET)
    src_port: Mapped[int | None] = mapped_column(Integer)
    dst_port: Mapped[int | None] = mapped_column(Integer)
    protocol: Mapped[int | None] = mapped_column(SmallInteger)
    bidirectional_duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    bidirectional_packets: Mapped[int | None] = mapped_column(Integer)
    bidirectional_bytes: Mapped[int | None] = mapped_column(BigInteger)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    prediction: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    flow_features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    flow_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session = relationship("CaptureSession", back_populates="flows")
