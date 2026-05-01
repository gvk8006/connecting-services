"""
Lead Qualifier Agent - Uses AI to score and qualify leads based on
company data, engagement signals, and fit criteria.
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.models.models import Lead, LeadStatus, AnalyticsEvent
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class QualifierAgent(BaseAgent):
    """
    AI-powered lead qualification agent.
    Scores leads based on:
    - Company fit (size, industry, location)
    - Contact completeness (email, phone, LinkedIn)
    - Engagement signals
    - AI analysis of lead quality
    """

    async def execute(self, session: AsyncSession, params: dict = None) -> dict:
        params = params or {}
        batch_size = params.get("batch_size", self.config.get("batch_size", 50))
        min_score = params.get("min_score", self.config.get("min_score", 0.3))

        # Fetch unscored or low-scored leads
        stmt = (
            select(Lead)
            .where(Lead.score == 0.0)
            .order_by(Lead.created_at.desc())
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        leads = result.scalars().all()

        scored_count = 0
        qualified_count = 0

        for lead in leads:
            score, breakdown = await self._score_lead(lead)
            lead.score = score
            lead.score_breakdown = breakdown

            if score >= min_score and lead.status == LeadStatus.NEW:
                lead.status = LeadStatus.QUALIFIED
                qualified_count += 1

            # Generate AI summary and next action
            summary, next_action = await self._generate_insights(lead, score, breakdown)
            lead.ai_summary = summary
            lead.ai_next_action = next_action
            lead.updated_at = datetime.utcnow()

            scored_count += 1

            # Log scoring event
            event = AnalyticsEvent(
                event_type="lead_scored",
                event_data={"score": score, "breakdown": breakdown},
                lead_id=lead.id,
                agent_id=self.agent_id,
            )
            session.add(event)

        await session.commit()

        return {
            "success": True,
            "leads_count": scored_count,
            "qualified_count": qualified_count,
            "total_processed": len(leads),
        }

    async def _score_lead(self, lead: Lead) -> tuple[float, dict]:
        """Score a lead on a 0-1 scale with breakdown."""
        breakdown = {}
        total = 0.0
        max_score = 0.0

        # Contact completeness (25% weight)
        contact_score = 0.0
        if lead.email:
            contact_score += 0.4
        if lead.phone:
            contact_score += 0.25
        if lead.linkedin_url:
            contact_score += 0.2
        if lead.twitter_handle:
            contact_score += 0.15
        breakdown["contact_completeness"] = round(contact_score, 2)
        total += contact_score * 0.25
        max_score += 0.25

        # Company information (20% weight)
        company_score = 0.0
        if lead.company:
            company_score += 0.4
        if lead.industry:
            company_score += 0.2
        if lead.company_size:
            company_score += 0.2
        if lead.website:
            company_score += 0.2
        breakdown["company_info"] = round(company_score, 2)
        total += company_score * 0.20
        max_score += 0.20

        # Job title relevance (15% weight)
        title_score = 0.0
        if lead.job_title:
            title_lower = lead.job_title.lower()
            decision_maker_titles = [
                "ceo", "cto", "cmo", "cfo", "coo", "vp", "vice president",
                "director", "head of", "founder", "owner", "partner",
                "manager", "lead", "chief",
            ]
            if any(t in title_lower for t in decision_maker_titles):
                title_score = 1.0
            else:
                title_score = 0.4
        breakdown["title_relevance"] = round(title_score, 2)
        total += title_score * 0.15
        max_score += 0.15

        # Location data (5% weight)
        location_score = 1.0 if lead.location else 0.0
        breakdown["location_data"] = location_score
        total += location_score * 0.05
        max_score += 0.05

        # Source quality (10% weight)
        source_scores = {
            "linkedin": 0.9,
            "referral": 1.0,
            "form_capture": 0.8,
            "google_search": 0.6,
            "web_scrape": 0.5,
            "twitter": 0.6,
            "email_campaign": 0.7,
        }
        source_val = lead.source.value if hasattr(lead.source, "value") else str(lead.source)
        source_score = source_scores.get(source_val, 0.3)
        breakdown["source_quality"] = source_score
        total += source_score * 0.10
        max_score += 0.10

        # Service intent clarity (15% weight) - does the lead have clear service tags and notes?
        intent_score = 0.0
        custom = lead.custom_fields or {}
        if custom.get("service_needed"):
            intent_score += 0.5
        if lead.tags and len(lead.tags) > 0:
            intent_score += 0.25
        if lead.notes and len(lead.notes) > 50:
            intent_score += 0.25
        breakdown["service_intent"] = round(intent_score, 2)
        total += intent_score * 0.15
        max_score += 0.15

        # Source URL quality (10% weight) - forum posts are higher value than generic pages
        url_score = 0.3
        url = lead.source_url or ""
        if any(s in url for s in ["reddit.com", "quora.com", "indiehackers.com"]):
            url_score = 0.9  # Forum post = high intent
        elif any(s in url for s in ["gumtree.com", "yell.com", "freelistinguk"]):
            url_score = 0.7  # Directory listing
        elif lead.email:
            url_score = 0.6  # Has contact info
        breakdown["url_quality"] = round(url_score, 2)
        total += url_score * 0.10
        max_score += 0.10

        final_score = round(total / max_score if max_score > 0 else 0.0, 2)
        return final_score, breakdown

    async def _generate_insights(
        self, lead: Lead, score: float, breakdown: dict
    ) -> tuple[str, str]:
        """Use LLM to generate lead summary and recommended next action."""
        try:
            llm = LLMService()
            prompt = f"""Analyze this sales lead and provide:
1. A brief 1-2 sentence summary of the lead quality
2. A recommended next action

Lead Data:
- Name: {lead.first_name or ''} {lead.last_name or ''}
- Company: {lead.company or 'Unknown'}
- Title: {lead.job_title or 'Unknown'}
- Industry: {lead.industry or 'Unknown'}
- Score: {score} / 1.0
- Score Breakdown: {breakdown}
- Source: {lead.source}

Respond in this exact format:
SUMMARY: <your summary>
ACTION: <your recommended action>"""

            response = await llm.complete(prompt)
            lines = response.strip().split("\n")
            summary = ""
            action = ""
            for line in lines:
                if line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                elif line.startswith("ACTION:"):
                    action = line.replace("ACTION:", "").strip()

            return (
                summary or f"Lead scored {score:.0%} based on available data.",
                action or "Review lead details and determine outreach strategy.",
            )
        except Exception as e:
            logger.warning(f"LLM insights generation failed: {e}")
            return (
                f"Lead scored {score:.0%}. {'High' if score >= 0.7 else 'Medium' if score >= 0.4 else 'Low'} priority.",
                "Review and qualify manually.",
            )
