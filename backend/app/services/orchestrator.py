"""
Agent Orchestrator - Manages the lifecycle and execution of all AI agents.
Provides a centralized interface for starting, stopping, and monitoring agents.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.models import Agent, AgentType, AgentStatus
from app.agents.scraper_agent import WebScraperAgent
from app.agents.qualifier_agent import QualifierAgent
from app.agents.email_agent import EmailOutreachAgent
from app.agents.social_monitor_agent import SocialMonitorAgent
from app.agents.form_processor_agent import FormProcessorAgent
from app.agents.prospector_tool import ProspectorTool
from app.agents.outreach_connector import OutreachConnector
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# Map agent types to their implementations
AGENT_CLASSES = {
    AgentType.SCRAPER: WebScraperAgent,
    AgentType.QUALIFIER: QualifierAgent,
    AgentType.EMAIL_OUTREACH: EmailOutreachAgent,
    AgentType.SOCIAL_MONITOR: SocialMonitorAgent,
    AgentType.FORM_PROCESSOR: FormProcessorAgent,
    AgentType.PROSPECTOR: ProspectorTool,
    AgentType.OUTREACH_CONNECTOR: OutreachConnector,
}


class AgentOrchestrator:
    """Manages all AI agents - starting, stopping, scheduling, and monitoring."""

    def __init__(self):
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def initialize_default_agents(self):
        """Create default agents if they don't exist."""
        async with async_session() as session:
            result = await session.execute(select(Agent))
            existing = result.scalars().all()

            if existing:
                return

            defaults = [
                Agent(
                    name="Service Prospector",
                    agent_type=AgentType.PROSPECTOR,
                    config={
                        "services": ["website", "saas", "ai_agents", "chatbot", "web_app", "crm", "qc_ai"],
                        "channels": ["google", "reddit", "twitter"],
                        "max_per_service": 15,
                    },
                    is_enabled=True,
                ),
                Agent(
                    name="Lead Qualifier",
                    agent_type=AgentType.QUALIFIER,
                    config={"batch_size": 50, "min_score": 0.4},
                    is_enabled=True,
                ),
                Agent(
                    name="Outreach Connector",
                    agent_type=AgentType.OUTREACH_CONNECTOR,
                    config={"max_outreach": 30, "min_score": 0.4},
                    is_enabled=True,
                ),
                Agent(
                    name="Form Processor",
                    agent_type=AgentType.FORM_PROCESSOR,
                    config={},
                    is_enabled=True,
                ),
            ]

            for agent in defaults:
                session.add(agent)
            await session.commit()
            logger.info("Default agents initialized")

    async def run_agent(self, agent_id: str, params: dict = None) -> dict:
        """Run a specific agent by ID."""
        async with async_session() as session:
            result = await session.execute(select(Agent).where(Agent.id == agent_id))
            agent_model = result.scalar_one_or_none()

            if not agent_model:
                return {"success": False, "error": "Agent not found"}

            if not agent_model.is_enabled:
                return {"success": False, "error": "Agent is disabled"}

            agent_type = agent_model.agent_type
            if isinstance(agent_type, str):
                agent_type = AgentType(agent_type)

            agent_class = AGENT_CLASSES.get(agent_type)
            if not agent_class:
                return {"success": False, "error": f"Unknown agent type: {agent_type}"}

            agent_instance = agent_class(
                agent_id=agent_id,
                config=agent_model.config or {},
            )

        # Run in background
        async def _run_and_notify():
            result = await agent_instance.run(params)
            await ws_manager.broadcast({
                "event": "agent_completed",
                "data": {
                    "agent_id": agent_id,
                    "result": result,
                },
            })
            return result

        task = asyncio.create_task(_run_and_notify())
        self._running_tasks[agent_id] = task

        # Notify via WebSocket
        await ws_manager.broadcast({
            "event": "agent_started",
            "data": {"agent_id": agent_id},
        })

        return {"success": True, "message": f"Agent {agent_id} started"}

    async def run_all_agents(self) -> dict:
        """Run all enabled agents sequentially: scraper -> qualifier -> outreach."""
        async with async_session() as session:
            result = await session.execute(
                select(Agent).where(Agent.is_enabled == True)
            )
            agents = result.scalars().all()

        results = {}
        # Run in priority order: prospect -> qualify -> outreach
        order = [AgentType.PROSPECTOR, AgentType.FORM_PROCESSOR, AgentType.QUALIFIER, AgentType.OUTREACH_CONNECTOR]

        for agent_type in order:
            matching = [a for a in agents if a.agent_type == agent_type]
            for agent_model in matching:
                agent_result = await self.run_agent(agent_model.id)
                results[agent_model.name] = agent_result

                # Wait for the task to complete before next step
                if agent_model.id in self._running_tasks:
                    try:
                        await self._running_tasks[agent_model.id]
                    except Exception as e:
                        logger.error(f"Agent {agent_model.name} failed: {e}")

        return {"success": True, "results": results}

    async def get_agent_statuses(self) -> list[dict]:
        """Get current status of all agents."""
        async with async_session() as session:
            result = await session.execute(select(Agent).order_by(Agent.created_at))
            agents = result.scalars().all()
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.agent_type.value if hasattr(a.agent_type, "value") else str(a.agent_type),
                    "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                    "is_enabled": a.is_enabled,
                    "leads_generated": a.leads_generated or 0,
                    "last_run_at": a.last_run_at.isoformat() if a.last_run_at else None,
                    "error_message": a.error_message,
                }
                for a in agents
            ]


# Singleton instance
orchestrator = AgentOrchestrator()
