import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


CaptureMode = Literal["offline_pcap", "offline_csv", "live"]
CaptureStatus = Literal["pending", "running", "stopping", "completed", "failed", "stopped"]


class CaptureCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    mode: CaptureMode = "offline_csv"
    model_id: uuid.UUID


class LiveCaptureCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    model_id: uuid.UUID
    agent_id: uuid.UUID
    iface: str = Field(min_length=1, max_length=64)
    bpf_filter: str | None = Field(default=None, max_length=255)
    duration_seconds: int = Field(default=30, ge=1, le=3600)


class CaptureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    mode: str
    source_filename: str | None
    agent_id: uuid.UUID | None
    iface: str | None
    bpf_filter: str | None
    model_id: uuid.UUID | None
    status: str
    flows_total: int
    flows_anomaly: int
    started_at: datetime | None
    finished_at: datetime | None
    created_by: uuid.UUID | None
    error_message: str | None
    nfstream_settings: dict[str, Any] | None
    live_session_id: uuid.UUID | None
    chunk_index: int | None


class CaptureListResponse(BaseModel):
    items: list[CaptureRead]
    total: int
    limit: int
    offset: int


class CaptureStartResponse(BaseModel):
    session_id: uuid.UUID
    status: str
