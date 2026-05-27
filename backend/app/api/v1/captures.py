import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.database import async_session_factory
from app.dependencies import get_capture_analytics_service, get_capture_service, get_current_user
from app.models.user import User
from app.schemas.analytics import CaptureAnalytics
from app.schemas.capture import CaptureCreate, CaptureListResponse, CaptureRead, CaptureStartResponse, LiveCaptureCreate
from app.services.capture_service import CaptureService

router = APIRouter(prefix="/captures", tags=["captures"])


async def process_uploaded_csv(capture_id: uuid.UUID, csv_path: str) -> None:
    from app.services.offline_csv_service import OfflineCsvService

    settings = get_settings()
    async with async_session_factory() as session:
        service = OfflineCsvService(
            session=session,
            captures_dir=settings.captures_dir,
            models_dir=settings.models_dir,
        )
        await service.process(capture_id, Path(csv_path))


async def process_uploaded_pcap(capture_id: uuid.UUID, pcap_path: str) -> None:
    from app.services.offline_pcap_service import OfflinePcapService

    settings = get_settings()
    async with async_session_factory() as session:
        service = OfflinePcapService(
            session=session,
            captures_dir=settings.captures_dir,
            models_dir=settings.models_dir,
        )
        await service.process(capture_id, Path(pcap_path))


async def save_upload(file: UploadFile, upload_path: Path) -> None:
    with upload_path.open("wb") as target:
        while chunk := await file.read(1024 * 1024):
            target.write(chunk)


@router.get("", response_model=CaptureListResponse)
async def list_captures(
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    _: Annotated[User, Depends(get_current_user)],
    mode: str | None = None,
    capture_status: Annotated[str | None, Query(alias="status")] = None,
    model_id: uuid.UUID | None = None,
    started_from: datetime | None = None,
    started_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CaptureListResponse:
    captures, total = await capture_service.list(
        mode=mode,
        status=capture_status,
        model_id=model_id,
        started_from=started_from,
        started_to=started_to,
        limit=limit,
        offset=offset,
    )
    return CaptureListResponse(items=captures, total=total, limit=limit, offset=offset)


@router.post("", response_model=CaptureRead, status_code=status.HTTP_201_CREATED)
async def create_capture_placeholder(
    payload: CaptureCreate,
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    capture = await capture_service.create_placeholder(
        mode=payload.mode,
        model_id=payload.model_id,
        created_by=current_user.id,
        name=payload.name,
    )
    await session.commit()
    await session.refresh(capture)
    return capture


@router.post("/upload-csv", response_model=CaptureStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_csv(
    background_tasks: BackgroundTasks,
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File()],
    model_id: Annotated[uuid.UUID, Form()],
    name: Annotated[str | None, Form()] = None,
) -> CaptureStartResponse:
    settings = get_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "flows.csv").name

    capture = await capture_service.create_offline_csv(
        model_id=model_id,
        created_by=current_user.id,
        name=name,
        source_filename=safe_filename,
    )
    await session.commit()
    await session.refresh(capture)

    upload_path = settings.uploads_dir / f"{capture.id}_{safe_filename}"
    await save_upload(file, upload_path)

    background_tasks.add_task(process_uploaded_csv, capture.id, str(upload_path))
    return CaptureStartResponse(session_id=capture.id, status=capture.status)


@router.post("/upload-pcap", response_model=CaptureStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_pcap(
    background_tasks: BackgroundTasks,
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File()],
    model_id: Annotated[uuid.UUID, Form()],
    name: Annotated[str | None, Form()] = None,
) -> CaptureStartResponse:
    from app.services.nfstream_settings import NFSTREAM_OFFLINE_SETTINGS

    settings = get_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "traffic.pcap").name

    capture = await capture_service.create_offline_pcap(
        model_id=model_id,
        created_by=current_user.id,
        name=name,
        source_filename=safe_filename,
        nfstream_settings=NFSTREAM_OFFLINE_SETTINGS,
    )
    await session.commit()
    await session.refresh(capture)

    upload_path = settings.uploads_dir / f"{capture.id}_{safe_filename}"
    await save_upload(file, upload_path)

    background_tasks.add_task(process_uploaded_pcap, capture.id, str(upload_path))
    return CaptureStartResponse(session_id=capture.id, status=capture.status)


@router.post("/live", response_model=CaptureStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_live_capture(
    payload: LiveCaptureCreate,
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CaptureStartResponse:
    capture = await capture_service.create_live(
        model_id=payload.model_id,
        created_by=current_user.id,
        agent_id=payload.agent_id,
        iface=payload.iface,
        bpf_filter=payload.bpf_filter,
        duration_seconds=payload.duration_seconds,
        name=payload.name,
    )
    await session.commit()
    await session.refresh(capture)
    return CaptureStartResponse(session_id=capture.id, status=capture.status)


@router.get("/{capture_id}", response_model=CaptureRead)
async def get_capture(
    capture_id: uuid.UUID,
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await capture_service.get(capture_id)


@router.post("/{capture_id}/stop", response_model=CaptureRead)
async def stop_capture(
    capture_id: uuid.UUID,
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CaptureRead:
    capture = await capture_service.stop(capture_id)
    await session.commit()
    return capture


@router.get("/{capture_id}/analytics", response_model=CaptureAnalytics)
async def get_capture_analytics(
    capture_id: uuid.UUID,
    analytics_service: Annotated[object, Depends(get_capture_analytics_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await analytics_service.build(capture_id)


@router.delete("/{capture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capture(
    capture_id: uuid.UUID,
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await capture_service.delete(capture_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
