"""
Email Outreach Agent - Manages automated email campaigns with AI-personalized messages.
Sends personalized outreach emails and tracks engagement.
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.models.models import Lead, LeadStatus, LeadActivity, Campaign, CampaignStatus, AnalyticsEvent
from app.services.llm_service import LLMService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class EmailOutreachAgent(BaseAgent):
    """
    Sends AI-personalized outreach emails to qualified leads.
    Uses LLM to generate contextual, personalized email content.
    """

    async def execute(self, session: AsyncSession, params: dict = None) -> dict:
        params = params or {}
        campaign_id = params.get("campaign_id")
        max_emails = params.get("max_emails", self.config.get("max_emails", 20))
        min_score = params.get("min_score", self.config.get("min_score", 0.5))

        # Get qualified leads that haven't been contacted
        stmt = (
            select(Lead)
            .where(
                Lead.status.in_([LeadStatus.NEW, LeadStatus.QUALIFIED]),
                Lead.email.isnot(None),
                Lead.score >= min_score,
                Lead.last_contacted_at.is_(None),
            )
            .order_by(Lead.score.desc())
            .limit(max_emails)
        )

        if campaign_id:
            stmt = stmt.where(Lead.campaign_id == campaign_id)

        result = await session.execute(stmt)
        leads = result.scalars().all()

        # Load campaign template if specified
        template = None
        if campaign_id:
            campaign_result = await session.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            )
            campaign = campaign_result.scalar_one_or_none()
            if campaign:
                template = campaign.email_template

        sent_count = 0
        failed_count = 0
        email_svc = EmailService()

        for lead in leads:
            try:
                # Generate personalized email
                subject, body = await self._generate_email(lead, template)

                # Send email
                success = await email_svc.send_email(
                    to_email=lead.email,
                    subject=subject,
                    body=body,
                )

                if success:
                    lead.status = LeadStatus.CONTACTED
                    lead.last_contacted_at = datetime.utcnow()
                    lead.updated_at = datetime.utcnow()

                    # Log activity
                    activity = LeadActivity(
                        lead_id=lead.id,
                        activity_type="email_sent",
                        description=f"Outreach email sent: {subject}",
                        extra_data={"subject": subject, "template_used": template is not None},
                    )
                    session.add(activity)
                    sent_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.warning(f"Failed to send email to {lead.email}: {e}")
                failed_count += 1

        await session.commit()

        # Update campaign stats if applicable
        if campaign_id:
            event = AnalyticsEvent(
                event_type="campaign_emails_sent",
                event_data={"sent": sent_count, "failed": failed_count},
                campaign_id=campaign_id,
                agent_id=self.agent_id,
            )
            session.add(event)
            await session.commit()

        return {
            "success": True,
            "leads_count": sent_count,
            "emails_sent": sent_count,
            "emails_failed": failed_count,
            "total_leads_found": len(leads),
        }

    async def _generate_email(
        self, lead: Lead, template: str = None
    ) -> tuple[str, str]:
        """Generate a personalized outreach email using AI."""
        try:
            llm = LLMService()
            name = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or "there"
            company = lead.company or "your company"

            if template:
                prompt = f"""Personalize this email template for the recipient.

Template:
{template}

Recipient:
- Name: {name}
- Company: {company}
- Title: {lead.job_title or 'Professional'}
- Industry: {lead.industry or 'their industry'}

Rules:
- Keep the core message but personalize naturally
- Be professional but warm
- Keep it concise (under 200 words)

Respond in this exact format:
SUBJECT: <email subject>
BODY: <email body>"""
            else:
                prompt = f"""Write a professional outreach email for a marketing agency
reaching out to a potential client.

Recipient:
- Name: {name}
- Company: {company}
- Title: {lead.job_title or 'Professional'}
- Industry: {lead.industry or 'their industry'}

Rules:
- Be professional but personable
- Offer clear value proposition
- Include a soft call-to-action
- Keep it concise (under 150 words)
- Don't be salesy or pushy

Respond in this exact format:
SUBJECT: <email subject>
BODY: <email body>"""

            response = await llm.complete(prompt)
            subject = ""
            body = ""
            lines = response.strip().split("\n")
            body_started = False
            for line in lines:
                if line.startswith("SUBJECT:"):
                    subject = line.replace("SUBJECT:", "").strip()
                elif line.startswith("BODY:"):
                    body = line.replace("BODY:", "").strip()
                    body_started = True
                elif body_started:
                    body += "\n" + line

            return (
                subject or f"Quick question for {name}",
                body or f"Hi {name},\n\nI'd love to connect about how we can help {company} grow.\n\nBest regards",
            )
        except Exception as e:
            logger.warning(f"Email generation failed: {e}")
            name = f"{lead.first_name or 'there'}"
            return (
                f"Partnership opportunity for {lead.company or 'your team'}",
                f"Hi {name},\n\nI came across {lead.company or 'your company'} and would love to discuss how our marketing services could help drive growth.\n\nWould you be open to a quick 15-minute call?\n\nBest regards",
            )
