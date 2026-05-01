"""
Social Monitor Agent - Monitors social media platforms for potential leads.
Watches for relevant keywords, hashtags, and engagement signals.
"""
from __future__ import annotations

import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.models.models import Lead, LeadSource, AnalyticsEvent

logger = logging.getLogger(__name__)


class SocialMonitorAgent(BaseAgent):
    """
    Monitors Twitter/X and LinkedIn for lead generation signals.
    Watches for keywords, hashtags, and engagement patterns.
    """

    async def execute(self, session: AsyncSession, params: dict = None) -> dict:
        params = params or {}
        keywords = params.get("keywords", self.config.get("keywords", ["need marketing help", "looking for agency"]))
        platforms = params.get("platforms", self.config.get("platforms", ["twitter"]))

        leads_found = []

        if "twitter" in platforms:
            twitter_leads = await self._monitor_twitter(keywords)
            leads_found.extend(twitter_leads)

        # Save leads
        saved_count = 0
        seen_handles = set()

        for lead_data in leads_found:
            identifier = lead_data.get("email") or lead_data.get("twitter_handle") or lead_data.get("linkedin_url")
            if identifier and identifier not in seen_handles:
                seen_handles.add(identifier)

                # Check for existing lead
                existing = None
                if lead_data.get("email"):
                    result = await session.execute(
                        select(Lead).where(Lead.email == lead_data["email"])
                    )
                    existing = result.scalar_one_or_none()
                elif lead_data.get("twitter_handle"):
                    result = await session.execute(
                        select(Lead).where(Lead.twitter_handle == lead_data["twitter_handle"])
                    )
                    existing = result.scalar_one_or_none()

                if existing is None:
                    lead = Lead(
                        first_name=lead_data.get("first_name"),
                        last_name=lead_data.get("last_name"),
                        email=lead_data.get("email"),
                        twitter_handle=lead_data.get("twitter_handle"),
                        linkedin_url=lead_data.get("linkedin_url"),
                        company=lead_data.get("company"),
                        job_title=lead_data.get("job_title"),
                        source=lead_data.get("source", LeadSource.TWITTER),
                        location=lead_data.get("location"),
                        notes=lead_data.get("notes"),
                        tags=lead_data.get("tags", ["social_monitor"]),
                    )
                    session.add(lead)
                    saved_count += 1

        await session.commit()

        return {
            "success": True,
            "leads_count": saved_count,
            "total_found": len(leads_found),
            "platforms_monitored": platforms,
            "keywords_tracked": keywords,
        }

    async def _monitor_twitter(self, keywords: list[str]) -> list[dict]:
        """Monitor Twitter/X for relevant tweets indicating potential leads."""
        leads = []

        if not settings.TWITTER_BEARER_TOKEN:
            logger.info("Twitter bearer token not configured, skipping Twitter monitoring")
            return leads

        headers = {"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            for keyword in keywords[:5]:
                try:
                    resp = await client.get(
                        "https://api.twitter.com/2/tweets/search/recent",
                        params={
                            "query": keyword,
                            "max_results": 10,
                            "tweet.fields": "author_id,created_at,text",
                            "expansions": "author_id",
                            "user.fields": "name,username,description,location",
                        },
                        headers=headers,
                    )

                    if resp.status_code != 200:
                        logger.warning(f"Twitter API returned {resp.status_code}")
                        continue

                    data = resp.json()
                    users = {
                        u["id"]: u
                        for u in data.get("includes", {}).get("users", [])
                    }

                    for tweet in data.get("data", []):
                        author = users.get(tweet.get("author_id"), {})
                        name_parts = author.get("name", "").split(" ", 1)

                        leads.append({
                            "first_name": name_parts[0] if name_parts else None,
                            "last_name": name_parts[1] if len(name_parts) > 1 else None,
                            "twitter_handle": f"@{author.get('username', '')}",
                            "location": author.get("location"),
                            "notes": f"Tweet: {tweet.get('text', '')[:500]}",
                            "source": LeadSource.TWITTER,
                            "tags": ["social_monitor", "twitter", keyword],
                        })

                except Exception as e:
                    logger.warning(f"Twitter monitoring failed for '{keyword}': {e}")

        return leads
