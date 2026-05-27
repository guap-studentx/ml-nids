from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


class ReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, *, limit: int = 50, offset: int = 0) -> tuple[list[Report], int]:
        from sqlalchemy import func

        total_result = await self.session.execute(select(func.count(Report.id)))
        result = await self.session.execute(
            select(Report).order_by(Report.created_at.desc(), Report.id.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), int(total_result.scalar_one())

    async def get(self, report_id: uuid.UUID) -> Report | None:
        result = await self.session.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()

    async def create(self, *, session_id: uuid.UUID, file_path: str, format: str) -> Report:
        report = Report(session_id=session_id, file_path=file_path, format=format)
        self.session.add(report)
        await self.session.flush()
        return report
