import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class FlowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    src_ip: str | None
    dst_ip: str | None
    src_port: int | None
    dst_port: int | None
    protocol: int | None
    bidirectional_duration_ms: int | None
    bidirectional_packets: int | None
    bidirectional_bytes: int | None
    anomaly_score: float
    prediction: int
    flow_features: dict[str, Any]
    flow_timestamp: datetime | None

    @field_validator("src_ip", "dst_ip", mode="before")
    @classmethod
    def serialize_inet(cls, value):
        if value is None:
            return None
        return str(value)


class FlowListResponse(BaseModel):
    items: list[FlowRead]
    total: int
    limit: int
    offset: int


class FlowExplanationItem(BaseModel):
    feature: str
    value: float
    contribution: float


class FlowDetailResponse(BaseModel):
    flow: FlowRead
    explanation: list[FlowExplanationItem]
