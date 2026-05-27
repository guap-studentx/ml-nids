from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture_session import CaptureSession


class CaptureSessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(
        self,
        *,
        mode: str | None = None,
        status: str | None = None,
        model_id: uuid.UUID | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CaptureSession], int]:
        stmt = self._apply_filters(
            select(CaptureSession),
            mode=mode,
            status=status,
            model_id=model_id,
            started_from=started_from,
            started_to=started_to,
        )
        count_stmt = self._apply_filters(
            select(func.count(CaptureSession.id)),
            mode=mode,
            status=status,
            model_id=model_id,
            started_from=started_from,
            started_to=started_to,
        )
        total_result = await self.session.execute(count_stmt)
        result = await self.session.execute(
            stmt.order_by(CaptureSession.started_at.desc().nullslast(), CaptureSession.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total_result.scalar_one())

    async def get(self, capture_id: uuid.UUID) -> CaptureSession | None:
        result = await self.session.execute(select(CaptureSession).where(CaptureSession.id == capture_id))
        return result.scalar_one_or_none()

    async def list_by_live_session(self, live_session_id: uuid.UUID) -> list[CaptureSession]:
        result = await self.session.execute(
            select(CaptureSession)
            .where(CaptureSession.live_session_id == live_session_id)
            .order_by(CaptureSession.chunk_index.asc().nullslast(), CaptureSession.id.asc())
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count(CaptureSession.id)))
        return int(result.scalar_one())

    async def recent(self, *, limit: int = 10) -> list[CaptureSession]:
        result = await self.session.execute(
            select(CaptureSession)
            .order_by(CaptureSession.started_at.desc().nullslast(), CaptureSession.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def anomaly_count_since(self, *, since: datetime) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(CaptureSession.flows_anomaly), 0)).where(
                CaptureSession.started_at >= since
            )
        )
        return int(result.scalar_one())

    async def timeseries_anomalies(self, *, hours: int) -> list[tuple[datetime, int]]:
        start = datetime.now(UTC) - timedelta(hours=hours)
        bucket = func.date_trunc("hour", CaptureSession.started_at).label("bucket")
        result = await self.session.execute(
            select(bucket, func.coalesce(func.sum(CaptureSession.flows_anomaly), 0))
            .where(CaptureSession.started_at >= start)
            .group_by(bucket)
            .order_by(bucket)
        )
        return [(row[0], int(row[1])) for row in result.all()]

    async def create(
        self,
        *,
        mode: str,
        model_id: uuid.UUID,
        created_by: uuid.UUID,
        name: str | None = None,
        status: str = "pending",
    ) -> CaptureSession:
        capture = CaptureSession(mode=mode, model_id=model_id, created_by=created_by, name=name, status=status)
        self.session.add(capture)
        await self.session.flush()
        return capture

    async def create_live_chunk(
        self,
        *,
        live_session_id: uuid.UUID,
        chunk_index: int,
        model_id: uuid.UUID,
        agent_id: uuid.UUID,
        iface: str,
        created_by: uuid.UUID | None,
        name: str | None = None,
        bpf_filter: str | None = None,
        source_filename: str | None = None,
        nfstream_settings: dict | None = None,
    ) -> CaptureSession:
        capture = CaptureSession(
            mode="live_chunk",
            model_id=model_id,
            agent_id=agent_id,
            iface=iface,
            bpf_filter=bpf_filter,
            source_filename=source_filename,
            created_by=created_by,
            name=name,
            status="pending",
            live_session_id=live_session_id,
            chunk_index=chunk_index,
            nfstream_settings=nfstream_settings,
        )
        self.session.add(capture)
        await self.session.flush()
        return capture

    async def next_chunk_index(self, live_session_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(CaptureSession.chunk_index), 0)).where(
                CaptureSession.live_session_id == live_session_id
            )
        )
        return int(result.scalar_one()) + 1

    async def aggregate_live_session(self, live_session_id: uuid.UUID) -> tuple[int, int]:
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(CaptureSession.flows_total), 0),
                func.coalesce(func.sum(CaptureSession.flows_anomaly), 0),
            ).where(
                CaptureSession.live_session_id == live_session_id,
                CaptureSession.status == "completed",
            )
        )
        row = result.one()
        return int(row[0]), int(row[1])

    async def pending_live_for_agent(self, agent_id: uuid.UUID) -> CaptureSession | None:
        result = await self.session.execute(
            select(CaptureSession)
            .where(
                CaptureSession.mode == "live",
                CaptureSession.agent_id == agent_id,
                CaptureSession.status == "pending",
            )
            .order_by(CaptureSession.id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def delete(self, capture: CaptureSession) -> None:
        await self.session.delete(capture)
        await self.session.flush()

    async def mark_running(self, capture: CaptureSession, *, source_filename: str | None = None) -> CaptureSession:
        capture.status = "running"
        capture.source_filename = source_filename or capture.source_filename
        capture.started_at = datetime.now(UTC)
        capture.error_message = None
        await self.session.flush()
        return capture

    async def mark_completed(
        self,
        capture: CaptureSession,
        *,
        flows_total: int,
        flows_anomaly: int,
    ) -> CaptureSession:
        capture.status = "completed"
        capture.flows_total = flows_total
        capture.flows_anomaly = flows_anomaly
        capture.finished_at = datetime.now(UTC)
        await self.session.flush()
        return capture

    async def mark_failed(self, capture: CaptureSession, *, error_message: str) -> CaptureSession:
        capture.status = "failed"
        capture.error_message = error_message
        capture.finished_at = datetime.now(UTC)
        await self.session.flush()
        return capture

    async def mark_stopping(self, capture: CaptureSession) -> CaptureSession:
        capture.status = "stopping"
        await self.session.flush()
        return capture

    async def mark_stopped(self, capture: CaptureSession, *, error_message: str | None = None) -> CaptureSession:
        capture.status = "stopped"
        capture.error_message = error_message
        capture.finished_at = datetime.now(UTC)
        await self.session.flush()
        return capture

    def _apply_filters(
        self,
        stmt: Select,
        *,
        mode: str | None,
        status: str | None,
        model_id: uuid.UUID | None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
    ) -> Select:
        if mode is not None:
            stmt = stmt.where(CaptureSession.mode == mode)
        if status is not None:
            stmt = stmt.where(CaptureSession.status == status)
        if model_id is not None:
            stmt = stmt.where(CaptureSession.model_id == model_id)
        if started_from is not None:
            stmt = stmt.where(CaptureSession.started_at >= started_from)
        if started_to is not None:
            stmt = stmt.where(CaptureSession.started_at <= started_to)
        return stmt
