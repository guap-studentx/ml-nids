from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.live_session import LiveSession


class LiveSessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(
        self,
        *,
        status: str | None = None,
        agent_id: uuid.UUID | None = None,
        model_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LiveSession], int]:
        stmt = self._apply_filters(select(LiveSession), status=status, agent_id=agent_id, model_id=model_id)
        count_stmt = self._apply_filters(
            select(func.count(LiveSession.id)),
            status=status,
            agent_id=agent_id,
            model_id=model_id,
        )
        total_result = await self.session.execute(count_stmt)
        result = await self.session.execute(
            stmt.order_by(LiveSession.started_at.desc().nullslast(), LiveSession.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), int(total_result.scalar_one())

    async def get(self, live_session_id: uuid.UUID) -> LiveSession | None:
        result = await self.session.execute(select(LiveSession).where(LiveSession.id == live_session_id))
        return result.scalar_one_or_none()

    async def delete(self, live_session: LiveSession) -> None:
        await self.session.delete(live_session)
        await self.session.flush()

    async def pending_for_agent(self, agent_id: uuid.UUID) -> LiveSession | None:
        result = await self.session.execute(
            select(LiveSession)
            .where(
                LiveSession.agent_id == agent_id,
                LiveSession.status == "pending",
            )
            .order_by(LiveSession.id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str | None,
        agent_id: uuid.UUID,
        iface: str,
        model_id: uuid.UUID,
        created_by: uuid.UUID,
        chunk_seconds: int,
        duration_seconds: int,
        bpf_filter: str | None = None,
    ) -> LiveSession:
        live_session = LiveSession(
            name=name,
            agent_id=agent_id,
            iface=iface,
            bpf_filter=bpf_filter,
            model_id=model_id,
            created_by=created_by,
            chunk_seconds=chunk_seconds,
            duration_seconds=duration_seconds,
            status="pending",
        )
        self.session.add(live_session)
        await self.session.flush()
        return live_session

    async def mark_stopped(self, live_session: LiveSession) -> LiveSession:
        live_session.status = "stopped"
        live_session.finished_at = datetime.now(UTC)
        await self.session.flush()
        return live_session

    async def mark_running(self, live_session: LiveSession) -> LiveSession:
        live_session.status = "running"
        live_session.started_at = datetime.now(UTC)
        live_session.error_message = None
        await self.session.flush()
        return live_session

    async def mark_stopping(self, live_session: LiveSession) -> LiveSession:
        live_session.status = "stopping"
        await self.session.flush()
        return live_session

    async def mark_completed(self, live_session: LiveSession) -> LiveSession:
        live_session.status = "completed"
        live_session.finished_at = datetime.now(UTC)
        await self.session.flush()
        return live_session

    async def mark_failed(self, live_session: LiveSession, *, error_message: str) -> LiveSession:
        live_session.status = "failed"
        live_session.error_message = error_message
        live_session.finished_at = datetime.now(UTC)
        await self.session.flush()
        return live_session

    async def update_aggregates(
        self,
        live_session: LiveSession,
        *,
        flows_total: int,
        flows_anomaly: int,
    ) -> LiveSession:
        live_session.flows_total = flows_total
        live_session.flows_anomaly = flows_anomaly
        await self.session.flush()
        return live_session

    def _apply_filters(
        self,
        stmt: Select,
        *,
        status: str | None,
        agent_id: uuid.UUID | None,
        model_id: uuid.UUID | None,
    ) -> Select:
        if status is not None:
            stmt = stmt.where(LiveSession.status == status)
        if agent_id is not None:
            stmt = stmt.where(LiveSession.agent_id == agent_id)
        if model_id is not None:
            stmt = stmt.where(LiveSession.model_id == model_id)
        return stmt
