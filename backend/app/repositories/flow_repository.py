from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flow import Flow


class FlowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_many(self, flows: list[Flow]) -> None:
        self.session.add_all(flows)
        await self.session.flush()

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
        stmt = self._apply_filters(
            select(Flow),
            session_id=session_id,
            prediction=prediction,
            min_score=min_score,
            src_ip=src_ip,
            dst_ip=dst_ip,
            protocol=protocol,
        )
        count_stmt = self._apply_filters(
            select(func.count(Flow.id)),
            session_id=session_id,
            prediction=prediction,
            min_score=min_score,
            src_ip=src_ip,
            dst_ip=dst_ip,
            protocol=protocol,
        )
        total_result = await self.session.execute(count_stmt)
        result = await self.session.execute(
            stmt.order_by(Flow.anomaly_score.desc(), Flow.id.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), int(total_result.scalar_one())

    async def top(self, *, session_id: uuid.UUID, n: int = 50) -> list[Flow]:
        result = await self.session.execute(
            select(Flow).where(Flow.session_id == session_id).order_by(Flow.anomaly_score.desc()).limit(n)
        )
        return list(result.scalars().all())

    async def get(self, *, session_id: uuid.UUID, flow_id: uuid.UUID) -> Flow | None:
        result = await self.session.execute(select(Flow).where(Flow.session_id == session_id, Flow.id == flow_id))
        return result.scalar_one_or_none()

    def _apply_filters(
        self,
        stmt: Select,
        *,
        session_id: uuid.UUID,
        prediction: int | None,
        min_score: float | None,
        src_ip: str | None,
        dst_ip: str | None,
        protocol: int | None,
    ) -> Select:
        stmt = stmt.where(Flow.session_id == session_id)
        if prediction is not None:
            stmt = stmt.where(Flow.prediction == prediction)
        if min_score is not None:
            stmt = stmt.where(Flow.anomaly_score >= min_score)
        if src_ip is not None:
            stmt = stmt.where(Flow.src_ip == src_ip)
        if dst_ip is not None:
            stmt = stmt.where(Flow.dst_ip == dst_ip)
        if protocol is not None:
            stmt = stmt.where(Flow.protocol == protocol)
        return stmt
