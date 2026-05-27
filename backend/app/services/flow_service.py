from __future__ import annotations

import uuid
from pathlib import Path

from app.exceptions import CaptureNotFoundError, ExportNotFoundError, FlowNotFoundError
from app.models.flow import Flow
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.repositories.flow_repository import FlowRepository


class FlowService:
    def __init__(self, captures: CaptureSessionRepository, flows: FlowRepository, captures_dir: Path):
        self.captures = captures
        self.flows = flows
        self.captures_dir = captures_dir

    async def list(
        self,
        *,
        session_id: uuid.UUID,
        prediction: int | None = None,
        min_score: float | None = None,
        src_ip: str | None = None,
        dst_ip: str | None = None,
        protocol: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Flow], int]:
        await self._ensure_capture_exists(session_id)
        return await self.flows.list(
            session_id=session_id,
            prediction=prediction,
            min_score=min_score,
            src_ip=src_ip,
            dst_ip=dst_ip,
            protocol=protocol,
            limit=limit,
            offset=offset,
        )

    async def top(self, *, session_id: uuid.UUID, n: int = 50) -> list[Flow]:
        await self._ensure_capture_exists(session_id)
        return await self.flows.top(session_id=session_id, n=n)

    async def get(self, *, session_id: uuid.UUID, flow_id: uuid.UUID) -> Flow:
        await self._ensure_capture_exists(session_id)
        flow = await self.flows.get(session_id=session_id, flow_id=flow_id)
        if flow is None:
            raise FlowNotFoundError()
        return flow

    def explain(self, flow: Flow, limit: int = 5) -> list[dict]:
        items = []
        for feature, value in flow.flow_features.items():
            numeric_value = self._numeric(value)
            if numeric_value is None:
                continue
            items.append({"feature": feature, "value": numeric_value, "contribution": abs(numeric_value)})
        return sorted(items, key=lambda item: item["contribution"], reverse=True)[:limit]

    async def export_path(self, *, session_id: uuid.UUID, export_format: str) -> Path:
        await self._ensure_capture_exists(session_id)
        parquet_path = self.captures_dir / str(session_id) / "flows.parquet"
        if not parquet_path.exists():
            raise ExportNotFoundError()

        if export_format == "parquet":
            return parquet_path
        if export_format == "csv":
            import pandas as pd

            csv_path = parquet_path.with_suffix(".csv")
            if not csv_path.exists() or csv_path.stat().st_mtime < parquet_path.stat().st_mtime:
                df = pd.read_parquet(parquet_path)
                df.to_csv(csv_path, index=False)
            return csv_path
        raise ValueError("Unsupported export format")

    async def _ensure_capture_exists(self, session_id: uuid.UUID) -> None:
        capture = await self.captures.get(session_id)
        if capture is None:
            raise CaptureNotFoundError()

    def _numeric(self, value) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
