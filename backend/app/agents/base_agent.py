"""
Base Agent class that all AI agents inherit from.
Provides common functionality for lead generation agents.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.models import Agent, AgentStatus, AnalyticsEvent

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all marketing AI agents."""

    def __init__(self, agent_id: str, config: dict = None):
        self.agent_id = agent_id
        self.config = config or {}
        self._running = False

    @abstractmethod
    async def execute(self, session: AsyncSession, params: dict = None) -> dict:
        """Execute the agent's main task. Must be implemented by subclasses."""
        pass

    async def run(self, params: dict = None) -> dict:
        """Run the agent with status tracking and error handling."""
        async with async_session() as session:
            try:
                self._running = True
                await self._update_status(session, AgentStatus.RUNNING)

                result = await self.execute(session, params or {})

                await self._update_status(
                    session,
                    AgentStatus.IDLE,
                    last_result=result,
                    leads_generated_delta=result.get("leads_count", 0),
                )
                await self._log_event(session, "agent_completed", result)

                return result

            except Exception as e:
                logger.exception(f"Agent {self.agent_id} failed: {e}")
                await self._update_status(
                    session, AgentStatus.ERROR, error_message=str(e)
                )
                await self._log_event(
                    session, "agent_error", {"error": str(e)}
                )
                return {"success": False, "error": str(e)}
            finally:
                self._running = False

    async def _update_status(
        self,
        session: AsyncSession,
        status: AgentStatus,
        last_result: dict = None,
        error_message: str = None,
        leads_generated_delta: int = 0,
    ):
        stmt = select(Agent).where(Agent.id == self.agent_id)
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()

        if agent:
            agent.status = status
            agent.updated_at = datetime.utcnow()
            agent.last_run_at = datetime.utcnow()
            if last_result is not None:
                agent.last_result = last_result
            if error_message is not None:
                agent.error_message = error_message
            if leads_generated_delta > 0:
                agent.leads_generated = (agent.leads_generated or 0) + leads_generated_delta
            await session.commit()

    async def _log_event(self, session: AsyncSession, event_type: str, data: dict):
        event = AnalyticsEvent(
            event_type=event_type,
            event_data=data,
            agent_id=self.agent_id,
        )
        session.add(event)
        await session.commit()
