from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import get_settings
from app.exceptions import AgentNotFoundError, AgentOfflineError, AuthError
from app.models.agent import Agent
from app.repositories.agent_repository import AgentRepository
from app.security import hash_password, verify_password


class AgentService:
    def __init__(self, agents: AgentRepository, offline_after_seconds: int | None = None):
        self.agents = agents
        self.offline_after_seconds = offline_after_seconds or get_settings().agent_offline_after_seconds

    async def list(self) -> list[Agent]:
        agents = await self.agents.list()
        for agent in agents:
            agent.status = self.effective_status(agent)
        return agents

    async def get(self, agent_id: uuid.UUID) -> Agent:
        agent = await self.agents.get(agent_id)
        if agent is None:
            raise AgentNotFoundError()
        return agent

    async def create(self, *, name: str) -> tuple[Agent, str]:
        token = secrets.token_urlsafe(32)
        agent = await self.agents.create(name=name, token_hash=hash_password(token))
        return agent, token

    async def delete(self, agent_id: uuid.UUID) -> None:
        agent = await self.get(agent_id)
        await self.agents.delete(agent)

    async def ifaces(self, agent_id: uuid.UUID) -> list[str]:
        agent = await self.get(agent_id)
        if self.effective_status(agent) != "online":
            raise AgentOfflineError()
        return agent.available_ifaces or []

    def effective_status(self, agent: Agent) -> str:
        if agent.status != "online":
            return agent.status or "offline"
        if agent.last_seen_at is None:
            return "offline"
        last_seen_at = agent.last_seen_at
        if last_seen_at.tzinfo is None:
            last_seen_at = last_seen_at.replace(tzinfo=UTC)
        if datetime.now(UTC) - last_seen_at > timedelta(seconds=self.offline_after_seconds):
            return "offline"
        return "online"

    async def mark_seen(
        self,
        agent_id: uuid.UUID,
        *,
        available_ifaces: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> Agent:
        agent = await self.get(agent_id)
        return await self.agents.mark_seen(
            agent,
            last_seen_at=datetime.now(UTC),
            available_ifaces=available_ifaces,
            metadata=metadata,
            status="online",
        )

    async def heartbeat(
        self,
        agent_id: uuid.UUID,
        *,
        token: str,
        available_ifaces: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> Agent:
        agent = await self.get(agent_id)
        if not verify_password(token, agent.token_hash):
            raise AuthError()
        return await self.agents.mark_seen(
            agent,
            last_seen_at=datetime.now(UTC),
            available_ifaces=available_ifaces,
            metadata=metadata,
            status="online",
        )

    async def authenticate(self, agent_id: uuid.UUID, *, token: str) -> Agent:
        agent = await self.get(agent_id)
        if not verify_password(token, agent.token_hash):
            raise AuthError()
        return agent
