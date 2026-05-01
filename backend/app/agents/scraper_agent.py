"""
Web Scraper Agent - Scrapes websites and Google search results to find potential leads.
Uses AI to extract contact information and company details from web pages.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.models.models import Lead, LeadSource
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Common email pattern
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


class WebScraperAgent(BaseAgent):
    """
    Scrapes target websites and search engines to discover leads.
    Extracts contact info, company details, and uses AI for enrichment.
    """

    async def execute(self, session: AsyncSession, params: dict = None) -> dict:
        params = params or {}
        keywords = params.get("keywords", self.config.get("keywords", ["marketing services"]))
        target_urls = params.get("target_urls", self.config.get("target_urls", []))
        max_leads = params.get("max_leads", self.config.get("max_leads", 20))

        leads_found = []

        # Scrape specific target URLs
        for url in target_urls[:10]:
            try:
                extracted = await self._scrape_url(url)
                leads_found.extend(extracted)
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")

        # Search-based lead discovery
        for keyword in keywords[:5]:
            try:
                search_leads = await self._search_leads(keyword)
                leads_found.extend(search_leads)
            except Exception as e:
                logger.warning(f"Failed search for '{keyword}': {e}")

        # Deduplicate and save
        saved_count = 0
        seen_emails = set()
        for lead_data in leads_found[:max_leads]:
            email = lead_data.get("email")
            if email and email not in seen_emails:
                seen_emails.add(email)
                existing = await session.execute(
                    select(Lead).where(Lead.email == email)
                )
                if existing.scalar_one_or_none() is None:
                    lead = Lead(
                        first_name=lead_data.get("first_name"),
                        last_name=lead_data.get("last_name"),
                        email=email,
                        phone=lead_data.get("phone"),
                        company=lead_data.get("company"),
                        job_title=lead_data.get("job_title"),
                        website=lead_data.get("website"),
                        source=LeadSource.WEB_SCRAPE,
                        source_url=lead_data.get("source_url"),
                        industry=lead_data.get("industry"),
                        location=lead_data.get("location"),
                        tags=lead_data.get("tags", ["web_scrape"]),
                    )
                    session.add(lead)
                    saved_count += 1

        await session.commit()

        return {
            "success": True,
            "leads_count": saved_count,
            "total_found": len(leads_found),
            "sources_scraped": len(target_urls) + len(keywords),
        }

    async def _scrape_url(self, url: str) -> list[dict]:
        """Scrape a single URL for contact information."""
        leads = []
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "MarketingAgencyBot/1.0"})
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        text_content = soup.get_text(separator=" ", strip=True)

        # Extract emails from page
        emails = EMAIL_REGEX.findall(text_content)
        common_ignored = {"example.com", "email.com", "domain.com", "yoursite.com"}
        emails = [e for e in set(emails) if e.split("@")[1] not in common_ignored]

        # Try to get company name from page title or meta
        company = ""
        if soup.title:
            company = soup.title.string or ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = meta_desc["content"] if meta_desc and meta_desc.get("content") else ""

        for email in emails:
            name_parts = email.split("@")[0].replace(".", " ").replace("_", " ").split()
            leads.append({
                "email": email,
                "first_name": name_parts[0].title() if name_parts else None,
                "last_name": name_parts[1].title() if len(name_parts) > 1 else None,
                "company": company[:200],
                "website": url,
                "source_url": url,
                "tags": ["web_scrape"],
            })

        return leads

    async def _search_leads(self, keyword: str) -> list[dict]:
        """
        Use Google Custom Search API or fallback to direct scraping
        to find leads based on keywords.
        """
        from app.core.config import settings

        leads = []

        if settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(
                        "https://www.googleapis.com/customsearch/v1",
                        params={
                            "key": settings.GOOGLE_API_KEY,
                            "cx": settings.GOOGLE_CSE_ID,
                            "q": f"{keyword} contact email",
                            "num": 10,
                        },
                    )
                    data = resp.json()
                    for item in data.get("items", []):
                        url = item.get("link", "")
                        try:
                            page_leads = await self._scrape_url(url)
                            leads.extend(page_leads)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Google search failed: {e}")

        return leads
