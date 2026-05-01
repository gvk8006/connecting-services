"""
Form Capture Routes - Public endpoints for lead capture forms and webhooks.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, async_session
from app.models.models import Agent, AgentType
from app.services.orchestrator import orchestrator
from app.services.websocket_manager import ws_manager

from sqlalchemy import select

router = APIRouter(prefix="/api/capture", tags=["capture"])


@router.post("/form")
async def capture_form_lead(request: Request):
    """
    Public endpoint for lead capture forms.
    Accepts form data or JSON and processes through the Form Processor Agent.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form_data = await request.form()
        data = dict(form_data)

    # Find the form processor agent
    async with async_session() as session:
        result = await session.execute(
            select(Agent).where(Agent.agent_type == AgentType.FORM_PROCESSOR).limit(1)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            return {"success": False, "error": "Form processor agent not configured"}

    # Run the form processor
    run_result = await orchestrator.run_agent(
        agent.id,
        params={"leads": [data], "source": "form_capture"},
    )

    # Notify via WebSocket
    await ws_manager.broadcast({
        "event": "new_lead",
        "data": {"source": "form_capture", "email": data.get("email")},
    })

    return {"success": True, "message": "Lead captured successfully"}


@router.post("/webhook")
async def capture_webhook(request: Request):
    """
    Webhook endpoint for external integrations (Zapier, HubSpot, etc.)
    """
    data = await request.json()
    leads = data.get("leads", [data]) if isinstance(data, dict) else data

    async with async_session() as session:
        result = await session.execute(
            select(Agent).where(Agent.agent_type == AgentType.FORM_PROCESSOR).limit(1)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return {"success": False, "error": "Form processor not configured"}

    run_result = await orchestrator.run_agent(
        agent.id,
        params={"leads": leads if isinstance(leads, list) else [leads], "source": "api_integration"},
    )

    return {"success": True, "message": f"Webhook processed"}
