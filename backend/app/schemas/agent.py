import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    last_seen_at: datetime | None
    status: str | None
    available_ifaces: list[str] | None
    agent_metadata: dict[str, Any] | None


class AgentCreateResponse(AgentRead):
    agent_token: str


class AgentIfacesResponse(BaseModel):
    agent_id: uuid.UUID
    ifaces: list[str]


class AgentHeartbeatRequest(BaseModel):
    available_ifaces: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class AgentHeartbeatResponse(BaseModel):
    agent_id: uuid.UUID
    status: str
    last_seen_at: datetime


class AgentCommand(BaseModel):
    type: Literal["capture", "live_session"] = "capture"
    capture_id: uuid.UUID | None = None
    live_session_id: uuid.UUID | None = None
    iface: str
    bpf_filter: str | None = None
    duration_seconds: int
    chunk_seconds: int | None = None
    model_id: uuid.UUID | None = None


class AgentCommandsResponse(BaseModel):
    commands: list[AgentCommand]


class AgentCaptureFailRequest(BaseModel):
    error_message: str = Field(min_length=1, max_length=2000)


class AgentCaptureStatusResponse(BaseModel):
    capture_id: uuid.UUID
    status: str


class AgentLiveSessionStatusResponse(BaseModel):
    live_session_id: uuid.UUID
    status: str
