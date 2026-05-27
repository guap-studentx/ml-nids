import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_capture_session_repository, get_current_user, get_live_session_service
from app.models.user import User
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.schemas.capture import CaptureRead
from app.schemas.live_session import LiveSessionCreate, LiveSessionListResponse, LiveSessionRead
from app.services.live_session_service import LiveSessionService

router = APIRouter(prefix="/live-sessions", tags=["live-sessions"])


@router.post("", response_model=LiveSessionRead, status_code=201)
async def create_live_session(
    payload: LiveSessionCreate,
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LiveSessionRead:
    live_session = await live_session_service.create(
        name=payload.name,
        agent_id=payload.agent_id,
        iface=payload.iface,
        bpf_filter=payload.bpf_filter,
        model_id=payload.model_id,
        created_by=current_user.id,
        chunk_seconds=payload.chunk_seconds,
        duration_seconds=payload.duration_seconds,
    )
    await session.commit()
    await session.refresh(live_session)
    return live_session


@router.get("", response_model=LiveSessionListResponse)
async def list_live_sessions(
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    _: Annotated[User, Depends(get_current_user)],
    status: str | None = None,
    agent_id: uuid.UUID | None = None,
    model_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> LiveSessionListResponse:
    items, total = await live_session_service.list(
        status=status,
        agent_id=agent_id,
        model_id=model_id,
        limit=limit,
        offset=offset,
    )
    return LiveSessionListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{live_session_id}", response_model=LiveSessionRead)
async def get_live_session(
    live_session_id: uuid.UUID,
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> LiveSessionRead:
    return await live_session_service.get(live_session_id)


@router.get("/{live_session_id}/chunks", response_model=list[CaptureRead])
async def get_live_session_chunks(
    live_session_id: uuid.UUID,
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    captures: Annotated[CaptureSessionRepository, Depends(get_capture_session_repository)],
    _: Annotated[User, Depends(get_current_user)],
) -> list:
    await live_session_service.get(live_session_id)
    return await captures.list_by_live_session(live_session_id)


@router.post("/{live_session_id}/stop", response_model=LiveSessionRead)
async def stop_live_session(
    live_session_id: uuid.UUID,
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LiveSessionRead:
    live_session = await live_session_service.stop(live_session_id)
    await session.commit()
    return live_session


@router.delete("/{live_session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_live_session(
    live_session_id: uuid.UUID,
    live_session_service: Annotated[LiveSessionService, Depends(get_live_session_service)],
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await live_session_service.delete(live_session_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
