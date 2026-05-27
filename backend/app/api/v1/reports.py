import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user, get_report_service
from app.models.user import User
from app.schemas.report import ReportCreate, ReportListResponse, ReportRead
from app.services.report_service import ReportService

router = APIRouter(tags=["reports"])


@router.post("/captures/{capture_id}/report", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def create_capture_report(
    capture_id: uuid.UUID,
    payload: ReportCreate,
    report_service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportRead:
    report = await report_service.create(capture_id=capture_id, format=payload.format)
    await session.commit()
    return ReportRead.model_validate(report)


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    report_service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReportListResponse:
    reports, total = await report_service.list(limit=limit, offset=offset)
    return ReportListResponse(items=reports, total=total, limit=limit, offset=offset)


@router.get("/reports/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: uuid.UUID,
    report_service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> ReportRead:
    return ReportRead.model_validate(await report_service.get(report_id))


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    report_service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    report = await report_service.get(report_id)
    path = report_service.download_path(report)
    media_type = "application/pdf" if report.format == "pdf" else "text/html"
    return FileResponse(path, media_type=media_type, filename=path.name)
