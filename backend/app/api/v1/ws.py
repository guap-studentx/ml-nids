import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import async_session_factory
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.repositories.user_repository import UserRepository
from app.security import decode_access_token

router = APIRouter(prefix="/ws", tags=["websocket"])

TERMINAL_STATUSES = {"completed", "failed", "stopped"}


@router.websocket("/captures/{capture_id}")
async def capture_progress(websocket: WebSocket, capture_id: uuid.UUID, token: str | None = None) -> None:
    if not await _authenticate(token):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            payload = await _capture_payload(capture_id)
            if payload is None:
                await websocket.send_json({"type": "error", "detail": "Capture session not found"})
                await websocket.close(code=1008)
                return

            await websocket.send_json({"type": "capture", "capture": payload})
            if payload["status"] in TERMINAL_STATUSES:
                await websocket.close(code=1000)
                return
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


async def _authenticate(token: str | None) -> bool:
    if not token:
        return False
    try:
        payload = decode_access_token(token)
    except ValueError:
        return False
    user_id = payload.get("sub")
    if not user_id:
        return False
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_id(user_id)
        return bool(user and user.is_active)


async def _capture_payload(capture_id: uuid.UUID) -> dict | None:
    async with async_session_factory() as session:
        capture = await CaptureSessionRepository(session).get(capture_id)
        if capture is None:
            return None
        return {
            "id": str(capture.id),
            "name": capture.name,
            "mode": capture.mode,
            "source_filename": capture.source_filename,
            "agent_id": str(capture.agent_id) if capture.agent_id else None,
            "iface": capture.iface,
            "bpf_filter": capture.bpf_filter,
            "model_id": str(capture.model_id) if capture.model_id else None,
            "status": capture.status,
            "flows_total": capture.flows_total,
            "flows_anomaly": capture.flows_anomaly,
            "started_at": _iso(capture.started_at),
            "finished_at": _iso(capture.finished_at),
            "created_by": str(capture.created_by) if capture.created_by else None,
            "error_message": capture.error_message,
            "nfstream_settings": capture.nfstream_settings,
        }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
