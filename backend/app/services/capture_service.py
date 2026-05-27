import uuid
from datetime import datetime

from app.exceptions import AgentCaptureError, AgentNotFoundError, AgentOfflineError, CaptureNotFoundError, ModelNotFoundError
from app.models.capture_session import CaptureSession
from app.repositories.agent_repository import AgentRepository
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.repositories.model_repository import ModelRepository
from app.services.agent_service import AgentService


class CaptureService:
    def __init__(
        self,
        captures: CaptureSessionRepository,
        models: ModelRepository,
        agents: AgentRepository | None = None,
    ):
        self.captures = captures
        self.models = models
        self.agents = agents

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
        return await self.captures.list(
            mode=mode,
            status=status,
            model_id=model_id,
            started_from=started_from,
            started_to=started_to,
            limit=limit,
            offset=offset,
        )

    async def get(self, capture_id: uuid.UUID) -> CaptureSession:
        capture = await self.captures.get(capture_id)
        if capture is None:
            raise CaptureNotFoundError()
        return capture

    async def delete(self, capture_id: uuid.UUID) -> None:
        capture = await self.get(capture_id)
        await self.captures.delete(capture)

    async def stop(self, capture_id: uuid.UUID) -> CaptureSession:
        capture = await self.get(capture_id)
        if capture.status == "pending":
            return await self.captures.mark_stopped(capture, error_message="Stopped before agent started capture")
        if capture.status == "running":
            return await self.captures.mark_stopping(capture)
        return capture

    async def create_placeholder(
        self,
        *,
        mode: str,
        model_id: uuid.UUID,
        created_by: uuid.UUID,
        name: str | None,
    ) -> CaptureSession:
        model = await self.models.get(model_id)
        if model is None or not model.is_active:
            raise ModelNotFoundError()
        return await self.captures.create(mode=mode, model_id=model_id, created_by=created_by, name=name)

    async def create_offline_csv(
        self,
        *,
        model_id: uuid.UUID,
        created_by: uuid.UUID,
        name: str | None,
        source_filename: str,
    ) -> CaptureSession:
        capture = await self.create_placeholder(
            mode="offline_csv",
            model_id=model_id,
            created_by=created_by,
            name=name,
        )
        capture.source_filename = source_filename
        return capture

    async def create_offline_pcap(
        self,
        *,
        model_id: uuid.UUID,
        created_by: uuid.UUID,
        name: str | None,
        source_filename: str,
        nfstream_settings: dict,
    ) -> CaptureSession:
        capture = await self.create_placeholder(
            mode="offline_pcap",
            model_id=model_id,
            created_by=created_by,
            name=name,
        )
        capture.source_filename = source_filename
        capture.nfstream_settings = nfstream_settings
        return capture

    async def create_live(
        self,
        *,
        model_id: uuid.UUID,
        created_by: uuid.UUID,
        agent_id: uuid.UUID,
        iface: str,
        duration_seconds: int,
        name: str | None = None,
        bpf_filter: str | None = None,
    ) -> CaptureSession:
        if self.agents is None:
            raise AgentNotFoundError()
        agent_service = AgentService(self.agents)
        agent = await agent_service.get(agent_id)
        if agent_service.effective_status(agent) != "online":
            raise AgentOfflineError()

        capture = await self.create_placeholder(
            mode="live",
            model_id=model_id,
            created_by=created_by,
            name=name,
        )
        capture.agent_id = agent_id
        capture.iface = iface
        capture.bpf_filter = bpf_filter
        capture.nfstream_settings = {"duration_seconds": duration_seconds}
        return capture

    async def claim_next_live_command(self, agent_id: uuid.UUID) -> CaptureSession | None:
        capture = await self.captures.pending_live_for_agent(agent_id)
        if capture is None:
            return None
        return await self.captures.mark_running(capture)

    async def fail_agent_capture(self, *, agent_id: uuid.UUID, capture_id: uuid.UUID, error_message: str) -> CaptureSession:
        capture = await self.get(capture_id)
        self._ensure_agent_capture(capture, agent_id)
        return await self.captures.mark_failed(capture, error_message=error_message)

    async def ensure_agent_capture(self, *, agent_id: uuid.UUID, capture_id: uuid.UUID) -> CaptureSession:
        capture = await self.get(capture_id)
        self._ensure_agent_capture(capture, agent_id)
        return capture

    async def agent_capture_status(self, *, agent_id: uuid.UUID, capture_id: uuid.UUID) -> str:
        capture = await self.ensure_agent_capture(agent_id=agent_id, capture_id=capture_id)
        return capture.status

    def _ensure_agent_capture(self, capture: CaptureSession, agent_id: uuid.UUID) -> None:
        if capture.mode != "live" or capture.agent_id != agent_id:
            raise AgentCaptureError()
