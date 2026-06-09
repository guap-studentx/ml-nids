import uuid
from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.dependencies import (
    get_agent_service,
    get_capture_service,
    get_capture_session_repository,
    get_live_session_service,
    require_admin,
)
from app.exceptions import AuthError
from app.models.user import User
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.schemas.agent import (
    AgentCaptureFailRequest,
    AgentCaptureStatusResponse,
    AgentCommand,
    AgentCommandsResponse,
    AgentCreate,
    AgentCreateResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentIfacesResponse,
    AgentLiveSessionStatusResponse,
    AgentRead,
)
from app.services.capture_service import CaptureService
from app.services.agent_service import AgentService
from app.services.live_session_service import LiveSessionService
from app.api.v1.captures import process_uploaded_csv, process_uploaded_pcap, save_upload

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentRead])
async def list_agents(
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    _: Annotated[User, Depends(require_admin)],
) -> list:
    return await agent_service.list()


@router.post("", response_model=AgentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AgentCreateResponse:
    agent, token = await agent_service.create(name=payload.name)
    await session.commit()
    data = AgentRead.model_validate(agent).model_dump()
    return AgentCreateResponse(**data, agent_token=token)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await agent_service.delete(agent_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{agent_id}/ifaces", response_model=AgentIfacesResponse)
async def get_agent_ifaces(
    agent_id: uuid.UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    _: Annotated[User, Depends(require_admin)],
) -> AgentIfacesResponse:
    return AgentIfacesResponse(agent_id=agent_id, ifaces=await agent_service.ifaces(agent_id))


@router.post("/{agent_id}/heartbeat", response_model=AgentHeartbeatResponse)
async def agent_heartbeat(
    agent_id: uuid.UUID,
    payload: AgentHeartbeatRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> AgentHeartbeatResponse:
    if not agent_token:
        raise AuthError()
    agent = await agent_service.heartbeat(
        agent_id,
        token=agent_token,
        available_ifaces=payload.available_ifaces,
        metadata=payload.metadata,
    )
    await session.commit()
    return AgentHeartbeatResponse(agent_id=agent.id, status=agent.status or "online", last_seen_at=agent.last_seen_at)


@router.get("/{agent_id}/commands", response_model=AgentCommandsResponse)
async def get_agent_commands(
    agent_id: uuid.UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> AgentCommandsResponse:
    if not agent_token:
        raise AuthError()
    await agent_service.authenticate(agent_id, token=agent_token)
    capture = await capture_service.claim_next_live_command(agent_id)
    live_session = None if capture is not None else await live_session_service.claim_next_command(agent_id)
    await session.commit()
    if capture is None and live_session is None:
        return AgentCommandsResponse(commands=[])
    if live_session is not None:
        return AgentCommandsResponse(
            commands=[
                AgentCommand(
                    type="live_session",
                    live_session_id=live_session.id,
                    iface=live_session.iface,
                    bpf_filter=live_session.bpf_filter,
                    duration_seconds=live_session.duration_seconds,
                    chunk_seconds=live_session.chunk_seconds,
                    model_id=live_session.model_id,
                )
            ]
        )
    settings = capture.nfstream_settings or {}
    return AgentCommandsResponse(
        commands=[
            AgentCommand(
                type="capture",
                capture_id=capture.id,
                iface=capture.iface or "",
                bpf_filter=capture.bpf_filter,
                duration_seconds=int(settings.get("duration_seconds", 30)),
            )
        ]
    )


@router.post("/{agent_id}/captures/{capture_id}/pcap", response_model=AgentHeartbeatResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_agent_capture_pcap(
    agent_id: uuid.UUID,
    capture_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File()],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> AgentHeartbeatResponse:
    if not agent_token:
        raise AuthError()
    agent = await agent_service.authenticate(agent_id, token=agent_token)
    capture = await capture_service.ensure_agent_capture(agent_id=agent_id, capture_id=capture_id)

    settings = get_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "live_capture.pcap").name
    upload_path = settings.uploads_dir / f"{capture.id}_{safe_filename}"
    await save_upload(file, upload_path)
    await session.commit()

    background_tasks.add_task(process_uploaded_pcap, capture.id, str(upload_path))
    return AgentHeartbeatResponse(agent_id=agent.id, status=agent.status or "online", last_seen_at=agent.last_seen_at)


@router.post("/{agent_id}/captures/{capture_id}/flows", response_model=AgentHeartbeatResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_agent_capture_flows(
    agent_id: uuid.UUID,
    capture_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File()],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> AgentHeartbeatResponse:
    if not agent_token:
        raise AuthError()
    agent = await agent_service.authenticate(agent_id, token=agent_token)
    capture = await capture_service.ensure_agent_capture(agent_id=agent_id, capture_id=capture_id)

    settings = get_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "live_flows.csv").name
    upload_path = settings.uploads_dir / f"{capture.id}_{safe_filename}"
    await save_upload(file, upload_path)
    await session.commit()

    background_tasks.add_task(process_uploaded_csv, capture.id, str(upload_path))
    return AgentHeartbeatResponse(agent_id=agent.id, status=agent.status or "online", last_seen_at=agent.last_seen_at)


@router.get("/{agent_id}/captures/{capture_id}/status", response_model=AgentCaptureStatusResponse)
async def get_agent_capture_status(
    agent_id: uuid.UUID,
    capture_id: uuid.UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> AgentCaptureStatusResponse:
    if not agent_token:
        raise AuthError()
    await agent_service.authenticate(agent_id, token=agent_token)
    status_value = await capture_service.agent_capture_status(agent_id=agent_id, capture_id=capture_id)
    return AgentCaptureStatusResponse(capture_id=capture_id, status=status_value)


@router.post("/{agent_id}/captures/{capture_id}/fail", status_code=status.HTTP_204_NO_CONTENT)
async def fail_agent_capture(
    agent_id: uuid.UUID,
    capture_id: uuid.UUID,
    payload: AgentCaptureFailRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    capture_service: Annotated[CaptureService, Depends(get_capture_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> Response:
    if not agent_token:
        raise AuthError()
    await agent_service.authenticate(agent_id, token=agent_token)
    await capture_service.fail_agent_capture(
        agent_id=agent_id,
        capture_id=capture_id,
        error_message=payload.error_message,
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{agent_id}/live-sessions/{live_session_id}/fail", status_code=status.HTTP_204_NO_CONTENT)
async def fail_agent_live_session(
    agent_id: uuid.UUID,
    live_session_id: uuid.UUID,
    payload: AgentCaptureFailRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> Response:
    if not agent_token:
        raise AuthError()
    await agent_service.authenticate(agent_id, token=agent_token)
    await live_session_service.fail_agent_live_session(
        agent_id=agent_id,
        live_session_id=live_session_id,
        error_message=payload.error_message,
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{agent_id}/live-sessions/{live_session_id}/status", response_model=AgentLiveSessionStatusResponse)
async def get_agent_live_session_status(
    agent_id: uuid.UUID,
    live_session_id: uuid.UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> AgentLiveSessionStatusResponse:
    if not agent_token:
        raise AuthError()
    await agent_service.authenticate(agent_id, token=agent_token)
    status_value = await live_session_service.agent_live_session_status(
        agent_id=agent_id,
        live_session_id=live_session_id,
    )
    return AgentLiveSessionStatusResponse(live_session_id=live_session_id, status=status_value)


@router.post(
    "/{agent_id}/live-sessions/{live_session_id}/chunks",
    response_model=AgentHeartbeatResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_agent_live_session_chunk(
    agent_id: uuid.UUID,
    live_session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    captures: Annotated[CaptureSessionRepository, Depends(get_capture_session_repository)],
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File()],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> AgentHeartbeatResponse:
    if not agent_token:
        raise AuthError()
    agent = await agent_service.authenticate(agent_id, token=agent_token)

    settings = get_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "live_chunk.pcap").name
    capture = await live_session_service.create_chunk_capture(
        captures=captures,
        agent_id=agent_id,
        live_session_id=live_session_id,
        source_filename=safe_filename,
    )
    upload_path = settings.uploads_dir / f"{capture.id}_{safe_filename}"
    await save_upload(file, upload_path)
    await session.commit()

    background_tasks.add_task(process_uploaded_pcap, capture.id, str(upload_path))
    return AgentHeartbeatResponse(agent_id=agent.id, status=agent.status or "online", last_seen_at=agent.last_seen_at)


@router.post(
    "/{agent_id}/live-sessions/{live_session_id}/chunks/flows",
    response_model=AgentHeartbeatResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_agent_live_session_flows_chunk(
    agent_id: uuid.UUID,
    live_session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    captures: Annotated[CaptureSessionRepository, Depends(get_capture_session_repository)],
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File()],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> AgentHeartbeatResponse:
    if not agent_token:
        raise AuthError()
    agent = await agent_service.authenticate(agent_id, token=agent_token)

    settings = get_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "live_chunk_flows.csv").name
    capture = await live_session_service.create_chunk_capture(
        captures=captures,
        agent_id=agent_id,
        live_session_id=live_session_id,
        source_filename=safe_filename,
    )
    upload_path = settings.uploads_dir / f"{capture.id}_{safe_filename}"
    await save_upload(file, upload_path)
    await session.commit()

    background_tasks.add_task(process_uploaded_csv, capture.id, str(upload_path))
    return AgentHeartbeatResponse(agent_id=agent.id, status=agent.status or "online", last_seen_at=agent.last_seen_at)


@router.post("/{agent_id}/live-sessions/{live_session_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
async def complete_agent_live_session(
    agent_id: uuid.UUID,
    live_session_id: uuid.UUID,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    session: Annotated[AsyncSession, Depends(get_session)],
    agent_token: Annotated[str | None, Header(alias="X-Agent-Token")] = None,
) -> Response:
    if not agent_token:
        raise AuthError()
    await agent_service.authenticate(agent_id, token=agent_token)
    await live_session_service.complete_agent_live_session(agent_id=agent_id, live_session_id=live_session_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
