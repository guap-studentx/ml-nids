import uuid

from app.exceptions import AgentCaptureError, AgentOfflineError, LiveSessionNotFoundError, ModelNotFoundError
from app.models.live_session import LiveSession
from app.repositories.agent_repository import AgentRepository
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.repositories.live_session_repository import LiveSessionRepository
from app.repositories.model_repository import ModelRepository
from app.services.agent_service import AgentService


class LiveSessionService:
    def __init__(
        self,
        live_sessions: LiveSessionRepository,
        models: ModelRepository,
        agents: AgentRepository,
    ):
        self.live_sessions = live_sessions
        self.models = models
        self.agents = agents

    async def list(
        self,
        *,
        status: str | None = None,
        agent_id: uuid.UUID | None = None,
        model_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LiveSession], int]:
        return await self.live_sessions.list(
            status=status,
            agent_id=agent_id,
            model_id=model_id,
            limit=limit,
            offset=offset,
        )

    async def get(self, live_session_id: uuid.UUID) -> LiveSession:
        live_session = await self.live_sessions.get(live_session_id)
        if live_session is None:
            raise LiveSessionNotFoundError()
        return live_session

    async def delete(self, live_session_id: uuid.UUID) -> None:
        live_session = await self.get(live_session_id)
        await self.live_sessions.delete(live_session)

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
        model = await self.models.get(model_id)
        if model is None or not model.is_active:
            raise ModelNotFoundError()

        agent_service = AgentService(self.agents)
        agent = await agent_service.get(agent_id)
        if agent_service.effective_status(agent) != "online":
            raise AgentOfflineError()

        return await self.live_sessions.create(
            name=name,
            agent_id=agent_id,
            iface=iface,
            bpf_filter=bpf_filter,
            model_id=model_id,
            created_by=created_by,
            chunk_seconds=chunk_seconds,
            duration_seconds=duration_seconds,
        )

    async def stop(self, live_session_id: uuid.UUID) -> LiveSession:
        live_session = await self.get(live_session_id)
        if live_session.status == "pending":
            return await self.live_sessions.mark_stopped(live_session)
        if live_session.status == "running":
            return await self.live_sessions.mark_stopping(live_session)
        return live_session

    async def claim_next_command(self, agent_id: uuid.UUID) -> LiveSession | None:
        live_session = await self.live_sessions.pending_for_agent(agent_id)
        if live_session is None:
            return None
        return await self.live_sessions.mark_running(live_session)

    async def fail_agent_live_session(
        self,
        *,
        agent_id: uuid.UUID,
        live_session_id: uuid.UUID,
        error_message: str,
    ) -> LiveSession:
        live_session = await self.get(live_session_id)
        self._ensure_agent_session(live_session, agent_id)
        return await self.live_sessions.mark_failed(live_session, error_message=error_message)

    async def complete_agent_live_session(self, *, agent_id: uuid.UUID, live_session_id: uuid.UUID) -> LiveSession:
        live_session = await self.get(live_session_id)
        self._ensure_agent_session(live_session, agent_id)
        if live_session.status == "running":
            return await self.live_sessions.mark_completed(live_session)
        if live_session.status == "stopping":
            return await self.live_sessions.mark_stopped(live_session)
        return live_session

    async def agent_live_session_status(self, *, agent_id: uuid.UUID, live_session_id: uuid.UUID) -> str:
        live_session = await self.get(live_session_id)
        self._ensure_agent_session(live_session, agent_id)
        return live_session.status

    async def create_chunk_capture(
        self,
        *,
        captures: CaptureSessionRepository,
        agent_id: uuid.UUID,
        live_session_id: uuid.UUID,
        source_filename: str,
    ):
        live_session = await self.get(live_session_id)
        self._ensure_agent_session(live_session, agent_id)
        if live_session.status not in {"running", "stopping"}:
            raise AgentCaptureError()
        chunk_index = await captures.next_chunk_index(live_session.id)
        return await captures.create_live_chunk(
            live_session_id=live_session.id,
            chunk_index=chunk_index,
            model_id=live_session.model_id,
            agent_id=live_session.agent_id,
            iface=live_session.iface,
            bpf_filter=live_session.bpf_filter,
            created_by=live_session.created_by,
            name=f"{live_session.name or 'Live session'} chunk {chunk_index}",
            source_filename=source_filename,
            nfstream_settings={"chunk_seconds": live_session.chunk_seconds},
        )

    async def refresh_aggregates(
        self,
        *,
        captures: CaptureSessionRepository,
        live_session_id: uuid.UUID,
    ) -> LiveSession | None:
        live_session = await self.live_sessions.get(live_session_id)
        if live_session is None:
            return None
        flows_total, flows_anomaly = await captures.aggregate_live_session(live_session_id)
        return await self.live_sessions.update_aggregates(
            live_session,
            flows_total=flows_total,
            flows_anomaly=flows_anomaly,
        )

    def _ensure_agent_session(self, live_session: LiveSession, agent_id: uuid.UUID) -> None:
        if live_session.agent_id != agent_id:
            raise AgentCaptureError()
