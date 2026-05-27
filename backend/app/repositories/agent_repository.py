from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent


class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_online(self, *, seen_after: datetime | None = None) -> int:
        query = select(func.count(Agent.id)).where(Agent.status == "online")
        if seen_after is not None:
            query = query.where(Agent.last_seen_at >= seen_after)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def list(self) -> list[Agent]:
        result = await self.session.execute(select(Agent).order_by(Agent.name))
        return list(result.scalars().all())

    async def get(self, agent_id: uuid.UUID) -> Agent | None:
        result = await self.session.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def create(self, *, name: str, token_hash: str) -> Agent:
        agent = Agent(name=name, token_hash=token_hash, status="offline")
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def delete(self, agent: Agent) -> None:
        await self.session.delete(agent)
        await self.session.flush()

    async def mark_seen(
        self,
        agent: Agent,
        *,
        last_seen_at: datetime,
        available_ifaces: list[str],
        metadata: dict[str, Any] | None = None,
        status: str = "online",
    ) -> Agent:
        agent.last_seen_at = last_seen_at
        agent.available_ifaces = available_ifaces
        agent.agent_metadata = metadata
        agent.status = status
        await self.session.flush()
        return agent
