from datetime import UTC, datetime, timedelta

from app.config import get_settings
from app.repositories.agent_repository import AgentRepository
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.repositories.model_repository import ModelRepository
from app.schemas.analytics import DashboardSummary, DashboardTimeseries, DashboardTimeseriesPoint


class DashboardService:
    def __init__(
        self,
        captures: CaptureSessionRepository,
        models: ModelRepository,
        agents: AgentRepository,
    ):
        self.captures = captures
        self.models = models
        self.agents = agents

    async def summary(self) -> DashboardSummary:
        return DashboardSummary(
            total_sessions=await self.captures.count_all(),
            anomalies_24h=await self.captures.anomaly_count_since(since=datetime.now(UTC) - timedelta(hours=24)),
            active_agents=await self.agents.count_online(
                seen_after=datetime.now(UTC) - timedelta(seconds=get_settings().agent_offline_after_seconds)
            ),
            active_models=await self.models.count_active(),
            recent_captures=await self.captures.recent(limit=10),
        )

    async def timeseries(self, period: str) -> DashboardTimeseries:
        hours = self._parse_period(period)
        points = [
            DashboardTimeseriesPoint(timestamp=timestamp, anomalies=anomalies)
            for timestamp, anomalies in await self.captures.timeseries_anomalies(hours=hours)
        ]
        return DashboardTimeseries(period_hours=hours, points=points)

    def _parse_period(self, period: str) -> int:
        if period.endswith("h"):
            return max(1, min(24 * 14, int(period[:-1])))
        return 24
