import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LiveSessionStatus = Literal["pending", "running", "stopping", "completed", "failed", "stopped"]


class LiveSessionCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    agent_id: uuid.UUID
    iface: str = Field(min_length=1, max_length=64)
    model_id: uuid.UUID
    bpf_filter: str | None = Field(default=None, max_length=255)
    chunk_seconds: int = Field(default=15, ge=5, le=300)
    duration_seconds: int = Field(default=3600, ge=30, le=21600)


class LiveSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    agent_id: uuid.UUID
    iface: str
    bpf_filter: str | None
    model_id: uuid.UUID
    status: str
    chunk_seconds: int
    duration_seconds: int
    flows_total: int
    flows_anomaly: int
    started_at: datetime | None
    finished_at: datetime | None
    created_by: uuid.UUID | None
    error_message: str | None


class LiveSessionListResponse(BaseModel):
    items: list[LiveSessionRead]
    total: int
    limit: int
    offset: int
