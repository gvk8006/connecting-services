"""
One-time migration: Set lead_type on existing leads.

- Leads with custom_fields.lead_type == "seeker" or "seeker" in tags -> lead_type = "seeker"
- All other leads -> lead_type = "provider"
- Auto-create ServiceRequest for seeker leads that have service_needed

Run from backend dir:
  python -m scripts.migrate_lead_types
"""
import asyncio
import sys
import os

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, text
from app.core.database import async_session, init_db
from app.models.models import Lead, ServiceRequest


async def migrate():
    await init_db()

    async with async_session() as session:
        # First, add lead_type column if it doesn't exist (SQLite)
        try:
            await session.execute(text(
                "ALTER TABLE leads ADD COLUMN lead_type VARCHAR(20) DEFAULT 'unknown'"
            ))
            await session.commit()
            print("Added lead_type column to leads table")
        except Exception:
            await session.rollback()
            print("lead_type column already exists")

        # Load all leads
        result = await session.execute(select(Lead))
        leads = result.scalars().all()
        print(f"Found {len(leads)} total leads")

        seekers = 0
        providers = 0

        for lead in leads:
            cf = lead.custom_fields or {}
            tags = lead.tags or []

            if cf.get("lead_type") == "seeker" or "seeker" in tags:
                lead.lead_type = "seeker"
                seekers += 1

                # Auto-create ServiceRequest if service_needed is set
                service = cf.get("service_needed")
                if service:
                    existing = await session.execute(
                        select(ServiceRequest).where(ServiceRequest.lead_id == lead.id)
                    )
                    if not existing.scalar_one_or_none():
                        # Build title from lead notes
                        title = f"Looking for {service.replace('_', ' ')} services"
                        if lead.notes:
                            # Use first line of notes as title
                            first_line = lead.notes.split("\n")[0][:200]
                            if ":" in first_line:
                                title = first_line.split(":", 1)[1].strip()[:200]
                            elif len(first_line) > 20:
                                title = first_line

                        req = ServiceRequest(
                            lead_id=lead.id,
                            title=title,
                            description=lead.notes,
                            service_category=service,
                        )
                        session.add(req)
            else:
                lead.lead_type = "provider"
                providers += 1

        await session.commit()
        print(f"Migration complete: {seekers} seekers, {providers} providers")

        # Verify service requests
        req_count = await session.execute(select(ServiceRequest))
        reqs = req_count.scalars().all()
        print(f"Service requests created: {len(reqs)}")


if __name__ == "__main__":
    asyncio.run(migrate())
