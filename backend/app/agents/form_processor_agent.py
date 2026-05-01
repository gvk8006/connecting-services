"""
Form Processor Agent - Handles inbound lead capture from forms, landing pages, and API integrations.
Processes, validates, enriches, and scores incoming leads.
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.models.models import Lead, LeadSource, LeadActivity, AnalyticsEvent

logger = logging.getLogger(__name__)


class FormProcessorAgent(BaseAgent):
    """
    Processes inbound leads from web forms, landing pages, and API integrations.
    Validates, deduplicates, enriches, and queues leads for qualification.
    """

    async def execute(self, session: AsyncSession, params: dict = None) -> dict:
        params = params or {}
        leads_data = params.get("leads", [])
        source = params.get("source", "form_capture")

        if not leads_data:
            return {"success": True, "leads_count": 0, "message": "No leads to process"}

        processed = 0
        duplicates = 0

        for data in leads_data:
            email = data.get("email")
            if not email:
                continue

            # Check for duplicates
            existing = await session.execute(
                select(Lead).where(Lead.email == email)
            )
            if existing.scalar_one_or_none():
                duplicates += 1
                continue

            lead = Lead(
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                email=email,
                phone=data.get("phone"),
                company=data.get("company"),
                job_title=data.get("job_title"),
                website=data.get("website"),
                linkedin_url=data.get("linkedin_url"),
                source=LeadSource(source) if source in LeadSource.__members__.values() else LeadSource.FORM_CAPTURE,
                industry=data.get("industry"),
                company_size=data.get("company_size"),
                location=data.get("location"),
                notes=data.get("notes") or data.get("message"),
                tags=data.get("tags", ["form_capture"]),
                custom_fields=data.get("custom_fields", {}),
            )
            session.add(lead)

            # Log activity
            activity = LeadActivity(
                lead_id=lead.id,
                activity_type="form_submission",
                description=f"Lead captured from {source}",
                extra_data={"source": source, "raw_data": data},
            )
            session.add(activity)
            processed += 1

        await session.commit()

        return {
            "success": True,
            "leads_count": processed,
            "duplicates_skipped": duplicates,
            "total_received": len(leads_data),
        }
