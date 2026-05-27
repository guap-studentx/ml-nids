import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


ReportFormat = Literal["pdf", "html"]


class ReportCreate(BaseModel):
    format: ReportFormat = "pdf"


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    file_path: str
    format: str
    created_at: datetime
    status: str = "completed"


class ReportListResponse(BaseModel):
    items: list[ReportRead]
    total: int
    limit: int
    offset: int
