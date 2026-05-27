from __future__ import annotations

import uuid
from pathlib import Path

from app.exceptions import CaptureNotFoundError
from app.models.capture_session import CaptureSession
from app.models.flow import Flow
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.repositories.flow_repository import FlowRepository
from app.schemas.analytics import (
    CaptureAnalytics,
    CaptureSummary,
    EndpointCount,
    ScoreBucket,
    TimelinePoint,
)


class CaptureAnalyticsService:
    def __init__(self, captures: CaptureSessionRepository, flows: FlowRepository, captures_dir: Path):
        self.captures = captures
        self.flows = flows
        self.captures_dir = captures_dir

    async def build(self, capture_id: uuid.UUID) -> CaptureAnalytics:
        capture = await self.captures.get(capture_id)
        if capture is None:
            raise CaptureNotFoundError()

        df = self._read_capture_dataframe(capture_id)
        if df is None:
            stored_flows, _ = await self.flows.list(session_id=capture_id, limit=1000)
            df = self._flows_to_dataframe(stored_flows)

        return CaptureAnalytics(
            capture=capture,
            summary=self._summary(capture, df),
            score_distribution=self._score_distribution(df),
            anomalies_timeline=self._timeline(df),
            top_sources=self._top_endpoints(df, "src_ip"),
            top_destinations=self._top_endpoints(df, "dst_ip"),
            recent_flows=await self.flows.top(session_id=capture_id, n=50),
        )

    def _read_capture_dataframe(self, capture_id: uuid.UUID) -> pd.DataFrame | None:
        pd = self._pd()
        parquet_path = self.captures_dir / str(capture_id) / "flows.parquet"
        if not parquet_path.exists():
            return None
        return pd.read_parquet(parquet_path)

    def _flows_to_dataframe(self, flows: list[Flow]) -> pd.DataFrame:
        pd = self._pd()
        return pd.DataFrame([flow.flow_features for flow in flows])

    def _summary(self, capture: CaptureSession, df: pd.DataFrame) -> CaptureSummary:
        pd = self._pd()
        total = int(capture.flows_total or len(df))
        anomalies = int(capture.flows_anomaly or int(df.get("prediction", pd.Series(dtype=int)).sum()))
        rate = round((anomalies / total) * 100, 4) if total else 0.0
        return CaptureSummary(total_flows=total, anomaly_flows=anomalies, anomaly_rate=rate)

    def _score_distribution(self, df: pd.DataFrame, buckets: int = 10) -> list[ScoreBucket]:
        pd = self._pd()
        if df.empty or "anomaly_score" not in df:
            return []
        scores = pd.to_numeric(df["anomaly_score"], errors="coerce").dropna()
        if scores.empty:
            return []

        min_score = float(scores.min())
        max_score = float(scores.max())
        if min_score == max_score:
            return [ScoreBucket(min_score=min_score, max_score=max_score, count=int(len(scores)))]

        counts = pd.cut(scores, bins=buckets, include_lowest=True).value_counts().sort_index()
        return [
            ScoreBucket(min_score=float(interval.left), max_score=float(interval.right), count=int(count))
            for interval, count in counts.items()
        ]

    def _timeline(self, df: pd.DataFrame) -> list[TimelinePoint]:
        pd = self._pd()
        if df.empty or "prediction" not in df:
            return []

        timestamp_column = self._timestamp_column(df)
        working = df.copy()
        if timestamp_column is None:
            return [
                TimelinePoint(
                    timestamp=None,
                    anomalies=int((working["prediction"] == 1).sum()),
                    total=int(len(working)),
                )
            ]

        working["_ts"] = pd.to_datetime(working[timestamp_column], errors="coerce", utc=True)
        working = working.dropna(subset=["_ts"])
        if working.empty:
            return []

        grouped = working.groupby(pd.Grouper(key="_ts", freq="1min"))
        return [
            TimelinePoint(
                timestamp=index.to_pydatetime(),
                anomalies=int((group["prediction"] == 1).sum()),
                total=int(len(group)),
            )
            for index, group in grouped
            if len(group) > 0
        ]

    def _timestamp_column(self, df: pd.DataFrame) -> str | None:
        for column in ("flow_timestamp", "bidirectional_first_seen_ms", "expiration_id"):
            if column in df:
                return column
        return None

    def _top_endpoints(self, df: pd.DataFrame, column: str, n: int = 10) -> list[EndpointCount]:
        if df.empty or column not in df:
            return []
        working = df
        if "prediction" in working:
            working = working[working["prediction"] == 1]
        counts = working[column].dropna().astype(str).value_counts().head(n)
        return [EndpointCount(value=value, count=int(count)) for value, count in counts.items()]

    def _pd(self):
        import pandas as pd

        return pd
