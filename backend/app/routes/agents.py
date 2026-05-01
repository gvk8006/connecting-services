"""
Agent Routes - API endpoints for managing and running AI agents.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Agent, AgentStatus
from app.models.schemas import AgentCreate, AgentUpdate, AgentRunRequest, AgentResponse
from app.services.orchestrator import orchestrator

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def get_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at))
    return result.scalars().all()


@router.get("/status")
async def get_agent_statuses():
    return await orchestrator.get_agent_statuses()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("")
async def create_agent(agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(**agent_data.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.put("/{agent_id}")
async def update_agent(agent_id: str, update_data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.post("/{agent_id}/run")
async def run_agent(agent_id: str, params: dict = None):
    """Trigger a specific agent to run."""
    result = await orchestrator.run_agent(agent_id, params or {})
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Agent run failed"))
    return result


@router.post("/run-all")
async def run_all_agents():
    """Run all enabled agents in sequence."""
    result = await orchestrator.run_all_agents()
    return result


@router.post("/{agent_id}/toggle")
async def toggle_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Enable or disable an agent."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_enabled = not agent.is_enabled
    await db.commit()
    return {"success": True, "is_enabled": agent.is_enabled}
