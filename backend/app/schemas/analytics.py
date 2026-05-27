import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.capture import CaptureRead
from app.schemas.flow import FlowRead


class ScoreBucket(BaseModel):
    min_score: float
    max_score: float
    count: int


class TimelinePoint(BaseModel):
    timestamp: datetime | None
    anomalies: int
    total: int


class EndpointCount(BaseModel):
    value: str
    count: int


class CaptureSummary(BaseModel):
    total_flows: int
    anomaly_flows: int
    anomaly_rate: float


class CaptureAnalytics(BaseModel):
    capture: CaptureRead
    summary: CaptureSummary
    score_distribution: list[ScoreBucket]
    anomalies_timeline: list[TimelinePoint]
    top_sources: list[EndpointCount]
    top_destinations: list[EndpointCount]
    recent_flows: list[FlowRead]


class DashboardSummary(BaseModel):
    total_sessions: int
    anomalies_24h: int
    active_agents: int
    active_models: int
    recent_captures: list[CaptureRead]


class DashboardTimeseriesPoint(BaseModel):
    timestamp: datetime
    anomalies: int


class DashboardTimeseries(BaseModel):
    period_hours: int
    points: list[DashboardTimeseriesPoint]
