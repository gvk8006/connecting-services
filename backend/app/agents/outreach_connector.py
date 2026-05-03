"""
Outreach Connector Agent - Generates personalized outreach messages for each
service category and manages the connection workflow.
Reaches out to leads with tailored pitches for: Website, SaaS, AI Agents,
Chatbot, Web App, CRM, QC AI Tool.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.models.models import Lead, LeadStatus, LeadActivity
from app.services.llm_service import LLMService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

# Service-specific outreach templates
SERVICE_PITCHES = {
    "website": {
        "subject": "Professional website for {company}",
        "pitch": (
            "I noticed you're looking for a professional website for your business. "
            "We specialise in building fast, mobile-responsive websites that convert visitors into customers. "
            "From landing pages to full business sites with booking systems and ecommerce -- we handle it all.\n\n"
            "Would love to show you some recent work and discuss your project."
        ),
    },
    "saas": {
        "subject": "SaaS product development for {company}",
        "pitch": (
            "I saw you're exploring building a SaaS product. "
            "We've built and launched multiple SaaS platforms -- from MVP to scale. "
            "Our stack includes Next.js, React, Node.js, and cloud-native architecture "
            "with built-in auth, billing, analytics, and multi-tenancy.\n\n"
            "Happy to jump on a quick call to discuss your SaaS idea and roadmap."
        ),
    },
    "ai_agents": {
        "subject": "Custom AI agents for {company}",
        "pitch": (
            "I noticed you're looking into AI agents for your business. "
            "We build autonomous AI agents that automate real workflows -- lead generation, "
            "customer support, data processing, and internal operations. "
            "Our agents integrate with your existing tools and learn from your data.\n\n"
            "Would you be interested in a quick demo of what an AI agent could do for your specific use case?"
        ),
    },
    "chatbot": {
        "subject": "AI chatbot solution for {company}",
        "pitch": (
            "I saw you're looking for a chatbot for your business. "
            "We build intelligent AI chatbots powered by GPT that handle customer queries 24/7, "
            "qualify leads, book appointments, and integrate directly with your website and CRM. "
            "Typical clients see 40-60% reduction in support tickets.\n\n"
            "Want to see a live demo tailored to your industry?"
        ),
    },
    "web_app": {
        "subject": "Custom web application for {company}",
        "pitch": (
            "I noticed you need a custom web application built. "
            "We develop full-stack web apps -- dashboards, portals, internal tools, "
            "and customer-facing platforms. Built with modern tech (React, Next.js, Python) "
            "for speed, security, and scalability.\n\n"
            "Would love to understand your requirements and share a quick estimate."
        ),
    },
    "crm": {
        "subject": "Custom CRM solution for {company}",
        "pitch": (
            "I saw you're looking for a CRM solution. "
            "Off-the-shelf CRMs often don't fit. We build custom CRMs tailored to your exact workflow -- "
            "lead tracking, pipeline management, automated follow-ups, reporting dashboards, "
            "and integrations with your existing tools.\n\n"
            "Shall I walk you through a custom CRM we recently built for a similar business?"
        ),
    },
    "qc_ai": {
        "subject": "AI Quality Check tool for {company}",
        "pitch": (
            "I noticed you're exploring AI-powered quality control. "
            "We build custom AI QC tools that automate visual inspection, defect detection, "
            "compliance checking, and quality scoring. Works with images, documents, or production data. "
            "Our solutions integrate directly into your existing QC pipeline.\n\n"
            "Interested in seeing how AI-powered QC could work for your specific use case?"
        ),
    },
}


class OutreachConnector(BaseAgent):
    """
    Connects with prospected leads by generating and sending personalised
    outreach messages based on the service they need.
    """

    async def execute(self, session: AsyncSession, params: dict = None) -> dict:
        params = params or {}
        max_outreach = params.get("max_outreach", self.config.get("max_outreach", 20))
        min_score = params.get("min_score", self.config.get("min_score", 0.4))
        service_filter = params.get("service_filter", None)

        # Get leads that haven't been contacted
        stmt = (
            select(Lead)
            .where(
                Lead.status.in_([LeadStatus.NEW, LeadStatus.QUALIFIED]),
                Lead.last_contacted_at.is_(None),
            )
            .order_by(Lead.score.desc())
            .limit(max_outreach)
        )
        result = await session.execute(stmt)
        leads = result.scalars().all()

        sent_count = 0
        failed_count = 0
        sent_services: dict[str, int] = {}
        email_svc = EmailService()

        for lead in leads:
            # Determine which service they need
            custom = lead.custom_fields or {}
            service_needed = custom.get("service_needed", "website")

            if service_filter and service_needed != service_filter:
                continue

            pitch_data = SERVICE_PITCHES.get(service_needed, SERVICE_PITCHES["website"])

            name = f"{lead.first_name or 'there'}"
            company = lead.company or "your business"
            subject = pitch_data["subject"].format(company=company)
            body = f"Hi {name},\n\n{pitch_data['pitch']}\n\nBest regards"

            # Try AI personalization if LLM is available
            try:
                llm = LLMService()
                if llm.api_key:
                    prompt = f"""Personalise this outreach message. Keep it under 150 words, professional but warm.

Recipient: {name} ({lead.job_title or 'Business Owner'} at {company})
Service they need: {SERVICE_PITCHES.get(service_needed, {}).get('subject', service_needed)}
Context from their post: {(lead.notes or '')[:300]}

Base pitch: {pitch_data['pitch']}

Respond with:
SUBJECT: <personalised subject>
BODY: <personalised message>"""
                    response = await llm.complete(prompt)
                    for line in response.strip().split("\n"):
                        if line.startswith("SUBJECT:"):
                            subject = line.replace("SUBJECT:", "").strip()
                        elif line.startswith("BODY:"):
                            body = line.replace("BODY:", "").strip()
            except Exception as e:
                logger.info(f"LLM personalisation skipped: {e}")

            # Send (or simulate) outreach
            try:
                if lead.email:
                    success = await email_svc.send_email(lead.email, subject, body)
                else:
                    # For Reddit/Twitter leads without email, log the outreach for manual follow-up
                    success = True
                    logger.info(f"Manual outreach needed for {lead.first_name} via {lead.source}")

                if success:
                    lead.status = LeadStatus.CONTACTED
                    lead.last_contacted_at = datetime.utcnow()
                    lead.updated_at = datetime.utcnow()

                    activity = LeadActivity(
                        lead_id=lead.id,
                        activity_type="outreach_sent",
                        description=f"Outreach for {service_needed}: {subject}",
                        extra_data={
                            "subject": subject,
                            "service": service_needed,
                            "channel": "email" if lead.email else "manual",
                            "message_preview": body[:200],
                        },
                    )
                    session.add(activity)
                    sent_count += 1
                    sent_services[service_needed] = sent_services.get(service_needed, 0) + 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.warning(f"Outreach failed for {lead.email}: {e}")
                failed_count += 1

        await session.commit()

        # Telegram notification
        from app.services.telegram_notifier import telegram
        await telegram.notify_outreach_sent(sent_count, sent_services)

        return {
            "success": True,
            "leads_count": sent_count,
            "outreach_sent": sent_count,
            "outreach_failed": failed_count,
            "total_leads_processed": len(leads),
        }
